# Attention State Collector

## 1. What this system does
This project is a local Python data collection tool for behavioural proxy signals that may be useful for later machine-learning experiments on three labels:

- `focused`
- `distracted`
- `fatigued`

It records webcam-derived facial proxy features and mouse/keyboard interaction features, then aggregates them into one row every 10 seconds and appends to:

- `data/attention_state_dataset.csv`

Each row is a fixed-window summary, not a raw frame.

## 2. What this system does not do
- It does **not** diagnose attention disorders, fatigue disorders, or any medical condition.
- It does **not** claim precise gaze tracking or cognitive-state measurement.
- It does **not** train a model in this version.
- It does **not** include any desktop pet or feedback agent in this version.

## 3. Install dependencies (Windows, local)
From `MML/attention_state_collector`:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Run the collector
From `MML/attention_state_collector`:

```powershell
python main.py
```

## Troubleshooting: MediaPipe has no attribute 'solutions'
This collector currently uses the legacy MediaPipe FaceMesh API (`mp.solutions.face_mesh`).
It expects:

- `mediapipe==0.10.21`

If you see the error, close the app and run these commands from `MML/attention_state_collector`:

```powershell
python -m pip uninstall mediapipe -y
python -m pip install --force-reinstall -r requirements.txt
python -c "import mediapipe as mp; print(mp.__version__); print(hasattr(mp, 'solutions'))"
```

Expected output should include:

```text
0.10.21
True
```

Then run:

```powershell
python main.py
```

## 5. How to collect data for focused / distracted / fatigued sessions
1. Fill in metadata fields in the GUI (`participant_id`, `session_id`, label, task info, self-reports).
2. Click **Start Recording**.
3. Keep the selected label condition for the session.
4. Click **Stop Recording** when done.

Suggested protocol:

- `focused`: perform one continuous task with minimal interruption.
- `distracted`: perform the task while intentionally switching context or interrupting yourself.
- `fatigued`: ideally after 30-45 minutes of work/study; self-reported fatigue preferably 4 or 5.
- Target 6-8 minutes per label session.
- With 10-second windows, 6 minutes yields about 36 rows.

## 6. CSV fields and feature meanings

Metadata columns:

- `timestamp`: row creation time.
- `participant_id`, `session_id`, `label`, `task_type`.
- `window_size_sec`, `window_start_time`, `window_end_time`.
- `pre_task_duration_min`.
- `self_report_focus_score`, `self_report_distraction_score`, `self_report_fatigue_score`.
- `condition_note`.

Visual proxy features:

- `face_detected_ratio`: fraction of frames in window with detectable face.
- `screen_facing_ratio`: fraction of detected-face frames with approximate frontal pose.
- `head_yaw_mean`, `head_yaw_std`: approximate horizontal head orientation summary.
- `head_pitch_mean`, `head_pitch_std`: approximate vertical head orientation summary.
- `eyes_open_ratio_mean`: mean eye-openness proxy (EAR-like) across detected frames.
- `blink_count`: number of closure-then-reopen blink events.
- `long_eye_closure_count`: number of closures lasting > 0.5 seconds.
- `face_absence_duration`: longest continuous no-face interval in seconds in that window.

Interaction features:

- `mouse_move_distance`: total mouse path length in pixels.
- `mouse_speed_mean`, `mouse_speed_std`: speed summary from movement events.
- `mouse_click_count`: number of mouse clicks.
- `key_press_count`: number of key press events (no key values stored).
- `interaction_count`: total interaction events (moves + clicks + key presses).
- `inactivity_duration`: longest continuous inactivity interval (seconds) in window.
- `active_time_ratio`: proportion of 1-second bins with at least one interaction.
- `activity_burstiness`: `std(events_per_sec) / (mean(events_per_sec) + 1e-6)`.

## 7. Privacy note
- No raw webcam images or videos are saved by default.
- No keyboard characters/content are saved.
- Only numerical aggregate features and study metadata are written to CSV.

## Project files
- `main.py`: Tkinter GUI and recording orchestration.
- `visual_features.py`: webcam + MediaPipe facial feature extraction.
- `interaction_features.py`: mouse/keyboard event collection with `pynput`.
- `feature_window.py`: 10-second window row building and CSV writes.
- `config.py`: constants and CSV schema.
