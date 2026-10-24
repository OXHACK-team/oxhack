import unittest
from unittest.mock import Mock, patch
import numpy as np
import cv2
from camera import Camera
from config import Config


class CameraTests(unittest.TestCase):
    def test_camera_unavailable_is_helpful_and_releases(self):
        cap=Mock()
        cap.isOpened.return_value=False
        camera=Camera(Config())
        with patch("camera.cv2.VideoCapture",return_value=cap):
            camera._capture()
        self.assertIsNone(camera.latest())
        self.assertIn("permissions",camera.status)
        cap.release.assert_called_once()

    def test_capture_mirrors_exactly_once_and_converts_to_rgb(self):
        camera=Camera(Config())
        bgr=np.array([[[10,20,30],[40,50,60],[70,80,90]]],dtype=np.uint8)
        cap=Mock()
        cap.isOpened.return_value=True
        def read():
            camera._stop.set()
            return True,bgr
        cap.read.side_effect=read
        with patch("camera.cv2.VideoCapture",return_value=cap):
            camera._capture()
        np.testing.assert_array_equal(camera.latest()[1],bgr[:,::-1,::-1])
        cap.release.assert_called_once()

    def test_permission_or_backend_exception_is_nonfatal(self):
        camera=Camera(Config())
        with patch("camera.cv2.VideoCapture",side_effect=cv2.error("access denied")):
            camera._capture()
        self.assertIn("Camera error",camera.status)
        self.assertIn("F2",camera.status)


if __name__=="__main__":
    unittest.main()
