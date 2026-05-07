from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

WINDOW_SIZE_SEC = 10
CAMERA_INDEX = 0
EYE_CLOSURE_THRESHOLD = 0.20
LONG_EYE_CLOSURE_SEC = 0.5
SCREEN_FACING_YAW_THRESHOLD = 20
SCREEN_FACING_PITCH_THRESHOLD = 20
DATA_PATH = str(BASE_DIR / "data" / "attention_state_dataset.csv")

VALID_LABELS = ("focused", "distracted", "fatigued")

CSV_COLUMNS = [
    "timestamp",
    "participant_id",
    "session_id",
    "label",
    "task_type",
    "window_size_sec",
    "window_start_time",
    "window_end_time",
    "pre_task_duration_min",
    "self_report_focus_score",
    "self_report_distraction_score",
    "self_report_fatigue_score",
    "condition_note",
    "face_detected_ratio",
    "screen_facing_ratio",
    "head_yaw_mean",
    "head_yaw_std",
    "head_pitch_mean",
    "head_pitch_std",
    "eyes_open_ratio_mean",
    "blink_count",
    "long_eye_closure_count",
    "face_absence_duration",
    "mouse_move_distance",
    "mouse_speed_mean",
    "mouse_speed_std",
    "mouse_click_count",
    "key_press_count",
    "interaction_count",
    "inactivity_duration",
    "active_time_ratio",
    "activity_burstiness",
]
