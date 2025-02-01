from Laserplot import Laserplot
from PlottingSettings import PlottingSettings
from MeasurementSettings import MeasurementSettings
import os
import shutil

if __name__ == "__main__":

    delte_old_pictures = True
    # um schnell bestimmtes zu exkludieren
    plot_general = True
    plot_fluo = True
    plot_time_slices = True

    # nur bestimmtes plotten. Leer ist disable (alles plotten). Enthält Keyword, welches in dem Namen sein muss.
    plot_list = []  # ["Bodensatz"]
    blacklist = False  # black- oder whitelist

    # die ganzen Symblinks löschen
    if delte_old_pictures:
        try:
            shutil.rmtree("plots/")
        except FileNotFoundError:
            print("plots dir was already deleted")

    plot = Laserplot()
    paths = []
    root = "messungen/"
    for dir in os.listdir(root):
        for subdir in os.listdir(os.path.join(root, dir)):
            paths.append(os.path.join(root, dir, subdir))

    for path in paths:
        # ob das Element in der white/blacklist ist
        if plot_list and (
            (blacklist and any(ele in path for ele in plot_list))
            or (not blacklist and any(ele not in path for ele in plot_list))
        ):
            continue

        print(path)

        names = [
            os.path.splitext(f)[0]
            for f in os.listdir(path)
            if (f.endswith((".npz")) and "overwrite-messung" not in f)
        ]

        if delte_old_pictures:
            pic_names = [
                os.path.splitext(f)[0] for f in os.listdir(path) if f.endswith((".png"))
            ]
            for pic_name in pic_names:
                os.remove(os.path.join(path, pic_name + ".png"))

        for name in names:

            # grüner Text (\033[ ist Escape sequence start, 32m Green color code, 4m underline, 0m color reset)
            print("\033[32m\033[4m" + name + "\033[0m")

            p_settings = []

            m_settings = MeasurementSettings.from_json(
                os.path.join(path, name + ".json")
            )

            # Generellen Durchschnitt plotten
            if plot_general:
                p_settings.append([PlottingSettings(path, name, smooth=True)])

            # Fluoreszenz-Peak plotten (zwischen 720 und 740 nm)
            if plot_fluo:
                p_settings.extend(
                    (
                        [
                            PlottingSettings(
                                path,
                                name,
                                smooth=True,
                                zoom_start=730,
                                zoom_end=731,
                                scatter=True,
                            )
                        ],
                        [
                            PlottingSettings(
                                path,
                                name,
                                smooth=True,
                                zoom_start=750,
                                zoom_end=751,
                                scatter=True,
                            )
                        ],
                        [
                            PlottingSettings(
                                path,
                                name,
                                smooth=True,
                                zoom_start=740,
                                zoom_end=741,
                                scatter=True,
                            )
                        ],
                    )
                )

            # # einzelne Zeitabschnitte plotten
            if plot_time_slices:
                p_settings.append(
                    [
                        PlottingSettings(
                            path,
                            name,
                            smooth=True,
                            interval_start=0,
                            interval_end=1 / 3,
                            scatter=False,
                            line_style="-",
                            color="black",
                        ),
                        PlottingSettings(
                            path,
                            name,
                            smooth=True,
                            interval_start=1 / 3,
                            interval_end=2 / 3,
                            line_style="--",
                            color="red",
                        ),
                        PlottingSettings(
                            path,
                            name,
                            smooth=True,
                            interval_start=2 / 3,
                            interval_end=3 / 3,
                            line_style=":",
                            color="blue",
                        ),
                    ]
                )

            for p in p_settings:
                plot.plot_results(p, m_settings, show_plots=False)
