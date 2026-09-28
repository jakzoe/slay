from slay.spectrum_plot import SpectrumPlot
from slay.settings import PlotSettings
from slay.settings import MeasurementSettings
import os, sys, io
import time
import shutil
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import copy
from pathlib import Path

delete_old_pictures = True
# Flags um schnell bestimmte plots nicht zu generieren
plot_general = True
plot_fluo = True
plot_interpolate_only = True
dont_plot_interpolate = False
assert (plot_interpolate_only and dont_plot_interpolate) is False
plot_time_slices = True

zoom_start = PlotSettings.default_min
zoom_end = PlotSettings.default_max
zoom_start = 350
zoom_end = 900

# nur bestimmtes plotten. Leer ist disable (alles plotten). Enthält Keyword, welches in dem Namen sein muss.
# plot_list = [
#     #  "Chlorophyll4HalbIsopropanol"
# ]  # []  # ["Gradiant", "Tageslicht", "Neutral"]
plot_list = [
    # "RapsSonne4060"
]

root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "messungen/")

blacklist = False  # black- oder whitelist


def sync_messungen_pics(src_name="messungen", dest_name="messungen_pics"):

    # #!/bin/bash
    # rm -r dest_name/
    # # damit die Bilder die gleiche Struktur behalten (multiple exclude weil unabhängig von shell expansion sein)
    # rsync -av --exclude='*.npy' --exclude='*.npz' --exclude='*.mp4' src_name/ dest_name/
    destination = Path(dest_name)
    if destination.exists():
        shutil.rmtree(destination)

    source = Path(src_name)
    destination = Path(dest_name)

    for root, dirs, files in os.walk(source):
        rel_path = Path(root).relative_to(source)
        dest_dir = destination / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file.endswith((".npy", ".npz", ".json", ".mp4")):
                continue

            src_file = Path(root) / file
            dest_file = dest_dir / file
            shutil.copy2(src_file, dest_file)


def resolve_settings_path(path, name):
    """Bei zwei gleichzeitig genutzten Spektrometern gibt es zwei Messdaten-Dateien mit jeweiligem Suffix sowie eine gemeinsame settings Datei.
    In dem Fall nun aus dem Namen der Messdatei die settings finden."""
    for suffix, which in (("-a", "a"), ("-b", "b")):
        if name.endswith(suffix):
            base_name = name[: -len(suffix)]
            candidate = os.path.join(path, base_name + ".json")
            if os.path.exists(candidate):
                return candidate, which
    return os.path.join(path, name + ".json"), "a"


def make_plots(path, name):

    # damit nicht alles durcheinander ist (wegen multiprocessing)
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()

    p_settings = []

    measurement_path = os.path.join(path, name + ".npz")
    measurement_path_json, which = resolve_settings_path(path, name)
    m_settings = MeasurementSettings.from_json(measurement_path_json)
    print(f"{m_settings.TYPE}")
    # grüner Text (\033[ ist Escape sequence start, 32m Green color code, 4m underline, 0m color reset)
    print("\033[32m\033[4m" + name + "\033[0m")

    SpectrumPlot.plot_heatmap(measurement_path, m_settings, 0)

    if m_settings.laser.num_gradiants > 1:
        SpectrumPlot.plot_3d_gradient(measurement_path, m_settings)
    # return

    # Generellen Durchschnitt plotten
    if plot_general:
        p_settings.append(
            [
                PlotSettings(
                    measurement_path,
                    smooth=True,
                    zoom_start=zoom_start,
                    zoom_end=zoom_end,
                )
            ]
        )

    # Fluoreszenz-Peak plotten (ca. zwischen 720 und 740 nm bei Chlorophyll)
    # ergibt nur Sinn, wenn es einigermaßen viele Datenpunkte gibt
    print(m_settings.laser.REPETITIONS * m_settings.laser.num_gradiants)
    if plot_fluo and m_settings.laser.REPETITIONS * m_settings.laser.num_gradiants > 15:
        first_len = len(p_settings)
        p_settings.extend(
            (
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=432.8,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=525,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=570,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=660,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=665,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=670,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=675,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=680,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=685,
                        scatter=True,
                    )
                ],
                [
                    PlotSettings(
                        measurement_path,
                        smooth=True,
                        single_wav=690,
                        scatter=True,
                    )
                ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=730,
                #         scatter=True,
                #     )
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=740,
                #         scatter=True,
                #     )
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=750,
                #         scatter=True,
                #     )
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=520,
                #         scatter=True,
                #     ),
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=530,
                #         scatter=True,
                #     ),
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=540,
                #         scatter=True,
                #     ),
                # ],
                # [
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=540,
                #         scatter=True,
                #     ),
                #     PlotSettings(
                #         measurement_path,
                #         smooth=True,
                #         single_wav=740,
                #         scatter=True,
                #     ),
                # ],
            )
        )
        last_len = len(p_settings)
        if not dont_plot_interpolate:
            for i in range(first_len, last_len):
                inte_setting = copy.deepcopy(p_settings[i][0])
                inte_setting.interpolate = True
                p_settings.append([inte_setting])

        if plot_interpolate_only:
            remove_setings = []
            for i in range(first_len, last_len):
                remove_setings.append(p_settings[i])
            for setting in remove_setings:
                p_settings.remove(setting)

    # # einzelne Zeitabschnitte plotten
    if plot_time_slices:

        def f(smooth):
            p_settings.append(
                [
                    PlotSettings(
                        measurement_path,
                        smooth=smooth,
                        interval_start=0,
                        interval_end=1 / 3,
                        zoom_start=zoom_start,
                        zoom_end=zoom_end,
                        scatter=False,
                        line_style="-",
                        color="black",
                    ),
                    PlotSettings(
                        measurement_path,
                        smooth=smooth,
                        interval_start=1 / 3,
                        interval_end=2 / 3,
                        zoom_start=zoom_start,
                        zoom_end=zoom_end,
                        line_style="--",
                        color="red",
                    ),
                    PlotSettings(
                        measurement_path,
                        smooth=smooth,
                        interval_start=2 / 3,
                        interval_end=3 / 3,
                        zoom_start=zoom_start,
                        zoom_end=zoom_end,
                        line_style=":",
                        color="blue",
                    ),
                ]
            )

        f(True)
        f(False)

    for p in p_settings:
        SpectrumPlot.plot_results(p, m_settings, which=which, show_plots=False)

    sys.stdout.flush()
    # sys.stderr.flush()
    output = sys.stdout.getvalue()
    sys.stdout = original_stdout
    print(output)
    # print(sys.stderr.getvalue())


