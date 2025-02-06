from Laserplot import Laserplot
from PlottingSettings import PlottingSettings
from MeasurementSettings import MeasurementSettings
import os, sys, io
import time
import shutil
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

delete_old_pictures = True
# um schnell bestimmtes zu exkludieren
plot_general = True
plot_fluo = True
plot_time_slices = True

# nur bestimmtes plotten. Leer ist disable (alles plotten). Enthält Keyword, welches in dem Namen sein muss.
plot_list = [
    # "Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Mit_Absatz_Aber_Also_Doof"
]  # ["Bodensatz"]
blacklist = False  # black- oder whitelist


def make_plots(path, name):

    # damit nicht alles durcheinander ist (wegen multiprocessing)
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()

    # grüner Text (\033[ ist Escape sequence start, 32m Green color code, 4m underline, 0m color reset)
    print(f"{path}:")
    print("\033[32m\033[4m" + name + "\033[0m")

    p_settings = []

    m_settings = MeasurementSettings.from_json(os.path.join(path, name + ".json"))

    # Generellen Durchschnitt plotten
    if plot_general:
        p_settings.append([PlottingSettings(path, name, smooth=True)])

    # Fluoreszenz-Peak plotten (ca. zwischen 720 und 740 nm bei Chlorophyll)
    if plot_fluo:
        p_settings.extend(
            (
                [
                    PlottingSettings(
                        path,
                        name,
                        smooth=True,
                        single_wav=730,
                        scatter=True,
                    )
                ],
                [
                    PlottingSettings(
                        path,
                        name,
                        smooth=True,
                        single_wav=750,
                        scatter=True,
                    )
                ],
                [
                    PlottingSettings(
                        path,
                        name,
                        smooth=True,
                        single_wav=740,
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
        Laserplot.plot_results(p, m_settings, show_plots=False)

    sys.stdout.flush()
    output = sys.stdout.getvalue()
    sys.stdout = original_stdout
    print(output)


if __name__ == "__main__":

    # path = r"messungen/Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Mit_Absatz_Aber_Also_Doof/Kontinuierlich/"
    # name = r"2025-01-26 20_39_36.791213"
    # m_settings = MeasurementSettings.from_json(os.path.join(path, name + ".json"))

    # p = [
    #     PlottingSettings(
    #         path,
    #         name,
    #         smooth=True,
    #         scatter=True,
    #     )
    # ]
    # Laserplot().plot_results(p, m_settings, show_plots=False)

    # exit()

    # die ganzen Symblinks löschen
    if delete_old_pictures:
        try:
            shutil.rmtree("plots/")
        except FileNotFoundError:
            print("plots dir was already deleted")

    paths = []
    root = "messungen/"
    for dir in os.listdir(root):
        for subdir in os.listdir(os.path.join(root, dir)):
            paths.append(os.path.join(root, dir, subdir))

    tasks = []

    for path in paths:
        # ob das Element in der white/blacklist ist
        if plot_list and (
            (blacklist and any(ele in path for ele in plot_list))
            or (not blacklist and any(ele not in path for ele in plot_list))
        ):
            continue

        names = [
            os.path.splitext(f)[0]
            for f in os.listdir(path)
            if (f.endswith((".npz")) and "overwrite-messung" not in f)
        ]

        if delete_old_pictures:
            pic_names = [
                os.path.splitext(f)[0] for f in os.listdir(path) if f.endswith((".png"))
            ]
            for pic_name in pic_names:
                os.remove(os.path.join(path, pic_name + ".png"))

        for name in names:
            tasks.append((path, name))

    # lambda geht nicht...
    def worker(args):
        return make_plots(*args)

    # print(f"Max processes: {os.cpu_count()}")
    max_workers = None  # None to disable
    start_time = time.time()

    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            executor.map(worker, tasks)
    except KeyboardInterrupt:
        multiprocessing.active_children()
        for p in multiprocessing.active_children():
            p.terminate()
        exit()

    print(f"took: {time.time() - start_time:.2f} s")

    # 12: took: 44.83 s
    # 8: took: 49.54 s
    # 4: took: 83.07 s
    # 1: took: 200.00 s
