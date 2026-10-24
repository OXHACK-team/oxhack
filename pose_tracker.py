"""MediaPipe Tasks VIDEO mode on a dedicated worker, with latest-frame delivery.

Two poses are published for the fixed-lane multiplayer input layer. Solo mode
rejects additional bodies. Hand centers are associated spatially by the input
layer, with pose wrists available when fine hand landmarks are unavailable.
"""
import threading
import time
import numpy as np
from config import ROOT
from tracking_types import TrackingFrame


class PoseTracker:
    def __init__(self, camera, config):
        self.camera, self.config = camera, config
        self._latest = TrackingFrame(time.perf_counter(), status="Loading tracking models...")
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name="mediapipe", daemon=True)
        self.track_hands = True

    def start(self):
        self.thread.start()

    def latest(self):
        with self._lock:
            return self._latest

    def _publish(self, result):
        with self._lock:
            self._latest = result

    def _run(self):
        pose = hands = None
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            pose_path = ROOT / "models/pose_landmarker_lite.task"
            hand_path = ROOT / "models/hand_landmarker.task"
            if not pose_path.exists() or not hand_path.exists():
                raise FileNotFoundError("Models missing. Run python scripts/download_models.py")
            pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(pose_path)),
                running_mode=vision.RunningMode.VIDEO, num_poses=2,
                min_pose_detection_confidence=.55, min_pose_presence_confidence=.55,
                min_tracking_confidence=.55))
            hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(hand_path)),
                running_mode=vision.RunningMode.VIDEO, num_hands=2))
            last_stamp = 0
            while not self._stop.is_set():
                captured = self.camera.latest()
                if captured is None or int(captured[0] * 1000) <= last_stamp:
                    self._stop.wait(.004)
                    continue
                timestamp, rgb = captured
                last_stamp = int(timestamp * 1000)
                started = time.perf_counter()
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                detected = pose.detect_for_video(image, last_stamp)
                points = None
                centers = []
                count = len(detected.pose_landmarks)
                all_poses=[np.array([[p.x,p.y,p.z,p.visibility] for p in body]) for body in detected.pose_landmarks]
                if count >= 1:
                    points = all_poses[0] if count==1 else None
                    if self.track_hands:
                        result = hands.detect_for_video(image, last_stamp)
                        centers = [np.mean([[h[i].x, h[i].y] for i in (0, 5, 9, 13, 17)], axis=0) for h in result.hand_landmarks]
                status = "Player visible" if count == 1 else "Only one player in the camera, please" if count > 1 else "Step back until your whole body is visible"
                self._publish(TrackingFrame(timestamp, points, rgb, centers, count, status,
                                             (time.perf_counter() - started) * 1000, rgb.shape[1] / rgb.shape[0],all_poses))
        except Exception as exc:
            self._publish(TrackingFrame(time.perf_counter(), status=f"Tracking unavailable: {exc}. Press F2 for demo."))
        finally:
            if hands is not None:
                hands.close()
            if pose is not None:
                pose.close()

    def close(self):
        self._stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=5)
