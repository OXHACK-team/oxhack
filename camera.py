"""A latest-frame camera: no inference or rendering on the capture thread."""
import threading
import time
import sys
import cv2


class Camera:
    def __init__(self, config):
        self.config = config
        self.status = "Opening camera..."
        self._latest = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._capture, name="camera", daemon=True)

    def start(self):
        self.thread.start()

    def latest(self):
        with self._lock:
            return self._latest

    def _capture(self):
        cap = None
        try:
            # DirectShow avoids slow MSMF startup on many Windows laptop cameras.
            cap = cv2.VideoCapture(self.config.camera_index, cv2.CAP_DSHOW) if sys.platform == 'win32' else cv2.VideoCapture(self.config.camera_index)
            if not cap.isOpened():
                self.status = "Camera unavailable. Close other camera apps, check permissions, or press F2 for demo."
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            failures = 0
            while not self._stop.is_set():
                ok, bgr = cap.read()
                if not ok:
                    failures += 1
                    self.status = "Camera signal lost. Reconnect the camera; restart or use F2 demo."
                    if failures > 30:
                        return
                    self._stop.wait(.03)
                    continue
                failures = 0
                rgb = cv2.cvtColor(cv2.flip(bgr, 1), cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._latest = (time.perf_counter(), rgb)
                self.status = "Camera ready"
        except Exception as exc:
            self.status = f"Camera error: {exc}. Press F2 for demo."
        finally:
            if cap is not None:
                cap.release()

    def close(self):
        self._stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
