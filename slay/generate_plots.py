from Laserplot import Laserplot
from PlottingSettings import PlottingSettings
from MeasurementSettings import MeasurementSettings
import os
import shutil

if __name__ == "__main__":

    delte_old_pictures = True

    # die ganzen Symblinks löschen
    if delte_old_pictures:
        shutil.rmtree("plots/")

    plot = Laserplot()
    paths = []
    root = "messungen/"
    for dir in os.listdir(root):
        for subdir in os.listdir(os.path.join(root, dir)):
            paths.append(os.path.join(root, dir, subdir))

    for path in paths:
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
            print(path, name)
            p_settings = []

            m_settings = MeasurementSettings.from_json(
                os.path.join(path, name + ".json")
            )

            # Generellen Durchschnitt plotten
            p_settings.append([PlottingSettings(path, name, True, scatter=True)])

            # Fluoreszenz-Peak plotten (zwischen 720 und 740 nm)
            p_settings.extend(
                (
                    [
                        PlottingSettings(
                            path, name, True, zoom_start=730, zoom_end=731, scatter=True
                        )
                    ],
                    [
                        PlottingSettings(
                            path, name, True, zoom_start=750, zoom_end=751, scatter=True
                        )
                    ],
                    [
                        PlottingSettings(
                            path, name, True, zoom_start=740, zoom_end=741, scatter=True
                        )
                    ],
                )
            )

            # einzelne Zeitabschnitte plotten
            p_settings.append(
                [
                    PlottingSettings(
                        path,
                        name,
                        True,
                        interval_start=0,
                        interval_end=1 / 3,
                        scatter=False,
                        line_style="-",
                        color="black",
                    ),
                    PlottingSettings(
                        path,
                        name,
                        True,
                        interval_start=1 / 3,
                        interval_end=2 / 3,
                        line_style="--",
                        color="red",
                    ),
                    PlottingSettings(
                        path,
                        name,
                        True,
                        interval_start=2 / 3,
                        interval_end=3 / 3,
                        line_style=":",
                        color="blue",
                    ),
                ]
            )

            for p in p_settings:
                plot.plot_results(p, m_settings, show_plots=False)

    exit()

    # path = "messungen/Neutral_445/Kontinuierlich/"
    # name = "2025-01-26 18_59_02.972938"
    # path = "messungen/Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub/Kontinuierlich/"
    # name = "2025-01-26 13_25_44.753531"
    # path = "messungen/Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Mit_Absatz_Aber_Also_Doof/Kontinuierlich/"
    # name = "2025-01-26 20_39_36.791213"
    # path = "messungen/Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Nur_Bodensatz_Also_Toll/Kontinuierlich/"
    # name = "2025-01-26 22_49_50.736128"
    # path = "messungen/Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert/Kontinuierlich/"
    # name = "2025-01-27 10_46_45.346951"
    path = "messungen/Radieschen_Direkt_Unfokussiert/Kontinuierlich/"
    name = "2025-01-26 17_37_51.172408"

    mSettings = MeasurementSettings.from_json(path + name + ".json")
    # plot.plot_results(
    #     [PlottingSettings(path, name, True, zoom_start=750, zoom_end=751, scatter=True)]
    # )

    plot.plot_results(
        [
            PlottingSettings(
                path,
                name,
                True,
                # zoom_start=750,
                # zoom_end=751,
                interval_start=0,
                interval_end=1200,
                scatter=False,
                line_style="-",
                color="black",
            ),
            PlottingSettings(
                path,
                name,
                True,
                # zoom_start=750,
                # zoom_end=751,
                interval_start=1200,
                interval_end=2400,
                line_style="--",
                color="red",
            ),
            PlottingSettings(
                path,
                name,
                True,
                # zoom_start=750,
                # zoom_end=751,
                interval_start=2_400,
                interval_end=3_600,
                line_style=":",
                color="blue",
            ),
        ],
        mSettings,
    )
