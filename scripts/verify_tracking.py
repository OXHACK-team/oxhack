"""Verify installed Tasks APIs, real-image inference and optionally webcam capture."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.request import urlopen
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera",action="store_true",help="Probe the local webcam; no camera images are saved")
    args=parser.parse_args()
    folder=ROOT/"artifacts"
    folder.mkdir(exist_ok=True)
    path=folder/"reference-pose.jpg"
    if not path.exists():
        with urlopen("https://storage.googleapis.com/mediapipe-assets/pose.jpg",timeout=30) as response:
            path.write_bytes(response.read())
    bgr=cv2.imread(str(path))
    if bgr is None:
        raise RuntimeError("Reference image could not be decoded")
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    rgb=cv2.resize(rgb,(640,int(rgb.shape[0]*640/rgb.shape[1])))
    image=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
    hand_path=folder/"reference-hands.jpg"
    if not hand_path.exists():
        with urlopen("https://storage.googleapis.com/mediapipe-tasks/hand_landmarker/woman_hands.jpg",timeout=30) as response:
            hand_path.write_bytes(response.read())
    hand_rgb=cv2.cvtColor(cv2.imread(str(hand_path)),cv2.COLOR_BGR2RGB)
    hand_rgb=cv2.resize(hand_rgb,(640,int(hand_rgb.shape[0]*640/hand_rgb.shape[1])))
    hand_image=mp.Image(image_format=mp.ImageFormat.SRGB,data=hand_rgb)
    report={"python":sys.version.split()[0],"mediapipe":mp.__version__,"opencv":cv2.__version__,"numpy":np.__version__}
    with vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(ROOT/"models/pose_landmarker_lite.task")),
        running_mode=vision.RunningMode.VIDEO,num_poses=2)) as pose, \
         vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(ROOT/"models/hand_landmarker.task")),
        running_mode=vision.RunningMode.VIDEO,num_hands=2)) as hands:
        timings=[]
        for i in range(30):
            start=time.perf_counter()
            result=pose.detect_for_video(image,i*34)
            timings.append((time.perf_counter()-start)*1000)
        report["reference_pose_count"]=len(result.pose_landmarks)
        assert report["reference_pose_count"]>=1,"Expected a person in official pose reference image"
        report["pose_inference_median_ms"]=float(np.median(timings[3:]))
        hand_timings=[]
        for i in range(20):
            start=time.perf_counter()
            hand_result=hands.detect_for_video(hand_image,i*34)
            hand_timings.append((time.perf_counter()-start)*1000)
        report["reference_hand_count"]=len(hand_result.hand_landmarks)
        assert report["reference_hand_count"]>=1,"Expected hands in official hand reference image"
        report["hand_inference_median_ms"]=float(np.median(hand_timings[3:]))
        blank=mp.Image(image_format=mp.ImageFormat.SRGB,data=np.zeros((480,640,3),np.uint8))
        assert not pose.detect_for_video(blank,2000).pose_landmarks
        assert not hands.detect_for_video(blank,2000).hand_landmarks
        report["blank_image_rejected"]=True
        # A generated test fixture made from two copies of Google's reference
        # photograph exercises multi-pose output without saving camera imagery.
        double=np.ascontiguousarray(np.concatenate([rgb,rgb],axis=1))
        both=mp.Image(image_format=mp.ImageFormat.SRGB,data=double)
        report["two_body_reference_count"]=len(pose.detect_for_video(both,3000).pose_landmarks)
        assert report["two_body_reference_count"]==2,"The multi-person model did not return two reference bodies"
    if args.camera:
        from camera import Camera
        from config import Config
        from pose_tracker import PoseTracker
        camera=Camera(Config())
        tracker=PoseTracker(camera,Config())
        camera.start()
        tracker.start()
        end=time.perf_counter()+5
        try:
            while camera.latest() is None and camera.thread.is_alive() and time.perf_counter()<end:
                time.sleep(.05)
            frame=camera.latest()
            report["camera_available"]=frame is not None
            report["camera_status"]=camera.status
            if frame is not None:
                report["camera_frame_shape"]=list(frame[1].shape)
                deadline=time.perf_counter()+3
                stamps=set()
                latest=None
                while time.perf_counter()<deadline:
                    sample=tracker.latest()
                    if sample.frame is not None:
                        stamps.add(sample.timestamp)
                        latest=sample
                    time.sleep(.01)
                report["live_inference_frames_3s"]=len(stamps)
                report["live_tracker_status"]=tracker.latest().status
                report["live_inference_last_ms"]=latest.inference_ms if latest else None
                assert stamps,"Webcam frames did not reach the inference worker"
        finally:
            tracker.close()
            camera.close()
        report["camera_worker_stopped"]=not camera.thread.is_alive()
        report["tracking_worker_stopped"]=not tracker.thread.is_alive()
        assert report["camera_worker_stopped"] and report["tracking_worker_stopped"],"A capture/inference worker did not release cleanly"
    (folder/"tracking-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
