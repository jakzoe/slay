import os
from Lasermessung import Lasermessung
from laser_constants import MEASUREMENT_SETTINGS

ARDUINO_PATH = "/dev/ttyUSB0"

measurement = Lasermessung(ARDUINO_PATH, MEASUREMENT_SETTINGS)


def infinite_live_plotting():

    measurement.enable_gui()
    measurement.infinite_measuring()


if __name__ == "__main__":

    # plot_results(
    #     [
    #         PlottingSettings(
    #             "Messungen/Langzeitmessung mit Superkontinuumlaser mit Blaulichtlasern mit 100 %"
    #         )
    #     ]
    # )
    # exit()

    infinite_live_plotting()
    exit()

    """
    ## alle Messungen plotten
    for messungs_dir in os.listdir("Messungen"):
        NAME = messungs_dir
        print(NAME)
        plot_results([PlottingSettings("Messungen/" + messungs_dir)])

    NAME = "Langzeitmessung mit Superkontinuumlaser mit Blaulichtlasern mit 100 %"
    #  zoom_start=642, zoom_end=662
    plot_results([PlottingSettings("Messungen/" + NAME, zoom_start=600, zoom_end=700)])

    NAME = "Langzeitmessung mit Superkontinuumlaser und Blaulichtlasern, 100.000 Schuss, Messreihe 3 mit 100 %"
    #  zoom_start=642, zoom_end=662
    plot_results([PlottingSettings("Messungen/" + NAME, zoom_start=600, zoom_end=700)])

    AUSSCHNITT = True

    ## eine Messung gestückelt plotten
    slice_sice = 10_000
    NAME = "Langzeitmessung mit Superkontinuumlaser mit Blaulichtlasern mit 100 %"
    for i in range(0, 100_000, slice_sice):
        print("range from {0} - {1} ".format(i, i + slice_sice))
        plot_results(
            [
                PlottingSettings(
                    "Messungen/" + NAME,
                    zoom_start=600,
                    zoom_end=700,
                    intervall_start=i,
                    intervall_end=i + slice_sice - 1,
                )
            ]
        )

    ## eine Messung gestückelt plotten
    slice_sice = 10_000
    NAME = "Langzeitmessung mit Superkontinuumlaser und Blaulichtlasern, 100.000 Schuss, Messreihe 3 mit 100 %"
    for i in range(0, 100_000, slice_sice):
        print("range from {0} - {1} ".format(i, i + slice_sice))
        plot_results(
            [
                PlottingSettings(
                    "Messungen/" + NAME,
                    zoom_start=600,
                    zoom_end=700,
                    intervall_start=i,
                    intervall_end=i + slice_sice - 1,
                )
            ]
        )
    AUSSCHNITT = False
    ## eine Messung gestückelt plotten
    slice_sice = 10_000
    NAME = "Langzeitmessung mit Superkontinuumlaser mit Blaulichtlasern mit 100 %"
    for i in range(0, 100_000, slice_sice):
        print("range from {0} - {1} ".format(i, i + slice_sice))
        plot_results(
            [
                PlottingSettings(
                    "Messungen/" + NAME,
                    intervall_start=i,
                    intervall_end=i + slice_sice - 1,
                )
            ]
        )

    ## eine Messung gestückelt plotten
    slice_sice = 10_000
    NAME = "Langzeitmessung mit Superkontinuumlaser und Blaulichtlasern, 100.000 Schuss, Messreihe 3 mit 100 %"
    for i in range(0, 100_000, slice_sice):
        print("range from {0} - {1} ".format(i, i + slice_sice))
        plot_results(
            [
                PlottingSettings(
                    "Messungen/" + NAME,
                    intervall_start=i,
                    intervall_end=i + slice_sice - 1,
                )
            ]
        )
    exit()
    """

    measurement.enable_gui()

    measurement.measure()
    DIR_PATH = os.path.dirname(os.path.realpath(__file__)) + "/Messungen/"
    measurement.save(DIR_PATH)
