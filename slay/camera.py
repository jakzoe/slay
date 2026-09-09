import cv2
import os
import numpy as np
from multiprocessing import Process, Event
import time


class USBCamera:

    def __init__(
        self,
        device_path: str,
        output_path: str,
        frame_width=640,
        frame_height=480,
        capture_fps=30,
        # supported by VSCode instead of mp4v
        # video_codec="avc1",
        video_codec="mp4v",
    ):

        self.device_path = device_path
        self.output_path = output_path
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.capture_fps = capture_fps
        self.video_codec = video_codec
        self.stop_event = Event()
        self.process = Process(target=self._camera_worker)

    def start(self):
        self.process.start()

    def stop(self):
        self.stop_event.set()
        self.process.join()

    def _camera_worker(self):
        cap = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"Could not open camera at {self.device_path}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self.capture_fps)

        ts_list, frame_list = [], []
        try:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print("Could not read frame. Stopping.")
                    break

                ts_list.append(time.time())
                frame_list.append(frame.copy())

                cv2.imshow(f"{self.device_path} - press q to stop", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.stop_event.set()
                    break
        except KeyboardInterrupt:
            print("KeyboardInterrupt in camera: terminating")
        finally:
            cap.release()
            cv2.destroyAllWindows()

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        ts_arr = np.array(ts_list, dtype=np.float64)
        np.save(self.output_path + "-cam-timestamps.npy", ts_arr)

        # zumindest bei meiner Kamera gibt es sehr sehr starke Abweichungen von den eingestellen FPS, deshalb nochmal ausrechnen
        duration = ts_arr[-1] - ts_arr[0] if len(ts_arr) > 1 else 0
        fps = (len(ts_arr) - 1) / duration if duration > 0 else self.capture_fps

        fourcc = cv2.VideoWriter_fourcc(*self.video_codec)
        vw = cv2.VideoWriter(
            self.output_path + ".mp4",
            fourcc,
            fps,
            (self.frame_width, self.frame_height),
        )
        if frame_list:
            # resampeln auf die timestamps, sonst entspricht die Videozeit nicht den gespeicherten timestamps (frames sind häufig nicht gleichmäßig verteilt)
            n_out_frames = (
                max(1, round(duration * fps)) if duration > 0 else len(frame_list)
            )
            out_timestamps = ts_arr[0] + np.arange(n_out_frames) / fps
            frame_indices = np.clip(
                np.searchsorted(ts_arr, out_timestamps, side="right") - 1,
                0,
                len(frame_list) - 1,
            )
            for idx in frame_indices:
                vw.write(frame_list[idx])
        vw.release()
