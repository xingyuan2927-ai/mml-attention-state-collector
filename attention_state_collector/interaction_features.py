import math
import threading
import time
from typing import Dict, List, Optional

import numpy as np
from pynput import keyboard, mouse


class InteractionFeatureCollector:
    """Collects mouse/keyboard event metadata (without key contents) and aggregates windows."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: List[Dict] = []
        self._last_mouse_position: Optional[tuple] = None

        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._events.clear()
        self._last_mouse_position = None

        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
        )
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)

        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> None:
        self.running = False
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

    def pop_window_events(self, window_start: float, window_end: float) -> List[Dict]:
        with self._lock:
            window_events = [
                event
                for event in self._events
                if window_start <= event["timestamp"] < window_end
            ]
            self._events = [event for event in self._events if event["timestamp"] >= window_end]
        return window_events

    @staticmethod
    def aggregate_window(
        window_start: float,
        window_end: float,
        events: List[Dict],
        window_size_sec: int,
    ) -> Dict:
        if not events:
            return {
                "mouse_move_distance": 0.0,
                "mouse_speed_mean": 0.0,
                "mouse_speed_std": 0.0,
                "mouse_click_count": 0,
                "key_press_count": 0,
                "interaction_count": 0,
                "inactivity_duration": round(window_end - window_start, 6),
                "active_time_ratio": 0.0,
                "activity_burstiness": 0.0,
            }

        sorted_events = sorted(events, key=lambda event: event["timestamp"])

        mouse_move_events = [event for event in sorted_events if event["type"] == "mouse_move"]
        mouse_click_count = sum(1 for event in sorted_events if event["type"] == "mouse_click")
        key_press_count = sum(1 for event in sorted_events if event["type"] == "key_press")

        mouse_move_distance = float(
            sum(event.get("distance", 0.0) for event in mouse_move_events)
        )
        mouse_speeds = []
        for i in range(1, len(mouse_move_events)):
            prev = mouse_move_events[i - 1]
            curr = mouse_move_events[i]
            delta_time = curr["timestamp"] - prev["timestamp"]
            if delta_time > 1e-6:
                mouse_speeds.append(curr.get("distance", 0.0) / delta_time)

        mouse_speed_mean = float(np.mean(mouse_speeds)) if mouse_speeds else 0.0
        mouse_speed_std = float(np.std(mouse_speeds)) if mouse_speeds else 0.0

        interaction_count = len(sorted_events)
        inactivity_duration = InteractionFeatureCollector._longest_inactivity_gap(
            window_start, window_end, sorted_events
        )

        # Bins for active_time_ratio and burstiness: 1-second bins across the window.
        bins = [0 for _ in range(window_size_sec)]
        for event in sorted_events:
            bin_index = int(event["timestamp"] - window_start)
            if 0 <= bin_index < window_size_sec:
                bins[bin_index] += 1

        active_bins = sum(1 for count in bins if count > 0)
        active_time_ratio = active_bins / float(window_size_sec)
        activity_burstiness = float(np.std(bins) / (np.mean(bins) + 1e-6))

        return {
            "mouse_move_distance": round(mouse_move_distance, 6),
            "mouse_speed_mean": round(mouse_speed_mean, 6),
            "mouse_speed_std": round(mouse_speed_std, 6),
            "mouse_click_count": int(mouse_click_count),
            "key_press_count": int(key_press_count),
            "interaction_count": int(interaction_count),
            "inactivity_duration": round(inactivity_duration, 6),
            "active_time_ratio": round(active_time_ratio, 6),
            "activity_burstiness": round(activity_burstiness, 6),
        }

    def _on_mouse_move(self, x: int, y: int) -> None:
        if not self.running:
            return

        now = time.time()
        distance = 0.0
        with self._lock:
            if self._last_mouse_position is not None:
                px, py = self._last_mouse_position
                distance = math.hypot(float(x - px), float(y - py))
            self._last_mouse_position = (x, y)
            self._events.append(
                {
                    "timestamp": now,
                    "type": "mouse_move",
                    "distance": distance,
                }
            )

    def _on_mouse_click(self, x: int, y: int, button, pressed: bool) -> None:
        if not self.running or not pressed:
            return
        with self._lock:
            self._events.append({"timestamp": time.time(), "type": "mouse_click"})

    def _on_key_press(self, _key) -> None:
        if not self.running:
            return
        # Privacy: key values are intentionally ignored; only count press events.
        with self._lock:
            self._events.append({"timestamp": time.time(), "type": "key_press"})

    @staticmethod
    def _longest_inactivity_gap(window_start: float, window_end: float, events: List[Dict]) -> float:
        if not events:
            return window_end - window_start

        timestamps = [event["timestamp"] for event in events]
        max_gap = max(0.0, timestamps[0] - window_start)
        for i in range(1, len(timestamps)):
            max_gap = max(max_gap, timestamps[i] - timestamps[i - 1])
        max_gap = max(max_gap, window_end - timestamps[-1])
        return max_gap
