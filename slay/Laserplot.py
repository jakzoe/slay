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
USE_GRID = False

import os
import threading
import subprocess
import warnings

import matplotlib.animation as animation
import sys
import time

# use a dic or something similar instead...
from laser_constants import *
from PlottingSettings import PlottingSettings


class Laserplot:
    def __init__(self):
        self.clim = (350, 780)
        norm = plt.Normalize(*self.clim)
        wl = np.arange(self.clim[0], self.clim[1] + 1, 2)
        colorlist = list(zip(norm(wl), [self.wavelength_to_rgb(w) for w in wl]))
        self.spectralmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "spectrum", colorlist
        )

        self.live_fig, self.live_ax = plt.subplots()
        plt.xlabel("Wellenlänge (nm)")
        plt.ylabel("Intensität (Counts)")
        # plt.grid(True)
        if USE_GRID:
            plt.grid(visible=True, which="both", linestyle="--", linewidth=0.5)
        # weniger Weiß an den Rändern

        self.scatter = self.live_ax.scatter(
            [], [], label="Mittelwert von 0 Messungen", s=5
        )

        self.past_measurement_index = -1

        plt.ion()
        plt.show()

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
            A = 1.0
        else:
            A = 0.5
        if wavelength < 380:
            wavelength = 380.0
        if wavelength > 750:
            wavelength = 750.0
        if wavelength >= 380 and wavelength <= 440:
            attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
            R = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
            G = 0.0
            B = (1.0 * attenuation) ** gamma
        elif wavelength >= 440 and wavelength <= 490:
            R = 0.0
            G = ((wavelength - 440) / (490 - 440)) ** gamma
            B = 1.0
        elif wavelength >= 490 and wavelength <= 510:
            R = 0.0
            G = 1.0
            B = (-(wavelength - 510) / (510 - 490)) ** gamma
        elif wavelength >= 510 and wavelength <= 580:
            R = ((wavelength - 510) / (580 - 510)) ** gamma
            G = 1.0
            B = 0.0
        elif wavelength >= 580 and wavelength <= 645:
            R = 1.0
            G = (-(wavelength - 645) / (645 - 580)) ** gamma
            B = 0.0
        elif wavelength >= 645 and wavelength <= 750:
            attenuation = 0.3 + 0.7 * (750 - wavelength) / (750 - 645)
            R = (1.0 * attenuation) ** gamma
            G = 0.0
            B = 0.0
        else:
            R = 0.0
            G = 0.0
            B = 0.0
        return (R, G, B, A)

    def plot_results(
        self,
        plotting_settings: list[PlottingSettings],
        measurement_settings,
        measurements,
        wav,
        verbose=True,
    ):
        """Erstellt den Plot anhand der gemessenen Daten."""

        # [:]: nutze eine Kopie von plotting_settings zum Iterieren
        for setting in plotting_settings[:]:
            file_list = [
                os.path.join(setting.file_path, f)
                for f in os.listdir(setting.file_path)
                if f.endswith(".npz")
            ]
            if not file_list:
                print(f"the dir {setting.file_path} ist empty!")
                plotting_settings.remove(setting)

        iterator = 0

        fig, ax = plt.subplots()

        # plt.grid(True)
        if USE_GRID:
            plt.grid(visible=True, which="both", linestyle="--", linewidth=0.5)
        # weniger Weiß an den Rändern
        plt.tight_layout()

        for setting in plotting_settings:

            file_list = [
                os.path.join(setting.file_path, f)
                for f in os.listdir(setting.file_path)
                if f.endswith(".npz")
            ]

            # colors = plt.cm.jet(np.linspace(0, 1, len(file_list) + 2))
            colors = matplotlib.colormaps["jet"](np.linspace(0, 1, len(file_list) + 2))

            # temp_data = np.load(file_list[0])["arr_0"][0]
            # # print(temp_data.shape)
            # # exit()
            # temp_waves = []
            # for val in temp_data:
            #     temp_waves.append(val[0])

            # temp_waves = np.array(temp_waves)

            wavelengths = np.load(file_list[0])["arr_1"]

            if setting.zoom_end == sys.maxsize:
                setting.zoom_end = 2048
            else:
                setting.zoom_end = (np.abs(wavelengths - setting.zoom_end)).argmin()

            if setting.zoom_start != 0:
                setting.zoom_start = (np.abs(wavelengths - setting.zoom_start)).argmin()

            x_ax_len = setting.zoom_end - setting.zoom_start

            result = np.zeros([x_ax_len], dtype=float)
            standard_deviation_data = []
            if verbose:
                print("calculating average...")

            for file in file_list:

                if verbose:
                    print("reading data from disk...")
                loaded_array = np.load(file)
                spectrometer_data = loaded_array["arr_0"]
                metadata = loaded_array["arr_2"]

                assert measurement_settings["REPETITIONS"] == len(spectrometer_data)

                normalize_integrationtime_factor = 1
                normalize_power = 1

                if setting.normalize_integrationtime:
                    normalize_integrationtime_factor = measurement_settings["INTTIME"]
                if setting.normalize_power:
                    normalize_integrationtime_factor = measurement_settings["INTENSITY"]

                mean = np.zeros([x_ax_len], dtype=float)

                for i in range(len(spectrometer_data)):
                    j = i + setting.interval_start
                    if j >= setting.interval_end:
                        break
                    intensity = []
                    for k in range(len(spectrometer_data[j])):
                        l = k + setting.zoom_start
                        if l >= setting.zoom_end:
                            break
                        intensity.append(
                            spectrometer_data[j][l]
                            / normalize_integrationtime_factor
                            / normalize_power
                        )
                    standard_deviation_data.append(intensity)

                    mean += spectrometer_data[j][setting.zoom_start : setting.zoom_end]

                print(
                    setting.interval_end - setting.interval_start
                    if setting.sliced()
                    else len(spectrometer_data)
                )
                print(setting.sliced())
                mean /= (
                    setting.interval_end - setting.interval_start
                    if setting.sliced()
                    else len(spectrometer_data)
                )
                result += mean

            result /= len(file_list)
            standard_deviation = np.std(standard_deviation_data, axis=0)

            # wave_min = min(wavelengths)
            # wave_max = max(wavelengths)
            # assert wave_min == wavelengths[0]
            # assert wave_max == wavelengths[-1]
            wave_min = wavelengths[0]
            wave_max = wavelengths[-1]

            intensity_min = min(result)
            intensity_max = max(result)
            std_max = max(standard_deviation)

            if verbose:
                print("creating backgroundimage...")
            # wird resized, deshalb height=1
            # ax.imshow(
            #     make_spectrum_image(int(len(wavelengths)), 1, wavelengths),
            #     extent=[
            #         wave_min,
            #         wave_max,
            #         intensity_min - std_max,
            #         intensity_max + std_max,
            #     ],
            #     aspect="auto",
            #     alpha=0.4,
            # )

            if verbose:
                print("creating plot...")

            rate = measurement_settings["REPETITIONS"]
            if setting.sliced():
                rate = setting.interval_end - setting.interval_start

            ax.scatter(
                wavelengths,
                result,
                label=f"Mittelwert von {rate} Messungen",
                color=colors[iterator],
                s=1,
            )
            assert len(result) == len(standard_deviation)

            # X, _ = np.meshgrid(wav, measurement)

            # extent = (np.min(wav), np.max(wav), np.min(measurement), np.max(measurement))
            # ax.imshow(X, clim=clim, extent=extent, cmap=spectralmap, aspect="auto")
            # ax.fill_between(wav, measurement, max(measurement), color="w")

            ax.fill_between(
                wavelengths,
                result - standard_deviation,
                result + standard_deviation,
                alpha=0.5,
                edgecolor="#CC4F1B",
                facecolor="#FF9848",
                label="Standardabweichung",
            )
            iterator += 1

        fig.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.05),
            fancybox=True,
            shadow=True,
            markerscale=4,
        )  # ,ncols=3

        plt.xlabel("Wellenlänge (nm)")
        plt.ylabel("Intensität (Counts)")

        title = setting.file_path  # measurement_settings["NAME"]

        for setting in plotting_settings:
            if setting.sliced():
                title += (
                    f" {setting.interval_start} bis {setting.interval_end} Laserschüsse"
                )
            if setting.normalize_integrationtime:
                title += " Integrationszeit normalisiert"
            if setting.normalize_power:
                title += " Power normalisiert"

            if setting.zoom():
                title += " Ausschnitt"
            # nur vom ersten hinzufügen, ansonsten wird der Titel zu lang
            break

        plt.title(title)
        title += ".png"

        plt.draw()

        try:
            os.makedirs("Plots/", 0o777)
        except OSError as error:
            print(error)
            print("(directory is already existent)")

        fig.savefig(
            "Plots/" + title.replace("%", "Prozent"), dpi=300, bbox_inches="tight"
        )
        if verbose:
            print("saved plot")

        plt.show()
        plt.close()
        plt.cla()
        plt.clf()

    def update_live_plot(self, i, messdata):
        """Plottet die aktuell gemessene Messung."""

        wav = messdata.wav
        measurements = messdata.measurements
        curr_measurement_index = messdata.curr_measurement_index

        if (
            len(measurements) == 0
            or curr_measurement_index < 0
            or self.past_measurement_index == curr_measurement_index
        ):
            return

        measurement = measurements[curr_measurement_index]

        self.live_ax.clear()
        # das Label wieder hinzufügen, nachdem .clear es gelöscht hat
        self.scatter = self.live_ax.scatter(
            [], [], label="Mittelwert von 0 Messungen", s=5
        )
        # funktioniert nicht
        # live_ax.legend(["Mittelwert von x Messungen"])

        # wurden zuvor von .clear gelöscht
        self.live_ax.set_xlabel("Wellenlänge (nm)")
        self.live_ax.set_ylabel("Intensität (Counts)")

        # die Daten im Scatter-Plot aktualisieren
        self.scatter.set_offsets(np.column_stack((wav, measurement)))

        self.scatter.set_label(f"Spektrum von Messung {curr_measurement_index + 1}")

        # den Wertebereich der Axen anpassen
        self.live_ax.set_xlim(wav[0], wav[-1])
        self.live_ax.set_ylim(min(measurement), max(measurement))
        # self.live_ax.set_ylim(0, 3000)
        # self.live_ax.set_xlim(350, 600)

        X, _ = np.meshgrid(wav, measurement)

        extent = (np.min(wav), np.max(wav), np.min(measurement), np.max(measurement))

        self.live_ax.imshow(
            X, clim=self.clim, extent=extent, cmap=self.spectralmap, aspect="auto"
        )
        self.live_ax.fill_between(wav, measurement, max(measurement), color="w")
        # Achsenbeschriftung alle 100 nm
        self.live_ax.xaxis.set_major_locator(MultipleLocator(100))
        self.live_fig.tight_layout()

        if USE_GRID:

            self.live_ax.legend(
                # loc="upper center",
                # bbox_to_anchor=(0.5, -0.05),
                frameon=True,
                fancybox=True,
                shadow=True,
                markerscale=4,
            )
        else:
            self.live_ax.legend(
                # loc="upper center",
                # bbox_to_anchor=(0.5, -0.05),
                # frameon=True,
                # fancybox=True,
                # shadow=True,
                markerscale=4,
            )

        self.past_measurement_index = curr_measurement_index
        return (self.scatter,)

    def suppressed_pause(self):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            # UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail.
            plt.pause(0.1)

    def start_gui_thread(self, frames, messdata):

        self.ani = animation.FuncAnimation(
            self.live_fig,
            self.update_live_plot,
            interval=10,
            frames=frames,
            fargs=(messdata,),
        )

        threading.Thread(
            target=lambda: [self.suppressed_pause() for _ in iter(int, 1)],
            daemon=True,  # Main-Thread soll nicht auf den Thread warten
        ).start()

        # threading.Thread(target=send_plot, daemon=True).start()
        # plt.ioff()

        # warten, bis der Thread gestartet ist
        time.sleep(0.5)
