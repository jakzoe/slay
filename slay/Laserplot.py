from MeasurementSettings import MeasurementSettings
from PlottingSettings import PlottingSettings

import numpy as np
from matplotlib.ticker import MultipleLocator

# andere backends sind ebenfalls möglich, brauchen aber teilweise andere dependencies
import matplotlib

matplotlib.use("Gtk3Agg")
import matplotlib.pyplot as plt
import matplotlib.colors

# print(plt.style.available)
# plt.style.use(["seaborn-v0_8-pastel"])

import scienceplots

plt.style.use(["science"])
# plt.rcParams["figure.figsize"] = [6.4, 4.8] # default, überschrieben von scienceplots

# wiki: 'constrained': The constrained layout solver adjusts Axes sizes to avoid overlapping Axes decorations.
# warum auch immer das nicht default ist
# da eine bestimmte figsize gespeichert wrid (zuvor definiert, hier von scienceplots. Defaul ist 6.4, 4.8)
# wird es dennoch zumindest zu einem overlapping label kommen. Dieses wird im Fall der Fälle auomatisch unter den Plot "verschoben" (siehe legend_collides)
plt.rcParams["figure.constrained_layout.use"] = True
USE_GRID = False

import os
import subprocess
from multiprocessing import Process
import warnings

import matplotlib.animation as animation
import sys
import time
import scipy
import threading

from math import ceil, floor


