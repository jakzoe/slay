import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time
from slay.spectrum_plot import SpectrumPlot


class LivePlotter:
    def __init__(self, use_grid=False):
        # self.fig, self.ax = plt.subplots()
        # self.data = []
        self.stop_event = threading.Event()

        ####

        self.live_fig, self.live_ax = plt.subplots()
        self.live_ax.set_xlabel("Wellenlänge (nm)")
        self.live_ax.set_ylabel("Intensität (Counts)")
        # self.live_ax.grid(True)
        if use_grid:
            self.live_ax.grid(visible=True, which="both", linestyle="--", linewidth=0.5)
        # weniger Weiß an den Rändern

        # self.scatter = self.live_ax.scatter(
        #     [], [], label="Mittelwert von 0 Messungen", s=5
        # )

        self.past_measurement_index = -1

        # plt.ion()
        # plt.show()
        # self.stop_event = threading.Event()

    def update_plot(self, frame, messdata):
        """Updates the plot every interval."""
        if self.stop_event.is_set():
            plt.close(self.live_fig)
            return

        # self.live_ax.clear()
        # self.live_ax.plot(self.data[-20:])

        # """Plottet die aktuell gemessene Messung."""

        # print(threading.current_thread() == threading.main_thread())

        wav = messdata.wav
        measurements = messdata.measurements

        # trying to calculate a signal to noise ratio...
        # mean_measurement = np.mean(measurements, axis=0)
        # std_measurement = np.std(measurements, axis=0)
        # with np.errstate(divide="ignore", invalid="ignore"):
        #     snr = np.true_divide(std_measurement, mean_measurement)
        #     snr[~np.isfinite(snr)] = 0  # set inf and NaN to 0
        # print(snr)

        curr_measurement_index = messdata.curr_measurement_index
        curr_gradiant = messdata.curr_gradiant

        # debug
        print(
            f"called update_plot with: {frame}, {len(measurements)}, {curr_measurement_index},{self.past_measurement_index}",
            flush=True,
        )

        if (
            len(measurements) == 0
            or curr_measurement_index < 0
            or self.past_measurement_index == curr_measurement_index
        ):
            return

        measurement = measurements[curr_gradiant][curr_measurement_index]

        label = f"Spektrum von Messung {curr_measurement_index + 1}"
        self.live_ax.clear()

        settings = SpectrumPlot.GraphSettings(
            self.live_fig, self.live_ax, wav, measurement, label, True, "black", "-"
        )
        SpectrumPlot.data_to_plot(settings)

        self.past_measurement_index = curr_measurement_index

        # self.live_ax.scatter([], [], label="Mittelwert von 0 Messungen", s=5)

    def start(self, frames, messdata_ref):
        """Starts background data thread and plot animation."""
        # Start animation
        self.ani = FuncAnimation(
            fig=self.live_fig,
            func=self.update_plot,
            interval=25,
            # frames=frames,
            fargs=(messdata_ref,),
        )
        plt.show()  # Blocking call; keep in main thread

    def stop(self):
        """Stop the animation and data collection."""
        self.stop_event.set()
        if hasattr(self, "ani"):
            self.ani.event_source.stop()
