from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QTextEdit, QGroupBox,
)
from PySide6.QtGui import QIcon
import ctypes
from ctypes import wintypes

from core.data_manager import DataManager
from core.vision_engine import VisionEngine
from core.script_engine import ScriptEngine
from ui.material_panel import MaterialPanel
from ui.script_panel import ScriptPanel


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_MAP = {v: k for k, v in vars(wintypes).items() if k.startswith("VK_")}
_VK_CODE_MAP = {}
for attr in dir(ctypes.wintypes):
    if attr.startswith("VK_"):
        try:
            _VK_CODE_MAP[attr] = getattr(ctypes.wintypes, attr)
        except Exception:
            pass

VK_NAMES = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F,
    "F17": 0x80, "F18": 0x81, "F19": 0x82, "F20": 0x83,
    "F21": 0x84, "F22": 0x85, "F23": 0x86, "F24": 0x87,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59,
    "Z": 0x5A,
}


def _parse_hotkey(hotkey_str: str) -> tuple[int, int] | None:
    if not hotkey_str:
        return None
    parts = [p.strip() for p in hotkey_str.upper().split("+")]
    modifiers = 0
    vk = 0
    for part in parts:
        if part == "CTRL" or part == "CONTROL":
            modifiers |= MOD_CONTROL
        elif part == "SHIFT":
            modifiers |= MOD_SHIFT
        elif part == "ALT":
            modifiers |= MOD_ALT
        elif part == "WIN" or part == "WINDOWS":
            modifiers |= MOD_WIN
        elif part in VK_NAMES:
            vk = VK_NAMES[part]
        else:
            return None
    if vk == 0:
        return None
    return (modifiers, vk)


class MainWindow(QMainWindow):
    MAX_LOG_LINES = 1000
    _hotkey_id = 1

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self._data_manager = data_manager
        self._vision = VisionEngine(data_manager._data_dir)
        self._script_engine = ScriptEngine(data_manager, self._vision)

        self.setWindowTitle("VisualAuto - 视觉自动化脚本")
        self.resize(1100, 700)
        self.setMinimumSize(900, 500)

        self._build_ui()
        self._connect_signals()
        self._register_hotkey()

    def _register_hotkey(self):
        user32 = ctypes.windll.user32
        hotkey_str = self._data_manager.script_config.hotkey
        parsed = _parse_hotkey(hotkey_str)
        if parsed is not None:
            mods, vk = parsed
            user32.RegisterHotKey(int(self.winId()), self._hotkey_id, mods, vk)

    def _unregister_hotkey(self):
        user32 = ctypes.windll.user32
        user32.UnregisterHotKey(int(self.winId()), self._hotkey_id)

    def _on_hotkey_changed(self, hotkey_str: str):
        self._unregister_hotkey()
        self._register_hotkey()

    def nativeEvent(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                if self._script_engine.is_running():
                    self._stop_script()
                else:
                    self._start_script()
                return True, 0
        return False, 0

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        self._script_panel = ScriptPanel(self._data_manager)
        splitter.addWidget(self._script_panel)

        self._material_panel = MaterialPanel(self._data_manager)
        splitter.addWidget(self._material_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 400])

        main_layout.addWidget(splitter, stretch=3)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(4, 4, 4, 4)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.document().setMaximumBlockCount(self.MAX_LOG_LINES)
        self._log_text.setMaximumHeight(120)
        log_layout.addWidget(self._log_text)
        main_layout.addWidget(log_group, stretch=0)

    def _connect_signals(self):
        self._script_panel.start_clicked.connect(self._start_script)
        self._script_panel.stop_clicked.connect(self._stop_script)
        self._script_panel.hotkey_changed.connect(self._on_hotkey_changed)

        self._script_engine.action_started.connect(self._script_panel._highlight_action)
        self._script_engine.log_message.connect(self.append_log)
        self._script_engine.script_finished.connect(self._on_script_finished)
        self._script_engine.script_error.connect(self._on_script_error)

        self._material_panel.material_list_changed.connect(self._on_material_list_changed)

    def append_log(self, message: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scrollbar = self._log_text.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10

        self._log_text.append(f"[{timestamp}] {message}")

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _start_script(self):
        self._script_panel.set_running(True)
        self._script_engine.start()

    def _stop_script(self):
        self._script_engine.stop_script()
        self._script_engine.wait(1000)
        self._script_panel.set_running(False)

    def _on_script_finished(self):
        self._script_panel.set_running(False)
        self._script_engine.clear_saved_state()

    def _on_script_error(self, error_msg: str):
        self._script_panel.set_running(False)
        self._script_engine.clear_saved_state()
        if self._data_manager.script_config.auto_restart_on_crash:
            self._show_error_with_countdown(error_msg)
        else:
            QMessageBox.critical(self, "脚本错误", f"脚本执行出错:\n{error_msg}")

    def _show_error_with_countdown(self, error_msg: str):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("脚本错误")
        dlg.setMinimumWidth(400)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)
        msg_label = QLabel(f"脚本执行出错:\n{error_msg}")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn_layout = QDialogButtonBox()
        self._countdown_btn = QPushButton("确定（10）")
        self._countdown_btn.clicked.connect(dlg.accept)
        btn_layout.addButton(self._countdown_btn, QDialogButtonBox.AcceptRole)
        layout.addWidget(btn_layout)

        self._countdown_value = 10
        self._countdown_dlg = dlg

        def _tick():
            self._countdown_value -= 1
            if self._countdown_value <= 0:
                self._countdown_timer.stop()
                dlg.accept()
            else:
                self._countdown_btn.setText(f"确定（{self._countdown_value}）")

        self._countdown_timer = QTimer(dlg)
        self._countdown_timer.timeout.connect(_tick)
        self._countdown_timer.start(1000)

        dlg.exec()

        self._countdown_timer.stop()
        self._script_engine.clear_saved_state()
        self._start_script()

    def _on_material_list_changed(self):
        pass

    def closeEvent(self, event):
        self._unregister_hotkey()
        if self._script_engine.is_running():
            self._script_engine.stop_script()
            self._script_engine.wait(2000)
        event.accept()