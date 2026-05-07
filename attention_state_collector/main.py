import threading
import time
import tkinter as tk
from queue import Empty, Queue
from tkinter import messagebox, ttk
from typing import Dict, Optional

from config import (
    CAMERA_INDEX,
    DATA_PATH,
    EYE_CLOSURE_THRESHOLD,
    LONG_EYE_CLOSURE_SEC,
    SCREEN_FACING_PITCH_THRESHOLD,
    SCREEN_FACING_YAW_THRESHOLD,
    VALID_LABELS,
    WINDOW_SIZE_SEC,
)
from feature_window import FeatureWindowWriter
from interaction_features import InteractionFeatureCollector
from visual_features import VisualFeatureExtractor


class AttentionStateCollectorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Attention State Collector")
        self.root.geometry("760x620")

        self.writer = FeatureWindowWriter(DATA_PATH)
        self.writer.ensure_dataset()
        self.ui_queue: Queue = Queue()

        self.visual_extractor: Optional[VisualFeatureExtractor] = None
        self.interaction_collector: Optional[InteractionFeatureCollector] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.recording_active = False
        self.recording_start_time = 0.0
        self.current_window_start = 0.0
        self.next_window_end = 0.0
        self.saved_window_count = 0
        self.session_metadata: Dict = {}

        self._build_ui()
        self._update_timer()
        self._process_ui_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(container, text="Session Setup", padding=12)
        form.pack(fill=tk.X, pady=(0, 12))

        self.participant_id_var = tk.StringVar()
        self.session_id_var = tk.StringVar()
        self.label_var = tk.StringVar(value=VALID_LABELS[0])
        self.task_type_var = tk.StringVar(value="coding")
        self.pre_task_duration_min_var = tk.StringVar(value="0")
        self.self_report_focus_var = tk.StringVar(value="3")
        self.self_report_distraction_var = tk.StringVar(value="3")
        self.self_report_fatigue_var = tk.StringVar(value="3")
        self.condition_note_var = tk.StringVar()

        self._add_form_row(form, 0, "participant_id", ttk.Entry(form, textvariable=self.participant_id_var))
        self._add_form_row(form, 1, "session_id", ttk.Entry(form, textvariable=self.session_id_var))
        self._add_form_row(
            form,
            2,
            "label",
            ttk.Combobox(form, textvariable=self.label_var, values=list(VALID_LABELS), state="readonly"),
        )
        self._add_form_row(form, 3, "task_type", ttk.Entry(form, textvariable=self.task_type_var))
        self._add_form_row(
            form, 4, "pre_task_duration_min", ttk.Entry(form, textvariable=self.pre_task_duration_min_var)
        )
        self._add_form_row(
            form, 5, "self_report_focus_score (1-5)", ttk.Entry(form, textvariable=self.self_report_focus_var)
        )
        self._add_form_row(
            form,
            6,
            "self_report_distraction_score (1-5)",
            ttk.Entry(form, textvariable=self.self_report_distraction_var),
        )
        self._add_form_row(
            form, 7, "self_report_fatigue_score (1-5)", ttk.Entry(form, textvariable=self.self_report_fatigue_var)
        )
        self._add_form_row(form, 8, "condition_note (optional)", ttk.Entry(form, textvariable=self.condition_note_var))

        controls = ttk.Frame(container)
        controls.pack(fill=tk.X, pady=(0, 12))
        self.start_button = ttk.Button(controls, text="Start Recording", command=self.start_recording)
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_button = ttk.Button(
            controls, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT)

        monitor = ttk.LabelFrame(container, text="Live Status", padding=12)
        monitor.pack(fill=tk.BOTH, expand=True)

        self.current_label_display_var = tk.StringVar(value="-")
        self.timer_var = tk.StringVar(value="00:00")
        self.saved_windows_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="idle")

        self._add_status_row(monitor, 0, "Current label", self.current_label_display_var)
        self._add_status_row(monitor, 1, "Recording timer", self.timer_var)
        self._add_status_row(monitor, 2, "Saved windows", self.saved_windows_var)
        self._add_status_row(monitor, 3, "Status", self.status_var)

    @staticmethod
    def _add_form_row(parent, row_index: int, label_text: str, widget) -> None:
        ttk.Label(parent, text=label_text).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=4)
        widget.grid(row=row_index, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)

    @staticmethod
    def _add_status_row(parent, row_index: int, label_text: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=f"{label_text}:").grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Label(parent, textvariable=variable).grid(row=row_index, column=1, sticky="w", pady=5)
        parent.columnconfigure(1, weight=1)

    def _collect_metadata(self) -> Dict:
        participant_id = self.participant_id_var.get().strip()
        session_id = self.session_id_var.get().strip()
        label = self.label_var.get().strip()
        task_type = self.task_type_var.get().strip()
        condition_note = self.condition_note_var.get().strip()

        if not participant_id:
            raise ValueError("participant_id is required.")
        if not session_id:
            raise ValueError("session_id is required.")
        if label not in VALID_LABELS:
            raise ValueError("label must be one of: focused / distracted / fatigued.")
        if not task_type:
            raise ValueError("task_type is required.")

        pre_task_duration_min = float(self.pre_task_duration_min_var.get().strip())
        if pre_task_duration_min < 0:
            raise ValueError("pre_task_duration_min must be >= 0.")

        self_report_focus = int(self.self_report_focus_var.get().strip())
        self_report_distraction = int(self.self_report_distraction_var.get().strip())
        self_report_fatigue = int(self.self_report_fatigue_var.get().strip())

        for value, name in [
            (self_report_focus, "self_report_focus_score"),
            (self_report_distraction, "self_report_distraction_score"),
            (self_report_fatigue, "self_report_fatigue_score"),
        ]:
            if value < 1 or value > 5:
                raise ValueError(f"{name} must be in range 1 to 5.")

        return {
            "participant_id": participant_id,
            "session_id": session_id,
            "label": label,
            "task_type": task_type,
            "pre_task_duration_min": pre_task_duration_min,
            "self_report_focus_score": self_report_focus,
            "self_report_distraction_score": self_report_distraction,
            "self_report_fatigue_score": self_report_fatigue,
            "condition_note": condition_note,
        }

    def start_recording(self) -> None:
        if self.recording_active:
            return

        try:
            self.session_metadata = self._collect_metadata()
            self.writer.ensure_dataset()
        except Exception as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        self.visual_extractor = VisualFeatureExtractor(
            camera_index=CAMERA_INDEX,
            eye_closure_threshold=EYE_CLOSURE_THRESHOLD,
            long_eye_closure_sec=LONG_EYE_CLOSURE_SEC,
            screen_facing_yaw_threshold=SCREEN_FACING_YAW_THRESHOLD,
            screen_facing_pitch_threshold=SCREEN_FACING_PITCH_THRESHOLD,
        )
        self.interaction_collector = InteractionFeatureCollector()

        try:
            self.visual_extractor.start()
        except Exception as exc:
            self.status_var.set("visual setup error")
            messagebox.showerror(
                "Visual Setup Error",
                f"Failed to start visual extraction (webcam + MediaPipe).\n\n{exc}",
            )
            return

        try:
            self.interaction_collector.start()
        except Exception as exc:
            self.visual_extractor.stop()
            self.status_var.set("listener error")
            messagebox.showerror("Listener Error", f"Failed to start input listeners.\n\n{exc}")
            return

        self.saved_window_count = 0
        self.saved_windows_var.set("0")
        self.current_label_display_var.set(self.session_metadata["label"])
        self.stop_event.clear()

        self.recording_start_time = time.time()
        self.current_window_start = self.recording_start_time
        self.next_window_end = self.current_window_start + WINDOW_SIZE_SEC
        self.recording_active = True

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("camera active")

        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()

    def stop_recording(self) -> None:
        if not self.recording_active:
            return
        self.status_var.set("stopping")
        self.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)

    def _record_loop(self) -> None:
        error_message = None
        last_status_update = 0.0

        try:
            while not self.stop_event.is_set():
                ok, face_detected = self.visual_extractor.capture_and_process_frame()
                now = time.time()

                if not ok:
                    error_message = "Webcam frame capture failed."
                    break

                if now - last_status_update >= 1.0:
                    status = "camera active | face detected" if face_detected else "camera active | no face detected"
                    self._set_status(status)
                    last_status_update = now

                while now >= self.next_window_end and not self.stop_event.is_set():
                    self._set_status("saving data")
                    self._save_one_window(self.current_window_start, self.next_window_end)
                    self.current_window_start = self.next_window_end
                    self.next_window_end += WINDOW_SIZE_SEC
        except Exception as exc:
            error_message = f"Recording loop error: {exc}"
        finally:
            stop_time = time.time()
            while stop_time >= self.next_window_end:
                try:
                    self._set_status("saving data")
                    self._save_one_window(self.current_window_start, self.next_window_end)
                    self.current_window_start = self.next_window_end
                    self.next_window_end += WINDOW_SIZE_SEC
                except Exception as exc:
                    error_message = error_message or f"Failed while saving window: {exc}"
                    break

            if self.interaction_collector is not None:
                self.interaction_collector.stop()
            if self.visual_extractor is not None:
                self.visual_extractor.stop()

            self.recording_active = False
            self._post_ui(self._on_recording_finished, error_message)

    def _save_one_window(self, window_start: float, window_end: float) -> None:
        window_frames, blinks, long_closures = self.visual_extractor.pop_window_data(
            window_start, window_end
        )
        visual_features = self.visual_extractor.aggregate_window(
            window_start, window_end, window_frames, blinks, long_closures
        )

        events = self.interaction_collector.pop_window_events(window_start, window_end)
        interaction_features = self.interaction_collector.aggregate_window(
            window_start, window_end, events, WINDOW_SIZE_SEC
        )

        row = self.writer.build_row(
            metadata=self.session_metadata,
            window_size_sec=WINDOW_SIZE_SEC,
            window_start=window_start,
            window_end=window_end,
            visual_features=visual_features,
            interaction_features=interaction_features,
        )
        self.writer.append_row(self.writer.ordered_row(row))

        self.saved_window_count += 1
        self._post_ui(self.saved_windows_var.set, str(self.saved_window_count))

    def _set_status(self, text: str) -> None:
        self._post_ui(self.status_var.set, text)

    def _on_recording_finished(self, error_message: Optional[str]) -> None:
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("stopped" if error_message is None else "error")

        if error_message:
            messagebox.showerror("Recording Error", error_message)
        else:
            messagebox.showinfo(
                "Recording Complete",
                f"Recording stopped successfully.\nSaved windows: {self.saved_window_count}",
            )

    def _update_timer(self) -> None:
        if self.recording_active:
            elapsed = int(time.time() - self.recording_start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.timer_var.set(f"{minutes:02d}:{seconds:02d}")
        self.root.after(500, self._update_timer)

    def _post_ui(self, callback, *args, **kwargs) -> None:
        self.ui_queue.put((callback, args, kwargs))

    def _process_ui_queue(self) -> None:
        while True:
            try:
                callback, args, kwargs = self.ui_queue.get_nowait()
            except Empty:
                break
            callback(*args, **kwargs)
        self.root.after(100, self._process_ui_queue)

    def _on_close(self) -> None:
        if self.recording_active:
            should_close = messagebox.askyesno(
                "Exit",
                "Recording is active. Stop recording and exit?",
            )
            if not should_close:
                return
            self.stop_event.set()
            if self.recording_thread is not None and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            if self.interaction_collector is not None:
                self.interaction_collector.stop()
            if self.visual_extractor is not None:
                self.visual_extractor.stop()
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    app = AttentionStateCollectorApp(app_root)
    app_root.mainloop()
