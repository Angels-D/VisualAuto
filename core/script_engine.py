import time
import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from models.action import Action, ActionType
from core.data_manager import DataManager
from core.vision_engine import VisionEngine
from core.input_simulator import move_mouse_to, click_at, get_cursor_pos

logger = logging.getLogger(__name__)


class ScriptEngine(QThread):
    action_started = Signal(int)
    action_finished = Signal(int)
    log_message = Signal(str)
    script_finished = Signal()
    script_error = Signal(str)

    def __init__(self, data_manager: DataManager, vision_engine: VisionEngine):
        super().__init__()
        self._data_manager = data_manager
        self._vision = vision_engine
        self._running = False
        self._paused = False
        self._mutex = QMutex()
        self._current_index = 0
        self._last_set_material_id: Optional[str] = None
        self._saved_state: Optional[dict] = None

    def stop_script(self):
        with QMutexLocker(self._mutex):
            self._running = False
            self._paused = False
            if self._data_manager.script_config.preserve_run_state:
                self._saved_state = {
                    "current_index": self._current_index,
                    "last_set_material_id": self._last_set_material_id,
                }

    def clear_saved_state(self):
        self._saved_state = None

    def has_saved_state(self) -> bool:
        return self._saved_state is not None

    def pause_script(self):
        with QMutexLocker(self._mutex):
            self._paused = True

    def resume_script(self):
        with QMutexLocker(self._mutex):
            self._paused = False

    def is_running(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._running

    def run(self):
        with QMutexLocker(self._mutex):
            self._running = True
            if self._saved_state is not None and self._data_manager.script_config.preserve_run_state:
                self._current_index = self._saved_state.get("current_index", 0)
                self._last_set_material_id = self._saved_state.get("last_set_material_id")
                self._saved_state = None
            else:
                self._current_index = 0
                self._last_set_material_id = None
                self._saved_state = None

        actions = self._data_manager.script_config.actions
        if not actions:
            self.script_error.emit("动作列表为空，无法执行脚本")
            self._running = False
            return

        self.log_message.emit("脚本开始执行")

        while self._running and 0 <= self._current_index < len(actions):
            with QMutexLocker(self._mutex):
                if self._paused:
                    self.msleep(100)
                    continue

            action = actions[self._current_index]
            self.action_started.emit(self._current_index)

            try:
                next_index = self._execute_action(action)
            except Exception as e:
                self.log_message.emit(f"执行动作 #{action.seq} 出错: {e}")
                self._running = False
                self.script_error.emit(str(e))
                break

            self.action_finished.emit(self._current_index)

            if next_index is not None:
                self._current_index = next_index
            else:
                self._current_index += 1

        self._running = False
        self.log_message.emit("脚本执行结束")
        self.script_finished.emit()

    def _execute_action(self, action: Action) -> Optional[int]:
        from datetime import datetime

        if action.action_type == ActionType.DELAY:
            self.log_message.emit(f"#{action.seq} [{action.name}] 延时 {action.delay_ms}ms")
            elapsed = 0
            while elapsed < action.delay_ms and self._running:
                time.sleep(0.05)
                elapsed += 50
            return None

        elif action.action_type == ActionType.MOUSE_MOVE:
            if action.use_last_detected_pos:
                if self._vision.last_detected_pos is None:
                    msg = f"#{action.seq} [{action.name}] 使用上一次识别位置，但尚无识别记录"
                    self.log_message.emit(msg)
                    self.script_error.emit(msg)
                    self._running = False
                    return None
                dx, dy = self._vision.last_detected_pos
                self.log_message.emit(f"#{action.seq} [{action.name}] 移动到上次识别位置 ({dx}, {dy})")
                move_mouse_to(dx, dy, action.move_duration_ms)
            else:
                self.log_message.emit(f"#{action.seq} [{action.name}] 移动到 ({action.dest_x}, {action.dest_y})")
                move_mouse_to(action.dest_x, action.dest_y, action.move_duration_ms)
            return None

        elif action.action_type == ActionType.MOUSE_CLICK:
            cx, cy = get_cursor_pos()
            click_type_str = "双击" if action.click_type == "double" else "单击"
            self.log_message.emit(f"#{action.seq} [{action.name}] 在 ({cx}, {cy}) {click_type_str}")
            click_at(cx, cy, action.click_type)
            return None

        elif action.action_type == ActionType.VISUAL:
            if action.use_last_material:
                if self._last_set_material_id is None:
                    msg = f"#{action.seq} [{action.name}] 使用上一个设置的素材，但尚无素材被设置"
                    self.log_message.emit(msg)
                    self.script_error.emit(msg)
                    self._running = False
                    return None
                material_id = self._last_set_material_id
            else:
                material_id = action.material_id

            material = self._data_manager.get_material(material_id)
            if material is None:
                self.log_message.emit(f"#{action.seq} [{action.name}] 视觉判断: 素材不存在")
                if action.on_not_found_jump_seq is not None:
                    return self._find_index_by_seq(action.on_not_found_jump_seq)
                return None

            template_path = self._data_manager.get_material_image_path(material)
            if not template_path:
                self.log_message.emit(f"#{action.seq} [{action.name}] 视觉判断: 素材图片不存在")
                if action.on_not_found_jump_seq is not None:
                    return self._find_index_by_seq(action.on_not_found_jump_seq)
                return None

            rx, ry, rw, rh = material.detect_region
            found, box = self._vision.match_template(template_path, (rx, ry, rw, rh), material.threshold,
                                                     material.target_pos)

            if found:
                cx, cy = self._vision.last_detected_pos
                self.log_message.emit(f"#{action.seq} [{action.name}] 视觉判断: 识别成功, 位置 ({cx}, {cy})")
                if action.on_found_jump_seq is not None:
                    return self._find_index_by_seq(action.on_found_jump_seq)
            else:
                self.log_message.emit(f"#{action.seq} [{action.name}] 视觉判断: 未识别到")
                if action.on_not_found_jump_seq is not None:
                    return self._find_index_by_seq(action.on_not_found_jump_seq)
            return None

        elif action.action_type == ActionType.SET_MATERIAL:
            material_id = action.material_id
            if not material_id:
                msg = f"#{action.seq} [{action.name}] 设置素材: 未选择素材"
                self.log_message.emit(msg)
                self.script_error.emit(msg)
                self._running = False
                return None
            material = self._data_manager.get_material(material_id)
            mat_name = material.name if material else "未知"
            self._last_set_material_id = material_id
            self.log_message.emit(f"#{action.seq} [{action.name}] 设置素材: {mat_name}")
            return None

        elif action.action_type == ActionType.JUMP:
            if action.jump_if_material_id:
                if self._last_set_material_id is None:
                    self.log_message.emit(
                        f"#{action.seq} [{action.name}] 条件跳转: 尚无素材被设置，跳转到 else 分支"
                    )
                    if action.jump_else_seq is not None:
                        return self._find_index_by_seq(action.jump_else_seq)
                    return None
                if self._last_set_material_id == action.jump_if_material_id:
                    mat = self._data_manager.get_material(action.jump_if_material_id)
                    mat_name = mat.name if mat else "未知"
                    self.log_message.emit(
                        f"#{action.seq} [{action.name}] 条件跳转: 素材匹配 ({mat_name})，跳转到 #{action.jump_if_material_seq}"
                    )
                    if action.jump_if_material_seq is not None:
                        return self._find_index_by_seq(action.jump_if_material_seq)
                else:
                    self.log_message.emit(
                        f"#{action.seq} [{action.name}] 条件跳转: 素材不匹配，跳转到 else 分支"
                    )
                    if action.jump_else_seq is not None:
                        return self._find_index_by_seq(action.jump_else_seq)
            else:
                self.log_message.emit(f"#{action.seq} [{action.name}] 跳转到 #{action.jump_seq}")
                if action.jump_seq is not None:
                    return self._find_index_by_seq(action.jump_seq)
            return None

        return None

    def _find_index_by_seq(self, seq: int) -> Optional[int]:
        for i, a in enumerate(self._data_manager.script_config.actions):
            if a.seq == seq:
                return i
        return None