def worker(args):
    return make_plots(*args)


if __name__ == "__main__":

    # path = r"messungen/Gradiant_Test/Kontinuierlich/"
    # name = r"test-messung"
    # m_settings = MeasurementSettings.from_json(os.path.join(path, name + ".json"))
    # # m_settings.print_status()

    # p = [
    #     PlottingSettings(
    #         path,
    #         name,
    #         smooth=True,
    #         # single_wav=750,
    #         grad_start=2,
    #         grad_end=4,
    #         scatter=True,
    #     )
    # ]
    # Laserplot().plot_results(p, m_settings, show_plots=False)

    # exit()

    # # die ganzen Symblinks löschen
    # if delete_old_pictures:
    #     try:
    #         shutil.rmtree("plots/")
    #     except FileNotFoundError:
    #         print("plots dir was already deleted")

    paths = []

    for dir in os.listdir(root_dir):
        paths.append(os.path.join(root_dir, dir))
        # for subdir in os.listdir(os.path.join(root, dir)):
        #     paths.append(os.path.join(root, dir, subdir))

    tasks = []

    for path in paths:

        names = [
            os.path.splitext(f)[0]
            for f in os.listdir(path)
            if (f.endswith((".npz")) and "overwrite-messung" not in f)
        ]

        # ob das Element in der white/blacklist ist
        measurement_name = os.path.basename(path)
        if plot_list and (
            (blacklist and any(ele == measurement_name for ele in plot_list))
            or (not blacklist and not any(ele == measurement_name for ele in plot_list))
        ):
            # print(f"skipping {path}")
            continue

        if delete_old_pictures:
            pic_names = [
                os.path.splitext(f)[0] for f in os.listdir(path) if f.endswith((".png"))
            ]
            for pic_name in pic_names:
                os.remove(os.path.join(path, pic_name + ".png"))

        for name in names:
            tasks.append((path, name))

    # print(tasks)
    # exit()
    # for task in tasks:
    #     make_plots(*task)

    # print("generated plots!", flush=True)
    # exit()

    start_time = time.time()

    try:
        with ProcessPoolExecutor(max_workers=int(os.cpu_count() / 1.2)) as executor:
            # sonst fallen Exceptions nicht auf
            for _ in executor.map(worker, tasks):
                pass
    except KeyboardInterrupt:
        multiprocessing.active_children()
        for p in multiprocessing.active_children():
            p.terminate()
        exit()

    print(f"took: {time.time() - start_time:.2f} s")

    sync_messungen_pics()
    # 12: took: 44.83 s
    # 8: took: 49.54 s
    # 4: took: 83.07 s
    # 1: took: 200.00 s
