import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time
from slay.spectrum_plot import SpectrumPlot


class LivePlotter:
    def __init__(self, use_grid=False):
        # self.fig, self.ax = plt.subplots()
        # self.data = []

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
        """Plottet die aktuell gemessene Messung."""
        if messdata.stop_event.is_set() and hasattr(self, "live_ani"):
            try:
                self.live_ani.event_source.stop()
                # self.live_ani.pause()
                plt.close(self.live_fig)
            except AttributeError as e:
                print("Error stopping animation:", e, flush=True)
            return

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

    def start(self, frames, interval, messdata_ref):
        """Starts live plotting."""
        self.live_ani = FuncAnimation(
            fig=self.live_fig,
            func=self.update_plot,
            frames=frames,
            interval=interval,
            fargs=(messdata_ref,),
            repeat=False,
            cache_frame_data=False,
            # RuntimeError: The animation function must return a sequence of Artist objects.
            # blit=True,
        )
        plt.show()
