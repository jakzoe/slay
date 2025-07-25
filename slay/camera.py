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

        np.save(
            self.output_path + "-cam-timestamps.npy",
            np.array(ts_list, dtype=np.float64),
        )

        fourcc = cv2.VideoWriter_fourcc(*self.video_codec)
        vw = cv2.VideoWriter(
            self.output_path + ".mp4",
            fourcc,
            self.capture_fps,
            (self.frame_width, self.frame_height),
        )
        for frame in frame_list:
            vw.write(frame)
        vw.release()
