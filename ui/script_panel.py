from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QGroupBox, QMessageBox,
    QAbstractItemView, QCheckBox,
)
from PySide6.QtGui import QColor

from models.action import Action, ActionType
from ui.action_dialog import ActionDialog


class ScriptPanel(QWidget):
    hotkey_changed = Signal(str)
    start_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self._data_manager = data_manager
        self._running = False
        self._current_action_index = -1

        self._build_ui()
        self._refresh_action_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        ctrl_group = QGroupBox("脚本控制")
        ctrl_layout = QVBoxLayout(ctrl_group)

        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("热键:"))
        self._hotkey_edit = QLineEdit()
        self._hotkey_edit.setPlaceholderText("例如: Ctrl+Shift+F1")
        self._hotkey_edit.setText(self._data_manager.script_config.hotkey)
        self._hotkey_edit.textChanged.connect(self._on_hotkey_changed)
        hotkey_layout.addWidget(self._hotkey_edit)

        self._auto_restart_cb = QCheckBox("崩溃后自动重启")
        self._auto_restart_cb.setChecked(self._data_manager.script_config.auto_restart_on_crash)
        self._auto_restart_cb.toggled.connect(self._on_auto_restart_changed)
        hotkey_layout.addWidget(self._auto_restart_cb)

        self._preserve_state_cb = QCheckBox("保留运行状态")
        self._preserve_state_cb.setChecked(self._data_manager.script_config.preserve_run_state)
        self._preserve_state_cb.setToolTip("停止后保留运行位置和临时变量，再次启动时从上一次位置继续")
        self._preserve_state_cb.toggled.connect(self._on_preserve_state_changed)
        hotkey_layout.addWidget(self._preserve_state_cb)

        ctrl_layout.addLayout(hotkey_layout)

        btn_layout = QHBoxLayout()
        self._toggle_btn = QPushButton("启动脚本")
        self._toggle_btn.clicked.connect(self._on_toggle)
        btn_layout.addWidget(self._toggle_btn)

        self._add_action_btn = QPushButton("+ 新增动作")
        self._add_action_btn.clicked.connect(self._add_action)
        btn_layout.addWidget(self._add_action_btn)
        ctrl_layout.addLayout(btn_layout)

        layout.addWidget(ctrl_group)

        action_group = QGroupBox("动作列表")
        action_layout = QVBoxLayout(action_group)
        self._action_list = QListWidget()
        self._action_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._action_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        action_layout.addWidget(self._action_list)
        layout.addWidget(action_group)

    def _on_hotkey_changed(self, text: str):
        self._data_manager.script_config.hotkey = text.strip()
        self._data_manager.save_scripts()
        self.hotkey_changed.emit(text.strip())

    def _on_auto_restart_changed(self, checked: bool):
        self._data_manager.script_config.auto_restart_on_crash = checked
        self._data_manager.save_scripts()

    def _on_preserve_state_changed(self, checked: bool):
        self._data_manager.script_config.preserve_run_state = checked
        self._data_manager.save_scripts()

    def _on_toggle(self):
        if self._running:
            self.stop_clicked.emit()
        else:
            actions = self._data_manager.script_config.actions
            if not actions:
                QMessageBox.warning(self, "提示", "动作列表为空，无法执行脚本")
                return
            seqs = [a.seq for a in actions]
            if len(seqs) != len(set(seqs)):
                QMessageBox.warning(self, "提示", "存在序号重复的动作，请检查后重试")
                return
            self.start_clicked.emit()

    def set_running(self, running: bool):
        self._running = running
        if running:
            self._toggle_btn.setText("停止脚本")
            self._toggle_btn.setStyleSheet("QPushButton { background-color: #c0392b; color: white; }")
            self._hotkey_edit.setEnabled(False)
            self._add_action_btn.setEnabled(False)
        else:
            self._toggle_btn.setText("启动脚本")
            self._toggle_btn.setStyleSheet("")
            self._hotkey_edit.setEnabled(True)
            self._add_action_btn.setEnabled(True)
            self._highlight_action(-1)

    def _highlight_action(self, index: int):
        self._current_action_index = index
        for i in range(self._action_list.count()):
            item = self._action_list.item(i)
            widget = self._action_list.itemWidget(item)
            if widget is not None:
                if i == index:
                    widget.setStyleSheet("background-color: rgba(0, 140, 60, 100); border-radius: 4px;")
                else:
                    widget.setStyleSheet("")

        if index >= 0:
            self._action_list.scrollToItem(
                self._action_list.item(index),
                QAbstractItemView.EnsureVisible,
            )

    def _add_action(self):
        dlg = ActionDialog(self._data_manager, parent=self)
        dlg.action_saved.connect(self._on_action_saved)
        dlg.exec()

    def _edit_action(self, action: Action):
        dlg = ActionDialog(self._data_manager, action, parent=self)
        dlg.action_saved.connect(self._on_action_saved)
        dlg.exec()

    def _on_action_saved(self, action: Action):
        existing = False
        for a in self._data_manager.script_config.actions:
            if a.id == action.id:
                existing = True
                break
        if existing:
            self._data_manager.update_action(action)
        else:
            self._data_manager.add_action(action)
        self._refresh_action_list()

    def _delete_action(self, action_id: str):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除该动作吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._data_manager.delete_action(action_id)
            self._refresh_action_list()

    def _move_action_up(self, action: Action):
        actions = self._data_manager.script_config.actions
        actions.sort(key=lambda a: a.seq)
        for i, a in enumerate(actions):
            if a.id == action.id and i > 0:
                self._data_manager.swap_action_seq(action.id, actions[i - 1].seq)
                self._refresh_action_list()
                return

    def _move_action_down(self, action: Action):
        actions = self._data_manager.script_config.actions
        actions.sort(key=lambda a: a.seq)
        for i, a in enumerate(actions):
            if a.id == action.id and i < len(actions) - 1:
                self._data_manager.swap_action_seq(action.id, actions[i + 1].seq)
                self._refresh_action_list()
                return

    def _get_material_name(self, material_id: str) -> str:
        if not material_id:
            return "无"
        for m in self._data_manager.materials:
            if m.id == material_id:
                return m.name
        return "未知素材"

    def _refresh_action_list(self):
        scrollbar = self._action_list.verticalScrollBar()
        saved_value = scrollbar.value()

        self._action_list.clear()
        self._data_manager.script_config.actions.sort(key=lambda a: a.seq)
        for i, action in enumerate(self._data_manager.script_config.actions):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, action.id)

            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 2, 4, 2)
            item_layout.setSpacing(6)

            seq_label = QLabel(f"#{action.seq}")
            seq_label.setFixedWidth(50)
            seq_label.setStyleSheet("font-weight: bold; color: #4fc3f7; font-size: 12px;")
            item_layout.addWidget(seq_label)

            name_label = QLabel(action.name)
            name_label.setStyleSheet("font-size: 12px; font-weight: bold;")
            item_layout.addWidget(name_label)

            type_label = QLabel(f"[{action.action_type.value}]")
            type_label.setStyleSheet("color: #888; font-size: 11px;")
            item_layout.addWidget(type_label)

            detail_text = self._format_detail(action)
            if detail_text:
                detail_label = QLabel(detail_text)
                detail_label.setStyleSheet("color: #a0a0b0; font-size: 11px;")
                item_layout.addWidget(detail_label)

            item_layout.addStretch()

            actions = self._data_manager.script_config.actions
            n = len(actions)

            up_btn = QPushButton("↑")
            up_btn.setFixedWidth(24)
            up_btn.setEnabled(i > 0)
            up_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #555; background: transparent;
                    color: #4fc3f7; font-size: 12px; padding: 2px 4px; border-radius: 3px;
                }
                QPushButton:hover {
                    color: #81d4fa; background: #3a3a3a;
                }
                QPushButton:disabled {
                    color: #444; border-color: #333;
                }
            """)
            up_btn.clicked.connect(lambda checked=False, a=action: self._move_action_up(a))
            item_layout.addWidget(up_btn)

            down_btn = QPushButton("↓")
            down_btn.setFixedWidth(24)
            down_btn.setEnabled(i < n - 1)
            down_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #555; background: transparent;
                    color: #4fc3f7; font-size: 12px; padding: 2px 4px; border-radius: 3px;
                }
                QPushButton:hover {
                    color: #81d4fa; background: #3a3a3a;
                }
                QPushButton:disabled {
                    color: #444; border-color: #333;
                }
            """)
            down_btn.clicked.connect(lambda checked=False, a=action: self._move_action_down(a))
            item_layout.addWidget(down_btn)

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #555; background: transparent;
                    color: #4fc3f7; font-size: 11px; padding: 2px 6px; border-radius: 3px;
                }
                QPushButton:hover {
                    color: #81d4fa; background: #3a3a3a;
                }
            """)
            action_id = action.id
            edit_btn.clicked.connect(lambda checked=False, a=action: self._edit_action(a))
            item_layout.addWidget(edit_btn)

            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #555; background: transparent;
                    color: #ff5555; font-size: 11px; padding: 2px 6px; border-radius: 3px;
                }
                QPushButton:hover {
                    color: #ff0000; background: #3a3a3a;
                }
            """)
            del_btn.clicked.connect(lambda checked=False, aid=action_id: self._delete_action(aid))
            item_layout.addWidget(del_btn)

            item.setSizeHint(item_widget.sizeHint())
            self._action_list.addItem(item)
            self._action_list.setItemWidget(item, item_widget)

        scrollbar.setValue(min(saved_value, scrollbar.maximum()))

    def _format_detail(self, action: Action) -> str:
        if action.action_type == ActionType.DELAY:
            if action.delay_ms >= 1000:
                return f"⏱ 延时 {action.delay_ms / 1000:.1f}s"
            return f"⏱ 延时 {action.delay_ms}ms"

        elif action.action_type == ActionType.VISUAL:
            if action.use_last_material:
                mat_name = "（上一个设置的素材）"
            else:
                mat_name = self._get_material_name(action.material_id)
            parts = [f"检测: {mat_name}"]
            if action.on_found_jump_seq is not None:
                parts.append(f"找到 → #{action.on_found_jump_seq}")
            else:
                parts.append("找到 → 继续")
            if action.on_not_found_jump_seq is not None:
                parts.append(f"未找到 → #{action.on_not_found_jump_seq}")
            else:
                parts.append("未找到 → 继续")
            return "  |  ".join(parts)

        elif action.action_type == ActionType.MOUSE_MOVE:
            if action.use_last_detected_pos:
                pos = "上次检测位置"
            else:
                pos = f"({action.dest_x}, {action.dest_y})"
            if action.move_duration_ms > 0:
                dur = f"{action.move_duration_ms}ms"
            else:
                dur = "瞬移"
            return f"目标: {pos}  |  {dur}"

        elif action.action_type == ActionType.MOUSE_CLICK:
            click_type = "双击" if action.click_type == "double" else "单击"
            return f"🖱 {click_type}"

        elif action.action_type == ActionType.JUMP:
            if action.jump_if_material_id:
                mat_name = self._get_material_name(action.jump_if_material_id)
                parts = [f"条件: 素材={mat_name}"]
                if action.jump_if_material_seq is not None:
                    parts.append(f"匹配 → #{action.jump_if_material_seq}")
                else:
                    parts.append("匹配 → 继续")
                if action.jump_else_seq is not None:
                    parts.append(f"否则 → #{action.jump_else_seq}")
                else:
                    parts.append("否则 → 继续")
                return "  |  ".join(parts)
            else:
                if action.jump_seq is not None:
                    return f"跳转到 #{action.jump_seq}"
                return "跳转到 (未设置)"

        elif action.action_type == ActionType.SET_MATERIAL:
            mat_name = self._get_material_name(action.material_id)
            return f"设置素材: {mat_name}"

        return ""