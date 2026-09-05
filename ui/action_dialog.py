from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QCheckBox, QPushButton,
    QButtonGroup, QRadioButton, QWidget, QLabel,
    QStackedWidget, QDialogButtonBox,
)
from PySide6.QtGui import QIntValidator

from models.action import Action, ActionType
from core.input_simulator import get_cursor_pos


class ActionDialog(QDialog):
    action_saved = Signal(object)

    def __init__(self, data_manager, action: Action = None, parent=None):
        super().__init__(parent)
        self._data_manager = data_manager
        self._action = action
        self._editing = action is not None
        self._selected_pos = None

        self.setWindowTitle("编辑动作" if self._editing else "新增动作")
        self.setMinimumWidth(450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._build_ui()

        if self._editing:
            self._load_action(action)
        else:
            self._auto_set_seq()

    def _auto_set_seq(self):
        existing_seqs = [a.seq for a in self._data_manager.script_config.actions]
        next_seq = max(existing_seqs) + 1 if existing_seqs else 1
        self._seq_edit.setText(str(next_seq))

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("输入动作名称")
        form.addRow("动作名称:", self._name_edit)

        self._seq_edit = QLineEdit("1")
        self._seq_edit.setValidator(QIntValidator(0, 999999))
        form.addRow("序号:", self._seq_edit)

        self._type_combo = QComboBox()
        for t in ActionType:
            self._type_combo.addItem(t.value)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("动作类型:", self._type_combo)

        layout.addLayout(form)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_delay_panel())
        self._stack.addWidget(self._build_visual_panel())
        self._stack.addWidget(self._build_move_panel())
        self._stack.addWidget(self._build_click_panel())
        self._stack.addWidget(self._build_jump_panel())
        self._stack.addWidget(self._build_set_material_panel())
        layout.addWidget(self._stack)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_delay_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self._delay_edit = QLineEdit("1000")
        self._delay_edit.setValidator(QIntValidator(0, 999999999))
        self._delay_edit.setPlaceholderText("毫秒")
        layout.addRow("延时时间 (ms):", self._delay_edit)
        return w

    def _build_visual_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self._visual_use_last_mat = QCheckBox("使用上一个设置的素材")
        self._visual_use_last_mat.toggled.connect(self._on_visual_use_last_toggled)
        layout.addRow("", self._visual_use_last_mat)

        self._visual_material = QComboBox()
        self._refresh_material_combo()
        layout.addRow("目标视觉素材:", self._visual_material)

        self._visual_not_found_jump = QComboBox()
        self._visual_not_found_jump.addItem("（继续下一条）", None)
        self._refresh_jump_combo(self._visual_not_found_jump)
        layout.addRow("未识别时跳转:", self._visual_not_found_jump)

        self._visual_found_jump = QComboBox()
        self._visual_found_jump.addItem("（继续下一条）", None)
        self._refresh_jump_combo(self._visual_found_jump)
        layout.addRow("识别到时跳转:", self._visual_found_jump)

        return w

    def _on_visual_use_last_toggled(self, checked: bool):
        self._visual_material.setEnabled(not checked)

    def _build_move_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self._move_use_last = QCheckBox("使用上一次视觉识别的目标位置")
        self._move_use_last.toggled.connect(self._on_move_use_last_toggled)
        layout.addRow("", self._move_use_last)

        pos_layout = QHBoxLayout()
        self._move_x = QLineEdit("0")
        self._move_x.setValidator(QIntValidator())
        self._move_x.setPlaceholderText("X")
        self._move_y = QLineEdit("0")
        self._move_y.setValidator(QIntValidator())
        self._move_y.setPlaceholderText("Y")
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self._move_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self._move_y)

        self._move_pick_btn = QPushButton("🎯")
        self._move_pick_btn.setToolTip("点击屏幕获取坐标")
        self._move_pick_btn.setFixedWidth(40)
        self._move_pick_btn.clicked.connect(self._pick_position)
        pos_layout.addWidget(self._move_pick_btn)

        layout.addRow("目标坐标:", pos_layout)

        self._move_duration = QLineEdit("0")
        self._move_duration.setValidator(QIntValidator(0, 999999))
        self._move_duration.setPlaceholderText("毫秒")
        self._move_duration.setToolTip("0 为瞬移，大于 0 以加速形式移动")
        layout.addRow("移动耗时 (ms):", self._move_duration)

        return w

    def _build_click_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self._click_single = QRadioButton("单击")
        self._click_double = QRadioButton("双击")
        self._click_single.setChecked(True)
        group = QButtonGroup(w)
        group.addButton(self._click_single)
        group.addButton(self._click_double)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self._click_single)
        radio_layout.addWidget(self._click_double)
        radio_layout.addStretch()
        layout.addRow("点击类型:", radio_layout)

        return w

    def _build_jump_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self._jump_conditional = QCheckBox("条件跳转（根据上一个设置的素材）")
        self._jump_conditional.toggled.connect(self._on_jump_conditional_toggled)
        layout.addRow("", self._jump_conditional)

        self._jump_simple_container = QWidget()
        simple_layout = QFormLayout(self._jump_simple_container)
        simple_layout.setContentsMargins(0, 0, 0, 0)
        self._jump_target = QComboBox()
        self._jump_target.addItem("（请选择）", None)
        self._refresh_jump_combo(self._jump_target)
        simple_layout.addRow("跳转到:", self._jump_target)
        layout.addRow(self._jump_simple_container)

        self._jump_cond_container = QWidget()
        cond_layout = QFormLayout(self._jump_cond_container)
        cond_layout.setContentsMargins(0, 0, 0, 0)

        self._jump_if_material = QComboBox()
        self._jump_if_material.addItem("（请选择）", "")
        for m in self._data_manager.materials:
            self._jump_if_material.addItem(m.name, m.id)
        cond_layout.addRow("如果上一个素材是:", self._jump_if_material)

        self._jump_if_target = QComboBox()
        self._jump_if_target.addItem("（请选择）", None)
        self._refresh_jump_combo(self._jump_if_target)
        cond_layout.addRow("匹配时跳转到:", self._jump_if_target)

        self._jump_else_target = QComboBox()
        self._jump_else_target.addItem("（请选择）", None)
        self._refresh_jump_combo(self._jump_else_target)
        cond_layout.addRow("不匹配/无素材时跳转到:", self._jump_else_target)

        self._jump_cond_container.setVisible(False)
        layout.addRow(self._jump_cond_container)

        return w

    def _on_jump_conditional_toggled(self, checked: bool):
        self._jump_simple_container.setVisible(not checked)
        self._jump_cond_container.setVisible(checked)

    def _build_set_material_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self._set_mat_combo = QComboBox()
        self._refresh_material_combo_for_set()
        layout.addRow("选择素材:", self._set_mat_combo)

        info_label = QLabel("该动作将设置后续视觉判断所使用的素材")
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("", info_label)

        return w

    def _refresh_material_combo_for_set(self):
        self._set_mat_combo.clear()
        self._set_mat_combo.addItem("（请选择）", "")
        for m in self._data_manager.materials:
            self._set_mat_combo.addItem(m.name, m.id)

    def _on_type_changed(self, idx: int):
        self._stack.setCurrentIndex(idx)

    def _on_move_use_last_toggled(self, checked: bool):
        self._move_x.setEnabled(not checked)
        self._move_y.setEnabled(not checked)
        self._move_pick_btn.setEnabled(not checked)

    def _pick_position(self):
        self.hide()
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtWidgets import QApplication

        def _do_pick():
            import time
            time.sleep(0.3)
            pos = get_cursor_pos()
            self._move_x.setText(str(pos[0]))
            self._move_y.setText(str(pos[1]))
            self.show()

        QTimer.singleShot(200, _do_pick)

    def _refresh_material_combo(self):
        self._visual_material.clear()
        self._visual_material.addItem("（请选择）", "")
        for m in self._data_manager.materials:
            self._visual_material.addItem(m.name, m.id)

    def _refresh_jump_combo(self, combo: QComboBox):
        current_data = combo.currentData()
        combo.clear()
        combo.addItem("（继续下一条）", None)
        for a in self._data_manager.script_config.actions:
            combo.addItem(f"#{a.seq} {a.name}", a.seq)
        if current_data is not None:
            idx = combo.findData(current_data)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _load_action(self, action: Action):
        self._name_edit.setText(action.name)
        self._seq_edit.setText(str(action.seq))

        type_idx = 0
        for i, t in enumerate(ActionType):
            if t == action.action_type:
                type_idx = i
                break
        self._type_combo.setCurrentIndex(type_idx)
        self._stack.setCurrentIndex(type_idx)

        self._delay_edit.setText(str(action.delay_ms))

        if action.material_id:
            idx = self._visual_material.findData(action.material_id)
            if idx >= 0:
                self._visual_material.setCurrentIndex(idx)

        self._visual_use_last_mat.setChecked(action.use_last_material)

        if action.on_not_found_jump_seq is not None:
            idx = self._visual_not_found_jump.findData(action.on_not_found_jump_seq)
            if idx >= 0:
                self._visual_not_found_jump.setCurrentIndex(idx)

        if action.on_found_jump_seq is not None:
            idx = self._visual_found_jump.findData(action.on_found_jump_seq)
            if idx >= 0:
                self._visual_found_jump.setCurrentIndex(idx)

        self._move_use_last.setChecked(action.use_last_detected_pos)
        self._move_x.setText(str(action.dest_x))
        self._move_y.setText(str(action.dest_y))
        self._move_duration.setText(str(action.move_duration_ms))

        if action.click_type == "double":
            self._click_double.setChecked(True)
        else:
            self._click_single.setChecked(True)

        if action.jump_seq is not None:
            idx = self._jump_target.findData(action.jump_seq)
            if idx >= 0:
                self._jump_target.setCurrentIndex(idx)

        is_conditional = bool(action.jump_if_material_id)
        self._jump_conditional.setChecked(is_conditional)
        if is_conditional:
            idx = self._jump_if_material.findData(action.jump_if_material_id)
            if idx >= 0:
                self._jump_if_material.setCurrentIndex(idx)
            if action.jump_if_material_seq is not None:
                idx = self._jump_if_target.findData(action.jump_if_material_seq)
                if idx >= 0:
                    self._jump_if_target.setCurrentIndex(idx)
            if action.jump_else_seq is not None:
                idx = self._jump_else_target.findData(action.jump_else_seq)
                if idx >= 0:
                    self._jump_else_target.setCurrentIndex(idx)

        if action.action_type == ActionType.SET_MATERIAL and action.material_id:
            idx = self._set_mat_combo.findData(action.material_id)
            if idx >= 0:
                self._set_mat_combo.setCurrentIndex(idx)

    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            return

        try:
            seq = int(self._seq_edit.text())
        except ValueError:
            seq = 0

        action_type = list(ActionType)[self._type_combo.currentIndex()]

        exclude_id = self._action.id if self._editing else None
        needs_insert_new = False
        if self._data_manager.is_seq_duplicate(seq, exclude_id):
            if self._editing:
                self._data_manager.insert_action_at_seq(self._action.id, seq)
            else:
                needs_insert_new = True

        if self._editing:
            action = Action(
                id=self._action.id,
                name=name,
                seq=seq,
                action_type=action_type,
            )
        else:
            action = Action(
                name=name,
                seq=seq,
                action_type=action_type,
            )

        if action_type == ActionType.DELAY:
            try:
                action.delay_ms = int(self._delay_edit.text())
            except ValueError:
                action.delay_ms = 0
        elif action_type == ActionType.VISUAL:
            action.use_last_material = self._visual_use_last_mat.isChecked()
            action.material_id = self._visual_material.currentData()
            action.on_not_found_jump_seq = self._visual_not_found_jump.currentData()
            action.on_found_jump_seq = self._visual_found_jump.currentData()
        elif action_type == ActionType.MOUSE_MOVE:
            action.use_last_detected_pos = self._move_use_last.isChecked()
            try:
                action.dest_x = int(self._move_x.text())
            except ValueError:
                action.dest_x = 0
            try:
                action.dest_y = int(self._move_y.text())
            except ValueError:
                action.dest_y = 0
            try:
                action.move_duration_ms = int(self._move_duration.text())
            except ValueError:
                action.move_duration_ms = 0
        elif action_type == ActionType.MOUSE_CLICK:
            action.click_type = "double" if self._click_double.isChecked() else "single"
        elif action_type == ActionType.JUMP:
            if self._jump_conditional.isChecked():
                action.jump_if_material_id = self._jump_if_material.currentData()
                action.jump_if_material_seq = self._jump_if_target.currentData()
                action.jump_else_seq = self._jump_else_target.currentData()
            else:
                action.jump_seq = self._jump_target.currentData()
        elif action_type == ActionType.SET_MATERIAL:
            action.material_id = self._set_mat_combo.currentData()

        if needs_insert_new:
            self._data_manager.insert_new_action_at_seq(action, seq)
            self.action_saved.emit(action)
        else:
            self.action_saved.emit(action)

        self.accept()