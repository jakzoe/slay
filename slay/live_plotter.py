import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from slay.spectrum_plot import SpectrumPlot


class LivePlotter:
    def __init__(self, use_grid=False, dual=False):
        # ggf. zweite Achse für zweites Spektrometer
        self.dual = dual
        n_axes = 2 if dual else 1
        # default figsize ist 6.4x4.8 mit scienceplots
        self.live_fig, axes = plt.subplots(1, n_axes, figsize=(6.4 * n_axes, 4.8))
        self.live_axes = list(axes) if dual else [axes]

        for ax in self.live_axes:
            ax.set_xlabel("Wellenlänge (nm)")
            ax.set_ylabel("Intensität (Counts)")
            if use_grid:
                ax.grid(visible=True, which="both", linestyle="--", linewidth=0.5)

        self.past_measurement_index = [-1, -1]

    def _update_axis(self, ax_index, messdata, label_suffix=""):
        ax = self.live_axes[ax_index]

        wav = messdata.wav
        measurements = messdata.measurements
        curr_measurement_index = messdata.curr_measurement_index
        curr_gradiant = messdata.curr_gradiant

        if (
            len(measurements) == 0
            or curr_measurement_index < 0
            or self.past_measurement_index[ax_index] == curr_measurement_index
        ):
            return

        measurement = measurements[curr_gradiant][curr_measurement_index]

        label = f"Spektrum von Messung {curr_measurement_index + 1}{label_suffix}"
        ax.clear()

        settings = SpectrumPlot.GraphSettings(
            self.live_fig, ax, wav, measurement, label, True, "black", "-"
        )
        SpectrumPlot.data_to_plot(settings)

        self.past_measurement_index[ax_index] = curr_measurement_index

    def _finish(self):
        plt.close(self.live_fig)
        # den Server von WebAgg schließen, damit plt.show() nicht mehr blockiert
        if plt.get_backend().lower() == "webagg" and not plt.get_fignums():
            import tornado.ioloop

            tornado.ioloop.IOLoop.instance().stop()

    def update_plot(self, frame, messdata_a, messdata_b=None):
        """Plottet die aktuell gemessenen Messungen (eines oder zweier Spektrometer)."""
        if messdata_a.stop_event.is_set():
            if self.live_ani.event_source is not None:
                self.live_ani.event_source.stop()
            close_timer = self.live_fig.canvas.new_timer(interval=1)
            close_timer.single_shot = True
            close_timer.add_callback(self._finish)
            close_timer.start()
            return

        self._update_axis(0, messdata_a, " (A)" if messdata_b is not None else "")
        if messdata_b is not None:
            self._update_axis(1, messdata_b, " (B)")

    def start(self, frames, interval, messdata_ref, messdata_ref_b=None):
        """Starts live plotting."""

        try:
            self.live_ani = FuncAnimation(
                fig=self.live_fig,
                func=self.update_plot,
                frames=frames,
                interval=interval,
                fargs=(messdata_ref, messdata_ref_b),
                repeat=False,
                cache_frame_data=False,
                # would have to return the artists to use blitting, which I am not doing right now
                # blit=True,
            )
            # die FuncAnimation startet den Timer erst bei dem ersten draw, was bei WebAgg erst geschieht, wenn man die Website aufruft. Macht man nicht immer, daher manuell vorsichtshalber den Timer mit einem Draw starten
            if plt.get_backend().lower() == "webagg":
                import tornado.ioloop

                tornado.ioloop.IOLoop.instance().add_callback(self.live_fig.canvas.draw)
            plt.show()
        except AttributeError as e:
            print("Error starting animation:", e, flush=True)
            # If plt.show() fails, we close the figure to avoid memory leaks
        plt.close()
