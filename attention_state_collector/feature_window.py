import csv
import os
from datetime import datetime
from typing import Dict

from config import CSV_COLUMNS


class FeatureWindowWriter:
    """Builds per-window rows and appends them to the dataset CSV."""

    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    def ensure_dataset(self) -> None:
        data_dir = os.path.dirname(self.data_path)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

        if not os.path.exists(self.data_path) or os.path.getsize(self.data_path) == 0:
            with open(self.data_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()

    def append_row(self, row: Dict) -> None:
        with open(self.data_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)

    @staticmethod
    def build_row(
        metadata: Dict,
        window_size_sec: int,
        window_start: float,
        window_end: float,
        visual_features: Dict,
        interaction_features: Dict,
    ) -> Dict:
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "participant_id": metadata["participant_id"],
            "session_id": metadata["session_id"],
            "label": metadata["label"],
            "task_type": metadata["task_type"],
            "window_size_sec": window_size_sec,
            "window_start_time": FeatureWindowWriter._to_iso(window_start),
            "window_end_time": FeatureWindowWriter._to_iso(window_end),
            "pre_task_duration_min": metadata["pre_task_duration_min"],
            "self_report_focus_score": metadata["self_report_focus_score"],
            "self_report_distraction_score": metadata["self_report_distraction_score"],
            "self_report_fatigue_score": metadata["self_report_fatigue_score"],
            "condition_note": metadata["condition_note"],
        }
        row.update(visual_features)
        row.update(interaction_features)
        return row

    @staticmethod
    def ordered_row(row: Dict) -> Dict:
        return {key: row.get(key, "") for key in CSV_COLUMNS}

    @staticmethod
    def _to_iso(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")