class Laserplot:

    class GraphSettings:

        def __init__(
            self,
            fig,
            ax,
            x_data,
            y_data,
            label,
            smooth,
            color,
            style,
            std=None,
            rainbow=False,
            scatter=True,
            marker_size=4,
            time_plot=False,
            single_wav=False,
        ):
            self.fig = fig
            self.ax = ax
            self.x_data = x_data
            self.y_data = y_data
            self.label = label
            self.smooth = smooth
            self.color = color
            self.style = style
            self.std = std
            self.rainbow = rainbow
            self.scatter = scatter
            self.marker_size = marker_size
            self.time_plot = time_plot
            self.single_wav = single_wav

    def __init__(self):
        self.clim = (350, 780)
        norm = plt.Normalize(*self.clim)
        wl = np.arange(self.clim[0], self.clim[1] + 1, 2)
        colorlist = list(zip(norm(wl), [self.wavelength_to_rgb(w) for w in wl]))
        self.spectralmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "spectrum", colorlist
        )

        self.live_fig, self.live_ax = plt.subplots()
        self.live_ax.set_xlabel("Wellenlänge (nm)")
        self.live_ax.set_ylabel("Intensität (Counts)")
        # self.live_ax.grid(True)
        if USE_GRID:
            self.live_ax.grid(visible=True, which="both", linestyle="--", linewidth=0.5)
        # weniger Weiß an den Rändern

        self.scatter = self.live_ax.scatter(
            [], [], label="Mittelwert von 0 Messungen", s=5
        )

        self.past_measurement_index = -1

        plt.ion()
        plt.show()
        self.stop_event = threading.Event()

    def wavelength_to_rgb(self, wavelength, gamma=0.8):
        """taken from http://www.noah.org/wiki/Wavelength_to_RGB_in_Python
        This converts a given wavelength of light to an
        approximate RGB color value. The wavelength must be given
        in nanometers in the range from 380 nm through 750 nm
        (789 THz through 400 THz).

        Based on code by Dan Bruton
        http://www.physics.sfasu.edu/astro/color/spectra.html
        Additionally alpha value set to 0.5 outside range
        """
        wavelength = float(wavelength)
        if wavelength >= 380 and wavelength <= 750:
            a = 1.0
        else:
            a = 0.5
        if wavelength < 380:
            wavelength = 380.0
        if wavelength > 750:
            wavelength = 750.0
        if wavelength >= 380 and wavelength <= 440:
            attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
            r = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
            g = 0.0
            b = (1.0 * attenuation) ** gamma
        elif wavelength >= 440 and wavelength <= 490:
            r = 0.0
            g = ((wavelength - 440) / (490 - 440)) ** gamma
            b = 1.0
        elif wavelength >= 490 and wavelength <= 510:
            r = 0.0
            g = 1.0
            b = (-(wavelength - 510) / (510 - 490)) ** gamma
        elif wavelength >= 510 and wavelength <= 580:
            r = ((wavelength - 510) / (580 - 510)) ** gamma
            g = 1.0
            b = 0.0
        elif wavelength >= 580 and wavelength <= 645:
            r = 1.0
            g = (-(wavelength - 645) / (645 - 580)) ** gamma
            b = 0.0
        elif wavelength >= 645 and wavelength <= 750:
            attenuation = 0.3 + 0.7 * (750 - wavelength) / (750 - 645)
            r = (1.0 * attenuation) ** gamma
            g = 0.0
            b = 0.0
        else:
            r = 0.0
            g = 0.0
            b = 0.0
        return (r, g, b, a)

    def legend_collides(self, ax, px, py):

        bbox_legend = ax.get_legend().get_window_extent()
        # in Datenkoordinaten umrechnen
        x0, y0 = ax.transData.inverted().transform((bbox_legend.x0, bbox_legend.y0))
        x1, y1 = ax.transData.inverted().transform((bbox_legend.x1, bbox_legend.y1))
        for x, y in zip(px, py):
            if x >= x0 and x <= x1 and y >= y0 and y <= y1:
                return True

        return False

        # def is_overlapping(x0a, y0a, x1a, y1a, x0b, y0b, x1b, y1b):
        #     return not (x1a < x0b or x1b < x0a or y1a < y0b or y1b < y0a)

        # bbox_legend = ax.get_legend().get_window_extent()
        # # x0b, y0b = ax.transData.inverted().transform((bbox_legend.x0, bbox_legend.y0))
        # # x1b, y1b = ax.transData.inverted().transform((bbox_legend.x1, bbox_legend.y1))

        # for artist in ax.get_children():
        #     if isinstance(artist, type(ax.get_legend())):
        #         continue
        #     print(artist)
        #     bbox = artist.get_window_extent()
        #     # x0a, y0a = ax.transData.inverted().transform((bbox.x0, bbox.y0))
        #     # x1a, y1a = ax.transData.inverted().transform((bbox.x1, bbox.y1))

        #     if matplotlib.transforms.Bbox.intersection(bbox, bbox_legend) is not None:
        #         return True
        #     # if is_overlapping(x0a, y0a, x1a, y1a, x0b, y0b, x1b, y1b):
        #     #     return True
        # return False

    def data_to_plot(
        self,
        settings: GraphSettings,
    ):

        def smooth_curve(array):
            return scipy.signal.savgol_filter(array, window_length=50, polyorder=5)

        line_data = (
            smooth_curve(settings.y_data)
            if not settings.time_plot and settings.smooth
            else settings.y_data
        )

        if settings.rainbow and not settings.time_plot:
            X, _ = np.meshgrid(settings.x_data, line_data)

            extent = (
                np.min(settings.x_data),
                np.max(settings.x_data),
                np.min(line_data),
                np.max(line_data),
            )

            settings.ax.imshow(
                X, clim=self.clim, extent=extent, cmap=self.spectralmap, aspect="auto"
            )
            settings.ax.fill_between(
                settings.x_data,
                line_data,
                np.max(line_data) + settings.marker_size,
                color="w",
            )

        if settings.std is not None and not settings.time_plot:

            std = smooth_curve(settings.std) if settings.smooth else settings.std
            assert len(settings.x_data) == len(line_data) == len(std)
            settings.ax.fill_between(
                settings.x_data,
                settings.y_data - std,
                settings.y_data + std,
                alpha=0.2,
                edgecolor="#CC4F1B",
                facecolor="#FF9848",
                label=None if settings.label is None else "Standardabweichung",
            )
            # ax.plot(
            #     wav,
            #     line_data - std,
            #     color="red",
            #     alpha=0.2,
            #     label=None if label is None else "Standardabweichung",
            # )
            # ax.plot(
            #     wav,
            #     line_data + std,
            #     color="red",
            #     alpha=0.2,
            # )
        # das Label wieder hinzufügen, nachdem .clear es gelöscht hat
        # self.scatter =
        if settings.smooth and settings.scatter:
            settings.ax.scatter(
                settings.x_data,
                settings.y_data,
                label=settings.label,
                s=settings.marker_size,
                color="gray" if not settings.time_plot else "blue",
                alpha=0.4 if not settings.time_plot else 1,
            )
        #     ax.plot(
        #         wav, line_data, label=None if label is None else "smooth"
        #     )  #  color=colors[iterator],

        # else:
        #     ax.scatter(
        #         wav,
        #         measurement,
        #         label=None if label is None else label,
        #         s=marker_size,
        #     )  #  color=colors[iterator],

        if not settings.time_plot:
            settings.ax.plot(
                settings.x_data,
                line_data,
                label=settings.label,
                color=settings.color,
                linestyle=settings.style,
                # alpha=0.1,
            )

        if settings.single_wav:  # settings.time_plot:

            # den konstanten Teil am Ende wegschneiden (der eine sehr geringe Steigung hat)
            index = len(settings.y_data)
            step_size = ceil(len(settings.y_data) / 10)
            if step_size > 1:
                for i in range(len(settings.y_data) - step_size - 1, 0, -step_size):
                    m = abs(
                        np.polyfit(
                            settings.x_data[i : i + step_size],
                            settings.y_data[i : i + step_size],
                            deg=1,
                        )[0]
                    )
                    if np.rad2deg(np.arctan(m)) > 25:
                        index = i
                        break

            cut_data_x = settings.x_data[:index]
            cut_data_y = settings.y_data[:index]
            linear_curve = np.polyfit(
                cut_data_x,
                cut_data_y,
                deg=1,
            )
            m = linear_curve[0]
            n = linear_curve[1]
            x_fitted = np.array([cut_data_x[0], cut_data_x[-1]])
            y_fitted = m * x_fitted + n
            settings.ax.plot(
                x_fitted,
                y_fitted,
                color="red",
                linewidth=settings.marker_size,
                label=r"$\text{{g}}(x) \approx {:.2f}x{}{:.0f}$".format(
                    m, "" if n < 0 else "+", n
                ),
            )
            # verhindern, dass das Label gar nicht erst erstellt wird (siehe if weiter unten)
            settings.label = " " if settings.label is None else settings.label

            # bei Noise kommt manchmal ein OptimizeWarning
            parameter = scipy.optimize.curve_fit(
                lambda t, a, b, c: a * np.exp(b * t) + c,
                settings.x_data,
                settings.y_data,
                # a ist ungefähr [0] - c, c ungefähr [-1]
                p0=(
                    settings.y_data[0] - settings.y_data[-1],
                    -0.0015,  # bisschen rumprobiert
                    settings.y_data[-1],
                ),
                maxfev=20_000,
            )[0]
            x_fitted = np.linspace(
                np.min(settings.x_data), np.max(settings.x_data), 1000
            )
            a = parameter[0]
            b = parameter[1]
            c = parameter[2]
            y_fitted_expo = a * np.exp(b * x_fitted) + c
            b_format = f"{b:.2e}".split("e")

            settings.ax.plot(
                x_fitted,
                y_fitted_expo,
                color="orange",
                linewidth=settings.marker_size,
                label=r"$\text{{exp}}(x) \approx {:.0f} e^{{ {} \cdot 10^{{{:.0f}}} t}} {}{:.0f}$".format(
                    a, float(b_format[0]), float(b_format[1]), "" if c < 0 else "+", c
                ),
            )

        # die Daten im Scatter-Plot aktualisieren
        # self.scatter.set_offsets(np.column_stack((wav, measurement)))
        # self.scatter.set_label(label)

        # funktioniert nicht
        # live_ax.legend(["Mittelwert von x Messungen"])

        # wurden zuvor von .clear gelösch
        settings.ax.set_xlabel(
            "Wellenlänge (nm)" if not settings.time_plot else "Zeit (s)"
        )
        settings.ax.set_ylabel("Intensität (Counts)")

        # den Wertebereich der Axen anpassen (mit Puffer)
        puffer = 0  # 10
        if not settings.time_plot:
            settings.ax.set_xlim(
                settings.x_data[0] - puffer, settings.x_data[-1] + puffer
            )
        # so machen, dass immer noch das Label oben hinpasst
        settings.ax.set_ylim(
            max(0, min(line_data), settings.ax.get_ylim()[0]),
            max(max(line_data), 2000, settings.ax.get_ylim()[1]),
        )  # * 1.05

        # ax.set_ylim(1500, max(measurement))
        # ax.set_xlim(350, 600)

        # Achsenbeschriftung alle 100 nm
        if not settings.time_plot:
            settings.ax.xaxis.set_major_locator(MultipleLocator(100))
        settings.ax.tick_params(axis="both", labelsize=8)

        # weniger Weiß an den Rändern. Überschreibt aber constrained layout
        # fig.tight_layout()

        options = {
            "frameon": True,
            "fancybox": True,
            "shadow": True,
            "markerscale": 4 if USE_GRID else 2,
            # framealpha=0.3,
        }

        if settings.label is not None:
            settings.ax.legend(**options)
            settings.fig.canvas.draw()

            if self.legend_collides(
                settings.ax,
                settings.x_data,
                settings.y_data,
            ):

                # ist in Pixeln
                label_y = settings.ax.xaxis.get_tightbbox().y1
                # in Pixel (dots) umgerechnet
                fig_height = settings.fig.get_size_inches()[1] * settings.fig.dpi
                # in Prozent umrechnen (für bbox_to_anchor)
                label_y_normalized = label_y / fig_height

                # drei Millimeter in Prozent
                offset = 3 / 25.4 * settings.fig.dpi / fig_height

                options.update(
                    {
                        "bbox_to_anchor": (0.5, -(label_y_normalized + offset)),
                        "loc": "upper center",
                        "ncols": 1,  # default
                    }
                )

                settings.ax.legend(**options)

                settings.fig.canvas.draw()
                orig_bounds = settings.ax.get_position().bounds

                # testen, ob zweispaltig besser ist
                options["ncols"] = 2
                settings.ax.legend(**options)
                settings.fig.canvas.draw()

                # rückgängig machen, wenn height gain kleiner ist als width Verlust (-1 ist height, -2 ist width)
                if (
                    settings.ax.get_position().bounds[-1] - orig_bounds[-1]
                    < orig_bounds[-1] - settings.ax.get_position().bounds[-2]
                ):
                    options["ncols"] = 1
                    settings.ax.legend(**options)
                    settings.fig.canvas.draw()

    def plot_results(
        self,
        plotting_settings: list[PlottingSettings],
        measurement_settings: MeasurementSettings,
        colors=None,
        show_plots=True,
        # messdata: Messdata,
        # verbose=True,
    ):
        """Erstellt einen Plot mit den in den Plotting-Settings definierten Graphen."""

        plt.ioff()
        # dirty, aber: Irgendwo wird eine figure ohne Inhalt erstellt und nicht geschlossen?? Die dann unten gezeigt werden würde.
        plt.close("all")
        # measurements, wav, curr_measurement_index = messdata.get_data()

        # # [:]: nutze eine Kopie von plotting_settings zum Iterieren
        # for setting in plotting_settings[:]:
        #     # if not os.path.exists(setting.file_path):
        #     #     print(f"The directory {setting.file_path} does not exist!")
        #     #     plotting_settings.remove(setting)
        #     #     continue

        #     file_list = [
        #         os.path.join(setting.file_path, f)
        #         for f in os.listdir(setting.file_path)
        #         if f.endswith(".npz")
        #     ]
        #     if not file_list:
        #         print(f"the dir {setting.file_path} ist empty!")
        #         plotting_settings.remove(setting)

        fig, ax = plt.subplots()  # plt.subplots(layout="constrained")
        # werden nicht immer benutz, daher nur bei Bedarf erstellen (damit keine leeren Plots erstelltt werden)
        fig_colorful, ax_colorful = (None, None)

        # plt.grid(True)
        if USE_GRID:
            plt.grid(visible=True, which="both", linestyle="--", linewidth=0.5)

        if colors is None:
            # colors = plt.cm.jet(np.linspace(0, 1, len(file_list) + 2))
            colors = matplotlib.colormaps["jet"](
                np.linspace(0, 1, len(plotting_settings) + 2)
            )

        # ob mehrere Graphen geplottet werden
        multiple_plots = len(plotting_settings) != 1
        time_plot = not multiple_plots and plotting_settings[0].single_wav
        for i, setting in enumerate(plotting_settings):

            # file_list = [
            #     os.path.join(setting.file_path, f)
            #     for f in os.listdir(setting.file_path)
            #     if f.endswith(".npz")
            # ]

            file_name = os.path.join(setting.file_path, setting.code_name + ".npz")

            loaded_array = np.load(file_name)
            spectrometer_data = loaded_array["arr_0"]
            x_data = loaded_array["arr_1"]
            time_stamps = loaded_array["arr_2"] - loaded_array["arr_2"][0]

            # falls es in Prozent angegeben wurde
            if setting.interval_start_time < 1 and setting.interval_end_time <= 1:
                setting.interval_start_time = (
                    time_stamps[-1] * setting.interval_start_time
                    if setting.interval_start_time != 0
                    else 0
                )
                setting.interval_end_time = time_stamps[-1] * setting.interval_end_time

            # Sekunden in Index umrechnen
            setting.interval_start = (
                0
                if setting.interval_start_time == 0
                else (np.abs(time_stamps - setting.interval_start_time)).argmin()
            )

            setting.interval_end = (
                len(spectrometer_data)
                if setting.interval_end_time == sys.maxsize
                else (np.abs(time_stamps - setting.interval_end_time)).argmin()
            )

            # von Wellenlänge in Index umrechnen
            setting.zoom_start = (
                0
                if setting.zoom_start_wav == 0
                else (np.abs(x_data - setting.zoom_start_wav)).argmin()
            )
            if setting.single_wav:
                setting.zoom_end = setting.zoom_start + 1
            else:
                setting.zoom_end = (
                    len(x_data)
                    if setting.zoom_end_wav == sys.maxsize
                    else (np.abs(x_data - setting.zoom_end_wav)).argmin()
                )

            # nur eine Wellenlänge über die Zeit plotten
            if setting.single_wav:
                x_data = (loaded_array["arr_2"] - loaded_array["arr_2"][0])[
                    setting.interval_start : setting.interval_end
                ]  # Zeit von UNIX time in delta Time in Minuten umrechnen
                print(f"Zeitlänge der Messung: {x_data[-1]:.2f} s")
                x_ax_len = len(x_data)
            else:
                assert len(x_data) == 2048
                x_ax_len = setting.zoom_end - setting.zoom_start
                x_data = x_data[setting.zoom_start : setting.zoom_end]

            # setting.zoom_end = (
            #     len(x_data)
            #     if setting.zoom_end == sys.maxsize
            #     else (np.abs(x_data - setting.zoom_end)).argmin()
            # )

            # if setting.zoom_start != 0:
            #     setting.zoom_start = (np.abs(x_data - setting.zoom_start)).argmin()

            assert measurement_settings.laser.REPETITIONS == len(spectrometer_data)

            del time_stamps, loaded_array

            normalize_integrationtime_factor = (
                measurement_settings.specto.INTTIME
                if setting.normalize_integrationtime
                else 1
            )
            normalize_power = (
                measurement_settings.laser.INTENSITY if setting.normalize_power else 1
            )

            # # aus den gesamten Daten den durch die Slices definierten Teil ausschneiden
            # extracted_data = np.zeros(
            #     (
            #         setting.interval_end - setting.interval_start,
            #         x_ax_len,
            #     )
            # )

            extracted_data = (
                spectrometer_data[
                    setting.interval_start : setting.interval_end,
                    setting.zoom_start : setting.zoom_end,
                ]
                / normalize_integrationtime_factor
                / normalize_power
            )
            if setting.single_wav:
                # setting.zoom_start : setting.zoom_end ist nur ein Element in diesem Fall
                extracted_data = extracted_data.flatten()

            # # jede Wiederholung der Messung
            # for i in range(len(spectrometer_data)):
            #     # nur Ausschnitt aus den Widerholungen der Messung (falls gewünscht)
            #     j = i + setting.interval_start
            #     if j >= setting.interval_end:
            #         break
            #     # die gesamten Daten von der Messung i sammeln und ggf. normalisieren
            #     intensities = []
            #     for k in range(len(spectrometer_data[j])):
            #         l = k + setting.zoom_start
            #         if l >= setting.zoom_end:
            #             break
            #         intensities.append(
            #             spectrometer_data[j][l]
            #             / normalize_integrationtime_factor
            #             / normalize_power
            #         )
            #     extracted_data[j] = np.array(intensities)
            del spectrometer_data

            if setting.single_wav:
                y_data = extracted_data
                standard_deviation = None
            else:
                y_data = np.mean(extracted_data, axis=0, dtype=float)
                # STD nicht plotten, wenn es mehrere Graphen sind (zu unübersichtlich)
                standard_deviation = (
                    np.std(extracted_data, axis=0, dtype=float)
                    if not multiple_plots
                    else None
                )
                if standard_deviation is not None:
                    assert len(y_data) == len(standard_deviation)
            assert len(y_data) == x_ax_len

            # nimmt zu viel Platz ein: Einfach dazu schreiben
            # label = f"Mittelwert von {rate} Messungen"

            color = colors[i] if setting.color is None else setting.color

            # blauer Text (\033[ ist Escape sequence start, 34m Blue color code, 0m color reset)
            print(
                f"\033[34mmax: {np.max(y_data):.2f} at {x_data[np.argmax(y_data)]:.2f}\033[0m"
            )

            def round_left(x):
                return (
                    floor(x)
                    if round(setting.interval_start_time)
                    == round(setting.interval_end_time)
                    else round(x)
                )

            def round_right(x):
                return (
                    ceil(x)
                    if round(setting.interval_start_time)
                    == round(setting.interval_end_time)
                    else round(x)
                )

            graphSettings = self.GraphSettings(
                fig=fig,
                ax=ax,
                x_data=x_data,
                y_data=y_data,
                label=(
                    f"{round_left(setting.interval_start_time)} s - {round_right(setting.interval_end_time)} s"
                    if setting.sliced and not setting.single_wav
                    else None
                ),
                smooth=setting.smooth,
                color=color,
                style=setting.line_style,
                std=standard_deviation,
                scatter=setting.scatter,
                time_plot=time_plot,
                single_wav=setting.single_wav,
            )
            self.data_to_plot(graphSettings)

            if not multiple_plots and not setting.single_wav:
                if fig_colorful is None and ax_colorful is None:
                    fig_colorful, ax_colorful = plt.subplots()
                graphSettings.fig = fig_colorful
                graphSettings.ax = ax_colorful
                graphSettings.rainbow = True
                graphSettings.scatter = False
                graphSettings.std = None

                self.data_to_plot(graphSettings)

        titles = [
            (
                f"{tle_set.code_name.split('.')[0]}"  # die Millisekunden entfernen, für kürzere Namen
                + (
                    f"_{round_left(tle_set.interval_start_time)}_{round_right(tle_set.interval_end_time)}"
                    if tle_set.sliced
                    else ""
                )
                + (f"_{tle_set.single_wav}" if setting.single_wav else "")
                + (
                    f"_{tle_set.zoom_start_wav}_{tle_set.zoom_end_wav}"
                    if setting.zoomed
                    else ""
                )
                # + ("_sw" if setting.single_wav else "")  # single wav (wird aber durch den Interval schon angegeben)
                + (
                    "_in" if tle_set.normalize_integrationtime else ""
                )  # integration normalized
                + ("_pn" if tle_set.normalize_power else "")  # power normalized
            )
            for tle_set in plotting_settings
        ]

        title = "__".join(titles)

        # plt.title(title)

        if show_plots:
            # ich weiß, dass das scuffed ist, der Bug ist aber auch nicht mehr aufgetreten bisher...
            # plt.ioff()
            for i in range(10):
                print(f"plt.show() on {i+1} try")
                if i == 9:
                    print("could not show plot...")
                    break
                try:
                    plt.draw()
                    plt.show(block=True)
                    # print("waiting for five sec...")
                    # time.sleep(5)
                    break
                except KeyboardInterrupt:
                    raise
                except:
                    continue
            # plt.ion()

        root_plot_dir = "plots/" + (
            "single/" if len(plotting_settings) == 1 else "multi/"
        )
        # print("figures: " + str(plt.get_fignums()))

        figures = [fig]
        paths = [root_plot_dir + "neutral/"]
        suffixes = [""]
        if not multiple_plots and not setting.single_wav:
            figures.append(fig_colorful)
            paths.append(root_plot_dir + "colorful/")
            paths.append("_colorful")

        for fig, path, suffix in zip(figures, paths, suffixes):
            fig.savefig(
                os.path.join(setting.file_path, title + suffix + ".png"),
                dpi=600,
            )

            os.makedirs(path, 0o777, exist_ok=True)

            # relpath, da docker und host unterschiedliche roots haben
            rel_path = (
                os.path.relpath(
                    os.path.abspath(setting.file_path), os.path.abspath(path)
                )
                + "/"
            )
            cwd = os.getcwd()
            os.chdir(os.path.abspath(path))
            try:
                src = rel_path + title + suffix + ".png"
                dest = title + suffix + ".png"
                if os.path.islink(dest):
                    os.remove(dest)
                os.symlink(src, dest)
            except FileExistsError as e:
                print("could not create symlink")
                print(e.strerror)

            os.chdir(cwd)

        return
        plt.show()
        plt.close()
        plt.cla()
        plt.clf()

    def update_live_plot(self, i, messdata):
        """Plottet die aktuell gemessene Messung."""

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

        if (
            len(measurements) == 0
            or curr_measurement_index < 0
            or self.past_measurement_index == curr_measurement_index
        ):
            return

        measurement = measurements[curr_measurement_index]

        label = f"Spektrum von Messung {curr_measurement_index + 1}"
        self.live_ax.clear()

        settings = self.GraphSettings(
            self.live_fig, self.live_ax, wav, measurement, label, True, "black", "-"
        )
        self.data_to_plot(settings)

        self.past_measurement_index = curr_measurement_index
        return (self.scatter,)

    def suppressed_pause(self):
        # if self.stop_event.is_set():
        #     print(self.stop_event.is_set())
        #     return
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            # UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail.
            plt.pause(0.1)

    def live_thread_job(self):

        pause_thread = threading.Thread(
            target=lambda: self.suppressed_pause(),  # ohne lambda wird es direkt ausgeführt
            daemon=True,
        )
        pause_thread.start()  # aus einem Grund, den ich nicht kenne, exited plt.pause nie. plt.draw() und dann plt.show(block=False) hat auch nicht funktioniert.
        while not self.stop_event.is_set():
            time.sleep(1)
            # pause_thread.join(timeout=1)

        # plt.cla()
        # plt.clf()
        plt.close(self.live_fig)

    def start_gui(self, frames, messdata):

        self.live_animation = animation.FuncAnimation(
            fig=self.live_fig,
            func=self.update_live_plot,
            interval=25,
            frames=frames,
            fargs=(messdata,),
            # blit=True,
        )

        # funktioniert nicht, da kein shared mem
        # self.live_thread = Process(
        #     target=lambda: [self.suppressed_pause() for _ in iter(int, 1)], daemon=True
        # )

        self.live_thread = threading.Thread(
            # target=lambda: [
            #     self.suppressed_pause() for _ in iter(int, 1)
            # ],  #
            target=self.live_thread_job,
            daemon=True,  # Main-Thread soll nicht auf den Thread warten
        )
        self.live_thread.start()

        # threading.Thread(
        #     target=plt.show(),  # instead of plt.show()
        #     daemon=True,  # Main-Thread soll nicht auf den Thread warten
        # ).start()

        # plt.show()

        # threading.Thread(target=send_plot, daemon=True).start()
        # plt.ioff()

        # warten, bis der Thread gestartet ist
        time.sleep(0.5)

    def stop_gui(self):
        if hasattr(self, "stop_event") and hasattr(self, "live_thread"):
            self.stop_event.set()
            self.live_thread.join(timeout=5)
            # self.live_animation.event_source.stop()

        # self.live_thread.terminate()
        # self.live_thread.join(timeout=3)
        # if self.live_thread.is_alive():
        #     self.live_thread.kill()
