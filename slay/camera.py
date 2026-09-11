import cv2
import os
import queue
import subprocess
import numpy as np
from multiprocessing import Process, Event
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FRAME_QUEUE_SIZE = 150


class _MJPEGRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while not self.server.stop_event.is_set():
                with self.server.frame_lock:
                    frame = self.server.latest_frame
                if frame is None:
                    time.sleep(0.05)
                    continue
                ok, jpeg = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                jpeg_bytes = jpeg.tobytes()
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg_bytes)}\r\n\r\n".encode())
                self.wfile.write(jpeg_bytes)
                self.wfile.write(b"\r\n")
                time.sleep(1 / self.server.stream_fps)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # das Loggen jedes einzelnen Requests wäre hier nur Rauschen
    def log_message(self, format, *args):
        pass


class USBCamera:

    def __init__(
        self,
        device_path: str,
        output_path: str,
        frame_width=640,
        frame_height=480,
        capture_fps=30,
        # anders als mp4v in VSCode abspielbar. Braucht dafür ffmpeg
        video_codec="libx264",
        # None deaktiviert das Streaming
        stream_port=8989,
        stream_fps=15,
    ):

        self.device_path = device_path
        self.output_path = output_path
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.capture_fps = capture_fps
        self.video_codec = video_codec
        self.stream_port = stream_port
        self.stream_fps = stream_fps
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

        http_server = None
        if self.stream_port is not None:
            http_server = ThreadingHTTPServer(
                ("0.0.0.0", self.stream_port), _MJPEGRequestHandler
            )
            http_server.stop_event = self.stop_event
            http_server.frame_lock = threading.Lock()
            http_server.latest_frame = None
            http_server.stream_fps = self.stream_fps
            threading.Thread(target=http_server.serve_forever, daemon=True).start()
            print(
                f"Streaming camera preview on http://0.0.0.0:{self.stream_port}/",
                flush=True,
            )

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        # Frames direkt an ffmpeg geben und nicht bis zum Ende im RAM halten. Resampling macht es dann quasi selbst
        ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pixel_format",
                "bgr24",
                "-video_size",
                f"{self.frame_width}x{self.frame_height}",
                "-framerate",
                str(self.capture_fps),
                "-use_wallclock_as_timestamps",
                "1",
                "-i",
                "-",
                "-fps_mode",
                "vfr",
                "-c:v",
                self.video_codec,
                "-pix_fmt",
                "yuv420p",
                self.output_path + ".mp4",
            ],
            stdin=subprocess.PIPE,
        )

        frame_queue = queue.Queue(maxsize=FRAME_QUEUE_SIZE)
        write_error = []

        def _writer():
            try:
                while True:
                    frame_bytes = frame_queue.get()
                    if frame_bytes is None:
                        break
                    ffmpeg_proc.stdin.write(frame_bytes)
            except BrokenPipeError:
                write_error.append("ffmpeg terminated early while writing the video.")

        writer_thread = threading.Thread(target=_writer, daemon=True)
        writer_thread.start()

        ts_list = []
        try:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print("Could not read frame. Stopping.")
                    break

                ts_list.append(time.time())
                # tobytes() kopiert bereits, ein zusätzliches frame.copy() ist nicht nötig
                frame_bytes = frame.tobytes()
                while True:
                    try:
                        frame_queue.put(frame_bytes, timeout=1)
                        break
                    except queue.Full:
                        if not writer_thread.is_alive():
                            raise RuntimeError(
                                "ffmpeg writer thread died, stopping capture."
                            )

                if http_server is not None:
                    with http_server.frame_lock:
                        http_server.latest_frame = frame
        except KeyboardInterrupt:
            print("KeyboardInterrupt in camera: terminating")
        except RuntimeError as e:
            print(e)
        finally:
            cap.release()
            if http_server is not None:
                http_server.shutdown()

            try:
                frame_queue.put_nowait(None)
            except queue.Full:
                pass  # writer_thread ist bereits tot (siehe write_error) und liest nicht mehr
            writer_thread.join()
            ffmpeg_proc.stdin.close()
            if ffmpeg_proc.wait() != 0:
                print(f"ffmpeg exited with code {ffmpeg_proc.returncode}.")
            for msg in write_error:
                print(msg)

        ts_arr = np.array(ts_list, dtype=np.float64)
        np.save(self.output_path + "-cam-timestamps.npy", ts_arr)
