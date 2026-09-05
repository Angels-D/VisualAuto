import cv2
import numpy as np
import mss
import os


class VisionEngine:
    def __init__(self, data_dir: str = "data"):
        self._data_dir = data_dir
        self._sct = mss.mss()
        self._last_detected_pos: tuple[int, int] | None = None

    @property
    def last_detected_pos(self) -> tuple[int, int] | None:
        return self._last_detected_pos

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        sct_img = self._sct.grab(monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def capture_and_save(self, x: int, y: int, w: int, h: int, save_path: str):
        img = self.capture_region(x, y, w, h)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cv2.imwrite(save_path, img)

    def match_template(self, template_path: str, region: tuple, threshold: float,
                       target_pos: tuple = None) -> tuple[bool, tuple[int, int] | None]:
        rx, ry, rw, rh = region
        if rw <= 0 or rh <= 0:
            monitor = self._sct.monitors[1]
            rx, ry, rw, rh = monitor["left"], monitor["top"], monitor["width"], monitor["height"]

        if not os.path.exists(template_path):
            return False, None

        screenshot = self.capture_region(rx, ry, rw, rh)
        template = cv2.imread(template_path)
        if template is None:
            return False, None

        th, tw = template.shape[:2]
        sh, sw = screenshot.shape[:2]
        if th > sh or tw > sw:
            return False, None

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            if target_pos is not None:
                target_x = rx + max_loc[0] + target_pos[0]
                target_y = ry + max_loc[1] + target_pos[1]
            else:
                target_x = rx + max_loc[0] + tw // 2
                target_y = ry + max_loc[1] + th // 2
            self._last_detected_pos = (target_x, target_y)
            return True, (rx + max_loc[0], ry + max_loc[1], tw, th)
        else:
            self._last_detected_pos = None
            return False, None

    def draw_detection_box(self, x: int, y: int, w: int, h: int, duration_s: float = 3.0):
        import time
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.rectangle(overlay, (0, 0), (w - 1, h - 1), (0, 255, 0), 3)

        monitor = {"left": x, "top": y, "width": w, "height": h}
        screenshot = self._sct.grab(monitor)
        base = np.array(screenshot)
        base = cv2.cvtColor(base, cv2.COLOR_BGRA2BGR)

        return base, overlay