import os
import shutil

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSlider, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QGroupBox, QMessageBox, QFileDialog,
    QApplication, QSizePolicy,
)
from models.material import Material
from ui.region_selector import RegionSelector
from ui.image_preview import ImagePreviewDialog
from core.vision_engine import VisionEngine


class MaterialPanel(QWidget):
    material_list_changed = Signal()

    PREVIEW_SIZE = 120

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self._data_manager = data_manager
        self._current_material: Material | None = None
        self._pending_region = None
        self._pending_screenshot = None
        self._pending_target_pos = None
        self._picking_target = False
        self._region_selector = None
        self._screenshot_selector = None
        self._detection_overlay = None

        self._build_ui()
        self._refresh_list()
        self._clear_editor()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        editor_group = QGroupBox("素材编辑")
        editor_layout = QVBoxLayout(editor_group)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("输入素材名称")
        form.addRow("素材名:", self._name_edit)

        region_layout = QHBoxLayout()
        self._region_edit = QLineEdit()
        self._region_edit.setPlaceholderText("x, y, w, h（可手动输入或框选）")
        region_layout.addWidget(self._region_edit)

        self._region_btn = QPushButton("框选")
        self._region_btn.setToolTip("交互式框选检测范围")
        self._region_btn.clicked.connect(self._start_region_selection)
        region_layout.addWidget(self._region_btn)
        form.addRow("检测范围:", region_layout)

        img_layout = QHBoxLayout()
        self._preview_label = QLabel()
        self._preview_label.setFixedSize(self.PREVIEW_SIZE, self.PREVIEW_SIZE)
        self._preview_label.setStyleSheet(
            "border: 1px solid #555; background-color: #2a2a2a;"
        )
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setText("无图片")
        self._preview_label.mousePressEvent = self._on_preview_click
        img_layout.addWidget(self._preview_label)

        img_btn_layout = QVBoxLayout()
        self._screenshot_btn = QPushButton("截图")
        self._screenshot_btn.setToolTip("交互式框选截图")
        self._screenshot_btn.clicked.connect(self._start_screenshot_selection)
        img_btn_layout.addWidget(self._screenshot_btn)

        self._choose_img_btn = QPushButton("选图")
        self._choose_img_btn.setToolTip("选择已有的图片文件")
        self._choose_img_btn.clicked.connect(self._choose_image_file)
        img_btn_layout.addWidget(self._choose_img_btn)
        img_btn_layout.addStretch()
        img_layout.addLayout(img_btn_layout)
        form.addRow("素材图片:", img_layout)

        threshold_layout = QHBoxLayout()
        self._threshold_slider = QSlider(Qt.Horizontal)
        self._threshold_slider.setRange(0, 100)
        self._threshold_slider.setValue(75)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(self._threshold_slider)

        self._threshold_label = QLabel("75%")
        self._threshold_label.setFixedWidth(40)
        threshold_layout.addWidget(self._threshold_label)
        form.addRow("识别误差:", threshold_layout)

        target_pos_layout = QHBoxLayout()
        self._target_x_edit = QLineEdit()
        self._target_x_edit.setPlaceholderText("X")
        self._target_x_edit.setFixedWidth(50)
        self._target_y_edit = QLineEdit()
        self._target_y_edit.setPlaceholderText("Y")
        self._target_y_edit.setFixedWidth(50)
        target_pos_layout.addWidget(QLabel("X:"))
        target_pos_layout.addWidget(self._target_x_edit)
        target_pos_layout.addWidget(QLabel("Y:"))
        target_pos_layout.addWidget(self._target_y_edit)

        self._target_pick_btn = QPushButton("选点")
        self._target_pick_btn.setToolTip("点击后在素材图片上选择目标位置")
        self._target_pick_btn.clicked.connect(self._start_target_pick)
        target_pos_layout.addWidget(self._target_pick_btn)

        target_pos_layout.addStretch()
        form.addRow("目标位置:", target_pos_layout)

        editor_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("添加素材")
        self._add_btn.clicked.connect(self._add_material)
        btn_layout.addWidget(self._add_btn)

        self._save_btn = QPushButton("保存修改")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_material)
        btn_layout.addWidget(self._save_btn)

        self._test_btn = QPushButton("测试识别")
        self._test_btn.clicked.connect(self._test_material)
        btn_layout.addWidget(self._test_btn)

        editor_layout.addLayout(btn_layout)
        layout.addWidget(editor_group)

        list_group = QGroupBox("素材列表")
        list_layout = QVBoxLayout(list_group)
        self._list_widget = QListWidget()
        self._list_widget.currentRowChanged.connect(self._on_list_selection)
        list_layout.addWidget(self._list_widget)
        layout.addWidget(list_group)

    def _on_threshold_changed(self, val: int):
        self._threshold_label.setText(f"{val}%")

    def _start_region_selection(self):
        self._region_selector = RegionSelector()
        self._region_selector.region_selected.connect(self._on_region_selected)
        self._region_selector.show()

    def _on_region_selected(self, x: int, y: int, w: int, h: int):
        self._region_edit.setText(f"{x}, {y}, {w}, {h}")
        self._pending_region = (x, y, w, h)

    def _parse_region(self) -> tuple | None:
        text = self._region_edit.text().strip()
        if not text:
            return None
        parts = text.replace(",", " ").split()
        if len(parts) != 4:
            return None
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        except ValueError:
            return None

    def _parse_target_pos(self) -> tuple | None:
        x_text = self._target_x_edit.text().strip()
        y_text = self._target_y_edit.text().strip()
        if not x_text and not y_text:
            return self._pending_target_pos
        try:
            x = int(x_text) if x_text else 0
            y = int(y_text) if y_text else 0
            return (x, y)
        except ValueError:
            return self._pending_target_pos

    def _set_preview_pixmap(self, original_pixmap: QPixmap):
        target_pos = self._parse_target_pos()
        if target_pos is None:
            target_pos = self._pending_target_pos

        scaled = original_pixmap.scaled(
            self.PREVIEW_SIZE, self.PREVIEW_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        scaled_w = scaled.width()
        scaled_h = scaled.height()

        if target_pos is not None and target_pos[0] >= 0 and target_pos[1] >= 0:
            orig_w = original_pixmap.width()
            orig_h = original_pixmap.height()

            offset_x = (self.PREVIEW_SIZE - scaled_w) // 2
            offset_y = (self.PREVIEW_SIZE - scaled_h) // 2

            dot_x = offset_x + int(target_pos[0] * scaled_w / orig_w)
            dot_y = offset_y + int(target_pos[1] * scaled_h / orig_h)

            canvas = QPixmap(self.PREVIEW_SIZE, self.PREVIEW_SIZE)
            canvas.fill(Qt.transparent)
            painter = QPainter(canvas)
            painter.drawPixmap(offset_x, offset_y, scaled)

            r = 4
            painter.setBrush(QBrush(QColor(255, 60, 60, 220)))
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.drawEllipse(dot_x - r, dot_y - r, r * 2, r * 2)
            painter.end()
            self._preview_label.setPixmap(canvas)
        else:
            self._preview_label.setPixmap(scaled)

    def _refresh_preview_from_path(self, image_path: str):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self._set_preview_pixmap(pixmap)
        else:
            self._preview_label.setText("图片加载失败")

    def _choose_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片文件", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        if not file_path or not os.path.exists(file_path):
            return

        import uuid
        temp_dir = os.path.join(self._data_manager._data_dir, "images")
        os.makedirs(temp_dir, exist_ok=True)
        self._cleanup_temp()
        temp_path = os.path.join(temp_dir, f"_temp_{uuid.uuid4().hex}.png")
        shutil.copy2(file_path, temp_path)

        self._preview_label.setProperty("_temp_path", temp_path)
        self._refresh_preview_from_path(temp_path)

    def _start_screenshot_selection(self):
        self._screenshot_selector = RegionSelector()
        self._screenshot_selector.region_selected.connect(self._on_screenshot_selected)
        self._screenshot_selector.show()

    def _on_screenshot_selected(self, x: int, y: int, w: int, h: int):
        self._pending_screenshot = (x, y, w, h)

        if not self._region_edit.text().strip():
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.geometry()
                dpr = screen.devicePixelRatio()
                sw = int(screen_geo.width() * dpr)
                sh = int(screen_geo.height() * dpr)
            else:
                sw, sh = 1920, 1080

            EXPAND = 50
            rx = max(0, x - EXPAND)
            ry = max(0, y - EXPAND)
            rw = min(sw - rx, w + 2 * EXPAND)
            rh = min(sh - ry, h + 2 * EXPAND)

            self._region_edit.setText(f"{rx}, {ry}, {rw}, {rh}")
            self._pending_region = (rx, ry, rw, rh)

        import uuid
        temp_dir = os.path.join(self._data_manager._data_dir, "images")
        os.makedirs(temp_dir, exist_ok=True)
        self._cleanup_temp()
        temp_path = os.path.join(temp_dir, f"_temp_{uuid.uuid4().hex}.png")

        engine = VisionEngine(self._data_manager._data_dir)
        engine.capture_and_save(x, y, w, h, temp_path)

        self._preview_label.setProperty("_temp_path", temp_path)
        self._refresh_preview_from_path(temp_path)

    def _on_preview_click(self, event):
        if self._picking_target:
            self._handle_target_pick(event)
            return
        path = self._preview_label.property("_temp_path")
        if not path:
            path = self._preview_label.property("_image_path")
        if path and os.path.exists(path):
            dlg = ImagePreviewDialog(path, self)
            dlg.exec()

    def _start_target_pick(self):
        image_path = self._preview_label.property("_temp_path")
        if not image_path:
            image_path = self._preview_label.property("_image_path")
        if not image_path or not os.path.exists(image_path):
            QMessageBox.warning(self, "提示", "请先截图或选择已有的素材图片")
            return

        self._picking_target = True
        self._target_pick_btn.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; }"
        )
        self._target_pick_btn.setText("选择中...")
        self._target_pick_btn.setToolTip("请在左侧素材图片上点击目标位置，按 Esc 取消")
        self._preview_label.setCursor(Qt.CrossCursor)
        self._preview_label.setToolTip("点击图片选择目标位置，按 Esc 取消")
        self.setFocus()

    def _cancel_target_pick(self):
        self._picking_target = False
        self._target_pick_btn.setStyleSheet("")
        self._target_pick_btn.setText("选点")
        self._target_pick_btn.setToolTip("点击后在素材图片上选择目标位置")
        self._preview_label.setCursor(Qt.ArrowCursor)
        self._preview_label.setToolTip("")

    def _handle_target_pick(self, event):
        image_path = self._preview_label.property("_temp_path")
        if not image_path:
            image_path = self._preview_label.property("_image_path")
        if not image_path or not os.path.exists(image_path):
            self._cancel_target_pick()
            return

        original = QPixmap(image_path)
        if original.isNull():
            self._cancel_target_pick()
            return

        original_w = original.width()
        original_h = original.height()

        scaled = original.scaled(
            self.PREVIEW_SIZE, self.PREVIEW_SIZE,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        scaled_w = scaled.width()
        scaled_h = scaled.height()

        offset_x = (self.PREVIEW_SIZE - scaled_w) // 2
        offset_y = (self.PREVIEW_SIZE - scaled_h) // 2

        click_x = event.position().x() - offset_x
        click_y = event.position().y() - offset_y

        if click_x < 0 or click_x >= scaled_w or click_y < 0 or click_y >= scaled_h:
            self._cancel_target_pick()
            return

        target_x = int(click_x * original_w / scaled_w)
        target_y = int(click_y * original_h / scaled_h)

        self._target_x_edit.setText(str(target_x))
        self._target_y_edit.setText(str(target_y))
        self._pending_target_pos = (target_x, target_y)
        self._cancel_target_pick()

        if image_path and os.path.exists(image_path):
            self._refresh_preview_from_path(image_path)

    def keyPressEvent(self, event):
        if self._picking_target and event.key() == Qt.Key_Escape:
            self._cancel_target_pick()
        super().keyPressEvent(event)

    def _add_material(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入素材名称")
            return

        region = self._parse_region() or self._pending_region or (0, 0, 0, 0)

        image_path = self._preview_label.property("_temp_path")
        if not image_path:
            image_path = self._preview_label.property("_image_path")

        target_pos = self._parse_target_pos()

        material = Material(
            name=name,
            detect_region=region,
            threshold=self._threshold_slider.value() / 100.0,
            target_pos=target_pos,
        )
        self._data_manager.add_material(material, image_path)
        self._cleanup_temp()
        self._refresh_list()
        self._clear_editor()
        self.material_list_changed.emit()

    def _save_material(self):
        if self._current_material is None:
            return
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入素材名称")
            return

        region = self._parse_region() or self._pending_region or (0, 0, 0, 0)

        self._current_material.name = name
        self._current_material.detect_region = region
        self._current_material.threshold = self._threshold_slider.value() / 100.0
        self._current_material.target_pos = self._parse_target_pos()

        image_path = self._preview_label.property("_temp_path")
        self._data_manager.update_material(self._current_material, image_path)
        self._cleanup_temp()
        self._refresh_list()
        self._clear_editor()
        self.material_list_changed.emit()

    def _delete_material(self, material_id: str):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除该素材吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._data_manager.delete_material(material_id)
            self._refresh_list()
            self._clear_editor()
            self.material_list_changed.emit()

    def _test_material(self):
        region = self._parse_region()
        if region is None or region[2] <= 0 or region[3] <= 0:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.geometry()
                dpr = screen.devicePixelRatio()
                region = (0, 0, int(screen_geo.width() * dpr), int(screen_geo.height() * dpr))
            else:
                region = (0, 0, 1920, 1080)

        image_path = self._preview_label.property("_temp_path")
        if not image_path:
            image_path = self._preview_label.property("_image_path")
        if not image_path or not os.path.exists(image_path):
            QMessageBox.warning(self, "提示", "请先截图或选择已有的素材图片")
            return

        threshold = self._threshold_slider.value() / 100.0
        target_pos = self._parse_target_pos()
        engine = VisionEngine(self._data_manager._data_dir)
        found, box = engine.match_template(image_path, region, threshold, target_pos)

        if not found:
            QMessageBox.information(self, "识别结果", "未识别到目标")
            return

        bx, by, bw, bh = box
        target_x, target_y = engine.last_detected_pos
        from ui.detection_overlay import DetectionOverlay
        self._detection_overlay = DetectionOverlay(bx, by, bw, bh, target_x, target_y)
        self._detection_overlay.show()

    def _refresh_list(self):
        self._list_widget.blockSignals(True)
        self._list_widget.clear()
        for m in self._data_manager.materials:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, m.id)

            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 2, 4, 2)
            item_layout.setSpacing(8)

            name_label = QLabel(m.name)
            name_label.setStyleSheet("font-size: 12px;")
            item_layout.addWidget(name_label)
            item_layout.addStretch()

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
            material_id = m.id
            del_btn.clicked.connect(lambda checked=False, mid=material_id: self._delete_material(mid))
            item_layout.addWidget(del_btn)

            item.setSizeHint(item_widget.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, item_widget)

        self._list_widget.blockSignals(False)

    def _on_list_selection(self, row: int):
        if row < 0 or row >= len(self._data_manager.materials):
            self._current_material = None
            self._save_btn.setEnabled(False)
            return

        self._current_material = self._data_manager.materials[row]
        self._save_btn.setEnabled(True)

        self._name_edit.setText(self._current_material.name)
        r = self._current_material.detect_region
        self._region_edit.setText(f"{r[0]}, {r[1]}, {r[2]}, {r[3]}")

        self._threshold_slider.setValue(int(self._current_material.threshold * 100))
        self._threshold_label.setText(f"{int(self._current_material.threshold * 100)}%")

        if self._current_material.target_pos is not None:
            self._target_x_edit.setText(str(self._current_material.target_pos[0]))
            self._target_y_edit.setText(str(self._current_material.target_pos[1]))
        else:
            self._target_x_edit.clear()
            self._target_y_edit.clear()

        img_path = self._data_manager.get_material_image_path(self._current_material)
        if img_path and os.path.exists(img_path):
            self._preview_label.setProperty("_image_path", img_path)
            self._preview_label.setProperty("_temp_path", None)
            self._refresh_preview_from_path(img_path)
        else:
            self._preview_label.setText("无图片")
            self._preview_label.setProperty("_image_path", None)
            self._preview_label.setProperty("_temp_path", None)

    def _clear_editor(self):
        self._cleanup_temp()
        self._current_material = None
        self._save_btn.setEnabled(False)
        self._name_edit.clear()
        self._region_edit.clear()
        self._pending_region = None
        self._pending_screenshot = None
        self._threshold_slider.setValue(75)
        self._threshold_label.setText("75%")
        self._target_x_edit.clear()
        self._target_y_edit.clear()
        self._pending_target_pos = None
        self._picking_target = False
        self._target_pick_btn.setStyleSheet("")
        self._target_pick_btn.setText("选点")
        self._preview_label.setCursor(Qt.ArrowCursor)
        self._preview_label.setToolTip("")
        self._preview_label.setText("无图片")
        self._preview_label.setProperty("_temp_path", None)
        self._preview_label.setProperty("_image_path", None)

    def _cleanup_temp(self):
        temp_path = self._preview_label.property("_temp_path")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass