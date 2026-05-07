import threading
import time
import sys
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np


class VisualFeatureExtractor:
    """Collects frame-level visual proxy signals and provides window aggregation."""

    LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
    NOSE_TIP_IDX = 1
    LEFT_CHEEK_IDX = 234
    RIGHT_CHEEK_IDX = 454
    FOREHEAD_IDX = 10
    CHIN_IDX = 152

    def __init__(
        self,
        camera_index: int,
        eye_closure_threshold: float,
        long_eye_closure_sec: float,
        screen_facing_yaw_threshold: float,
        screen_facing_pitch_threshold: float,
    ) -> None:
        self.camera_index = camera_index
        self.eye_closure_threshold = eye_closure_threshold
        self.long_eye_closure_sec = long_eye_closure_sec
        self.screen_facing_yaw_threshold = screen_facing_yaw_threshold
        self.screen_facing_pitch_threshold = screen_facing_pitch_threshold

        self.cap: Optional[cv2.VideoCapture] = None
        self.face_mesh = None
        self.running = False

        self._lock = threading.Lock()
        self._frame_samples: List[Dict] = []
        self._blink_events: List[float] = []
        self._long_closure_events: List[float] = []

        self._eye_closed = False
        self._closure_start_time: Optional[float] = None
        self._long_closure_recorded = False

    def start(self) -> None:
        print(f"Python version: {sys.version}")
        print(f"MediaPipe version: {getattr(mp, '__version__', 'unknown')}")
        print(f"MediaPipe has solutions API: {hasattr(mp, 'solutions')}")
        print(f"OpenCV version: {cv2.__version__}")

        has_solutions = hasattr(mp, "solutions")
        has_face_mesh = has_solutions and hasattr(mp.solutions, "face_mesh")
        if not has_face_mesh:
            raise RuntimeError(
                "This collector uses the legacy MediaPipe FaceMesh API: "
                "mp.solutions.face_mesh. Your installed MediaPipe version does not include "
                "mp.solutions. Please reinstall dependencies with: python -m pip install "
                "--force-reinstall -r requirements.txt. The project expects mediapipe==0.10.21."
            )

        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Unable to open webcam at CAMERA_INDEX={self.camera_index}."
            )

        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.running = True

    def stop(self) -> None:
        self.running = False
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def capture_and_process_frame(self) -> Tuple[bool, bool]:
        if not self.running or self.cap is None:
            return False, False

        ok, frame = self.cap.read()
        if not ok:
            return False, False

        timestamp = time.time()
        face_detected = self._process_frame(frame, timestamp)
        return True, face_detected

    def pop_window_data(
        self, window_start: float, window_end: float
    ) -> Tuple[List[Dict], List[float], List[float]]:
        with self._lock:
            window_frames = [
                sample
                for sample in self._frame_samples
                if window_start <= sample["timestamp"] < window_end
            ]
            self._frame_samples = [
                sample for sample in self._frame_samples if sample["timestamp"] >= window_end
            ]

            blinks = [t for t in self._blink_events if window_start <= t < window_end]
            self._blink_events = [t for t in self._blink_events if t >= window_end]

            long_closures = [
                t for t in self._long_closure_events if window_start <= t < window_end
            ]
            self._long_closure_events = [
                t for t in self._long_closure_events if t >= window_end
            ]

        return window_frames, blinks, long_closures

    def aggregate_window(
        self,
        window_start: float,
        window_end: float,
        window_frames: List[Dict],
        blinks: List[float],
        long_closures: List[float],
    ) -> Dict:
        if not window_frames:
            return {
                "face_detected_ratio": 0.0,
                "screen_facing_ratio": 0.0,
                "head_yaw_mean": 0.0,
                "head_yaw_std": 0.0,
                "head_pitch_mean": 0.0,
                "head_pitch_std": 0.0,
                "eyes_open_ratio_mean": 0.0,
                "blink_count": len(blinks),
                "long_eye_closure_count": len(long_closures),
                "face_absence_duration": round(window_end - window_start, 4),
            }

        total_frames = len(window_frames)
        detected_frames = [frame for frame in window_frames if frame["face_detected"]]

        face_detected_ratio = len(detected_frames) / total_frames if total_frames else 0.0
        screen_facing_ratio = (
            sum(1 for frame in detected_frames if frame["screen_facing"]) / len(detected_frames)
            if detected_frames
            else 0.0
        )

        yaw_values = [frame["head_yaw"] for frame in detected_frames if frame["head_yaw"] is not None]
        pitch_values = [
            frame["head_pitch"] for frame in detected_frames if frame["head_pitch"] is not None
        ]
        eye_values = [
            frame["eyes_open_ratio"]
            for frame in detected_frames
            if frame["eyes_open_ratio"] is not None
        ]

        head_yaw_mean = float(np.mean(yaw_values)) if yaw_values else 0.0
        head_yaw_std = float(np.std(yaw_values)) if yaw_values else 0.0
        head_pitch_mean = float(np.mean(pitch_values)) if pitch_values else 0.0
        head_pitch_std = float(np.std(pitch_values)) if pitch_values else 0.0
        eyes_open_ratio_mean = float(np.mean(eye_values)) if eye_values else 0.0

        face_absence_duration = self._longest_face_absence_duration(
            window_start, window_end, window_frames
        )

        return {
            "face_detected_ratio": round(face_detected_ratio, 6),
            "screen_facing_ratio": round(screen_facing_ratio, 6),
            "head_yaw_mean": round(head_yaw_mean, 6),
            "head_yaw_std": round(head_yaw_std, 6),
            "head_pitch_mean": round(head_pitch_mean, 6),
            "head_pitch_std": round(head_pitch_std, 6),
            "eyes_open_ratio_mean": round(eyes_open_ratio_mean, 6),
            "blink_count": len(blinks),
            "long_eye_closure_count": len(long_closures),
            "face_absence_duration": round(face_absence_duration, 6),
        }

    def _process_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        face_detected = bool(results.multi_face_landmarks)
        screen_facing = False
        head_yaw = None
        head_pitch = None
        eyes_open_ratio = None

        if face_detected:
            face_landmarks = results.multi_face_landmarks[0].landmark
            head_yaw, head_pitch = self._estimate_head_yaw_pitch(face_landmarks)
            eyes_open_ratio = self._eye_openness_proxy(face_landmarks)

            if head_yaw is not None and head_pitch is not None:
                screen_facing = (
                    abs(head_yaw) < self.screen_facing_yaw_threshold
                    and abs(head_pitch) < self.screen_facing_pitch_threshold
                )
            self._update_blink_state(eyes_open_ratio, timestamp)
        else:
            self._reset_eye_state()

        with self._lock:
            self._frame_samples.append(
                {
                    "timestamp": timestamp,
                    "face_detected": face_detected,
                    "screen_facing": screen_facing,
                    "head_yaw": head_yaw,
                    "head_pitch": head_pitch,
                    "eyes_open_ratio": eyes_open_ratio,
                }
            )

        return face_detected

    def _estimate_head_yaw_pitch(self, landmarks) -> Tuple[Optional[float], Optional[float]]:
        """Approximate yaw/pitch from landmark geometry (not full 3D pose estimation)."""
        try:
            nose = landmarks[self.NOSE_TIP_IDX]
            left_cheek = landmarks[self.LEFT_CHEEK_IDX]
            right_cheek = landmarks[self.RIGHT_CHEEK_IDX]
            forehead = landmarks[self.FOREHEAD_IDX]
            chin = landmarks[self.CHIN_IDX]
        except IndexError:
            return None, None

        half_face_width = max(abs(right_cheek.x - left_cheek.x) / 2.0, 1e-6)
        face_mid_x = (left_cheek.x + right_cheek.x) / 2.0
        yaw = np.degrees(np.arctan2((nose.x - face_mid_x), half_face_width))

        half_face_height = max(abs(chin.y - forehead.y) / 2.0, 1e-6)
        face_mid_y = (forehead.y + chin.y) / 2.0
        pitch = np.degrees(np.arctan2((nose.y - face_mid_y), half_face_height))

        return float(yaw), float(pitch)

    def _eye_openness_proxy(self, landmarks) -> Optional[float]:
        left_ear = self._eye_aspect_ratio(landmarks, self.LEFT_EYE_IDX)
        right_ear = self._eye_aspect_ratio(landmarks, self.RIGHT_EYE_IDX)

        if left_ear is None or right_ear is None:
            return None
        return float((left_ear + right_ear) / 2.0)

    @staticmethod
    def _eye_aspect_ratio(landmarks, idx: List[int]) -> Optional[float]:
        try:
            p1 = np.array([landmarks[idx[0]].x, landmarks[idx[0]].y], dtype=np.float32)
            p2 = np.array([landmarks[idx[1]].x, landmarks[idx[1]].y], dtype=np.float32)
            p3 = np.array([landmarks[idx[2]].x, landmarks[idx[2]].y], dtype=np.float32)
            p4 = np.array([landmarks[idx[3]].x, landmarks[idx[3]].y], dtype=np.float32)
            p5 = np.array([landmarks[idx[4]].x, landmarks[idx[4]].y], dtype=np.float32)
            p6 = np.array([landmarks[idx[5]].x, landmarks[idx[5]].y], dtype=np.float32)
        except IndexError:
            return None

        horizontal = np.linalg.norm(p1 - p4)
        if horizontal < 1e-6:
            return None

        vertical = np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)
        return float(vertical / (2.0 * horizontal))

    def _update_blink_state(self, eye_ratio: Optional[float], timestamp: float) -> None:
        if eye_ratio is None:
            self._reset_eye_state()
            return

        if eye_ratio < self.eye_closure_threshold:
            if not self._eye_closed:
                self._eye_closed = True
                self._closure_start_time = timestamp
                self._long_closure_recorded = False
            elif (
                not self._long_closure_recorded
                and self._closure_start_time is not None
                and (timestamp - self._closure_start_time) >= self.long_eye_closure_sec
            ):
                with self._lock:
                    self._long_closure_events.append(timestamp)
                self._long_closure_recorded = True
            return

        if self._eye_closed and self._closure_start_time is not None:
            with self._lock:
                self._blink_events.append(timestamp)
        self._reset_eye_state()

    def _reset_eye_state(self) -> None:
        self._eye_closed = False
        self._closure_start_time = None
        self._long_closure_recorded = False

    @staticmethod
    def _longest_face_absence_duration(
        window_start: float, window_end: float, frames: List[Dict]
    ) -> float:
        if not frames:
            return window_end - window_start

        sorted_frames = sorted(frames, key=lambda item: item["timestamp"])
        if not any(frame["face_detected"] for frame in sorted_frames):
            return window_end - window_start

        max_absence = 0.0
        absence_start = None

        for index, frame in enumerate(sorted_frames):
            is_face_detected = frame["face_detected"]
            ts = frame["timestamp"]

            if not is_face_detected and absence_start is None:
                absence_start = window_start if index == 0 else ts
            elif is_face_detected and absence_start is not None:
                max_absence = max(max_absence, ts - absence_start)
                absence_start = None

        if absence_start is not None:
            max_absence = max(max_absence, window_end - absence_start)

        return max_absence
