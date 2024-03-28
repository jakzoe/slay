import os
from datetime import datetime
import numpy as np

np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
from PIL import Image
import sys
import time
import serial
import tempfile
import threading

from laser_constants import *

try:
    from stellarnet.stellarnet_driverLibs import stellarnet_driver3 as sn

    print(sn.version())
except:
    print("\n Failed to load the stellarnet library.\n")
    # exit()

DEBUG = False

spectrometer = None
wav = None
arduino = None

if DEBUG:
    wav = np.zeros((2048, 1))
    for i in range(len(wav)):
        wav[i] = 300 + i / 5.0


class PlottingSettings:
    file_path = ""

    # Angabe: Wellenlänge
    zoom_start = 0
    zoom_end = 0

    # nur einen Ausschnitt/Batch aus den Messungen zur Durchschnittsberechnung etc. nutzten.
    # Angabe: Index
    intervall_start = 0
    intervall_end = 0

    normalize_integrationtime = False
    normalize_power = False

    def __init__(
        self,
        file_path,
        zoom_start=0,
        zoom_end=sys.maxsize,
        intervall_start=0,
        intervall_end=sys.maxsize,
        normalize_integrationtime=False,
        normalize_power=False,
    ):
        self.file_path = file_path

        self.zoom_start = zoom_start
        self.zoom_end = zoom_end

        self.intervall_start = intervall_start
        self.intervall_end = intervall_end

        self.normalize_integrationtime = normalize_integrationtime
        self.normalize_power = normalize_power

    def sliced(self) -> bool:
        return not (self.intervall_start == 0 and self.intervall_end == sys.maxsize)

    def zoom(self) -> bool:
        return not (
            self.zoom_start == 0
            and (self.zoom_end == sys.maxsize or self.zoom_end == 2048)
        )


def arduino_setup(PORT, wait):
    global arduino
    arduino = serial.Serial(PORT, 9600, timeout=5)
    # auf den Arduino warten
    time.sleep(wait)
    arduino.flush()


def turn_on_laser():
    arduino.write(b"1\n")
    time.sleep(ARDUINO_DELAY / 1000.0)


def turn_off_laser():
    arduino.write(b"0\n")
    time.sleep(ARDUINO_DELAY / 1000.0)


# modefied, von https://codingmess.blogspot.com/2009/05/conversion-of-wavelength-in-nanometers.html
def wav2RGB(wavelength):
    # print(np.array(wavelength).shape)
    w = int(wavelength)

    # colour
    if w >= 380 and w < 440:
        R = -(w - 440.0) / (440.0 - 350.0)
        G = 0.0
        B = 1.0
    elif w >= 440 and w < 490:
        R = 0.0
        G = (w - 440.0) / (490.0 - 440.0)
        B = 1.0
    elif w >= 490 and w < 510:
        R = 0.0
        G = 1.0
        B = -(w - 510.0) / (510.0 - 490.0)
    elif w >= 510 and w < 580:
        R = (w - 510.0) / (580.0 - 510.0)
        G = 1.0
        B = 0.0
    elif w >= 580 and w < 645:
        R = 1.0
        G = -(w - 645.0) / (645.0 - 580.0)
        B = 0.0
    elif w >= 645 and w <= 780:
        R = 1.0
        G = 0.0
        B = 0.0
    else:
        R = 255.0
        G = 255.0
        B = 255.0
        return (int(R), int(G), int(B))

    # intensity correction
    if w >= 380 and w < 420:
        SSS = 0.3 + 0.7 * (w - 350) / (420 - 350)
    elif w >= 420 and w <= 700:
        SSS = 1.0
    elif w > 700 and w <= 780:
        SSS = 0.3 + 0.7 * (780 - w) / (780 - 700)
    else:
        SSS = 1 / 255.0
    SSS *= 255

    return (int(SSS * R), int(SSS * G), int(SSS * B))


def make_spectrum_image(width, height, wavelength, cache=True):

    if cache:
        try:
            return Image.open(
                "{0}/spectrum_background_{1}_{2}.png".format(
                    tempfile.gettempdir(), width, height
                )
            )
        except:
            pass

    image = Image.new("RGB", (width, height), (255, 255, 255))

    for x in range(width):
        for y in range(height):
            image.putpixel((x, y), wav2RGB(wavelength[x]))  #  + (200,)

    if cache:
        image.save(
            "{0}/spectrum_background_{1}_{2}.png".format(
                tempfile.gettempdir(), width, height
            )
        )

    return image


def spectrometer_setup():

    global spectrometer, wav

    spectrometer, wav = sn.array_get_spec(0)

    print(spectrometer)
    sn.ext_trig(spectrometer, True)
    print("\nDevice ID: ", sn.getDeviceId(spectrometer))

    sn.ext_trig(spectrometer, True)

    # True ignoriert die ersten Messdaten, da diese ungenau sein können (durch Änderung der Integrationszeit)
    sn.setParam(spectrometer, INTTIME, SCAN_AVG, SMOOTH, XTIMING, True)


def get_data():
    # start_time = time.time()
    # var = sn.array_spectrum(spectrometer, wav)
    # print((time.time() - start_time) * 1000)
    # return var
    return sn.array_spectrum(spectrometer, wav)
    # return sn.getSpectrum_Y(spectrometer)


def plot_results(
    plotting_settings: list[PlottingSettings],
    verbose=True,
):

    # [:]: nutze eine Kopie von plotting_settings zum Iterieren
    for setting in plotting_settings[:]:
        file_list = [
            os.path.join(setting.file_path, f)
            for f in os.listdir(setting.file_path)
            if f.endswith(".npz")
        ]
        if not file_list:
            print("the dir {0} ist empty!".format(setting.file_path))
            plot_results.remove(setting)

    iterator = 0

    fig, ax = plt.subplots()

    plt.grid(True)

    for setting in plotting_settings:

        file_list = [
            os.path.join(setting.file_path, f)
            for f in os.listdir(setting.file_path)
            if f.endswith(".npz")
        ]

        colors = plt.cm.jet(np.linspace(0, 1, len(file_list) + 2))

        temp_data = np.load(file_list[0])["arr_0"][0]
        # print(temp_data.shape)
        # exit()
        temp_waves = []
        for val in temp_data:
            temp_waves.append(val[0])

        temp_waves = np.array(temp_waves)

        if setting.zoom_end == sys.maxsize:
            setting.zoom_end = 2048
        else:
            setting.zoom_end = (np.abs(temp_waves - setting.zoom_end)).argmin()

        if setting.zoom_start != 0:
            setting.zoom_start = (np.abs(temp_waves - setting.zoom_start)).argmin()

        x_ax_len = setting.zoom_end - setting.zoom_start

        result = np.zeros([x_ax_len, 2], dtype=float)
        standard_deviation_data = []
        if verbose:
            print("calculating average...")
        for file in file_list:

            if verbose:
                print("reading data from disk...")
            loaded_array = np.load(file)
            spectrometer_data = loaded_array["arr_0"]
            metadata = loaded_array["arr_1"]

            assert metadata[REPETITIONS_INDEX] == len(spectrometer_data)

            normalize_integrationtime_factor = 1
            normalize_power = 1

            if setting.normalize_integrationtime:
                normalize_integrationtime_factor = metadata[INTTIME_INDEX]
            if setting.normalize_power:
                normalize_integrationtime_factor = metadata[INTENSITY_INDEX]

            mean = np.zeros([x_ax_len, 2], dtype=float)

            for i in range(len(spectrometer_data)):
                j = i + setting.intervall_start
                if j >= setting.intervall_end:
                    break
                intensity = []
                for k in range(len(spectrometer_data[j])):
                    l = k + setting.zoom_start
                    if l >= setting.zoom_end:
                        break
                    intensity.append(
                        spectrometer_data[j][l][1]
                        / normalize_integrationtime_factor
                        / normalize_power
                    )
                standard_deviation_data.append(intensity)

                mean += spectrometer_data[j][setting.zoom_start : setting.zoom_end]

            print(
                setting.intervall_end - setting.intervall_start
                if setting.sliced()
                else len(spectrometer_data)
            )
            print(setting.sliced())
            mean /= (
                setting.intervall_end - setting.intervall_start
                if setting.sliced()
                else len(spectrometer_data)
            )
            result += mean

        result /= len(file_list)
        standard_deviation = np.std(standard_deviation_data, axis=0)

        wavelength = []
        intensity = []
        for val in result:
            wavelength.append(val[0])
            intensity.append(val[1])

        wave_min = min(wavelength)
        wave_max = max(wavelength)

        intensity_min = min(intensity)
        intensity_max = max(intensity)
        std_max = max(standard_deviation)

        if verbose:
            print("creating backgroundimage...")
        # wird resized, deshalb height=1
        ax.imshow(
            make_spectrum_image(int(len(wavelength)), 1, wavelength),
            extent=[
                wave_min,
                wave_max,
                intensity_min - std_max,
                intensity_max + std_max,
            ],
            aspect="auto",
            alpha=0.4,
        )

        if verbose:
            print("creating plot...")

        rate = metadata[REPETITIONS_INDEX]
        if setting.sliced():
            rate = setting.intervall_end - setting.intervall_start

        ax.scatter(
            wavelength,
            intensity,
            label="Mittelwert von {0} Messungen".format(rate),
            color=colors[iterator],
            s=1,
        )
        print(len(intensity), len(standard_deviation))

        assert len(intensity) == len(standard_deviation)
        ax.fill_between(
            wavelength,
            intensity - standard_deviation,
            intensity + standard_deviation,
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

    plt.xlabel("Wellenlänge in nm")
    plt.ylabel("Intensität in Counts")

    title = NAME

    for setting in plotting_settings:
        if setting.sliced():
            title = "{0} bis {1} Laserschüsse {2}".format(
                setting.intervall_start, setting.intervall_end, NAME
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
    title += ".jpg"

    plt.draw()

    try:
        os.makedirs("Plots/", 0o777)
    except OSError as error:
        print(error)
        print("(directory is already existent)")

    fig.savefig("Plots/" + title.replace("%", "Prozent"), dpi=300, bbox_inches="tight")
    if verbose:
        print("saved plot")
    # plt.show(block=False)
    plt.close()
    plt.cla()
    plt.clf()


def make_plot():
    pass


class UnixUser(object):

    def __init__(self, uid, gid=None):
        self.uid = uid
        self.gid = gid

    def __enter__(self):
        self.cache = os.getuid(), os.getgid()
        if self.gid is not None:
            os.setgid(self.gid)
        os.setuid(self.uid)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.setuid(self.cache[0])
        os.setgid(self.cache[1])


def time_measurement(iter: int):

    seconds_list = [time.time()]

    for i in range(iter):
        turn_on_laser()
        time.sleep(IRRADITION_TIME / 1000.0)
        get_data()
        turn_off_laser()
        time.sleep(MEASUREMENT_DELAY / 1000.0)
        # print(i)
        seconds_list.append(time.time())

    total_time_millis = int(round(time.time() * 1000)) - int(
        round(seconds_list[0] * 1000)
    )
    print("measurements took: {0} ms".format(total_time_millis))
    delays_time = (MEASUREMENT_DELAY + 2 * ARDUINO_DELAY + IRRADITION_TIME) * iter
    print("thereof delays: {0} ms".format(delays_time))
    print("a measurement took: {0} ms".format(total_time_millis / 1.0 / iter))
    print("std: +/- " + str(np.std(np.array(seconds_list) - seconds_list[0])))
    print("without delays:")
    print(
        "a measurement took: {0} ms".format(
            (total_time_millis - delays_time) / 1.0 / iter
        )
    )
    print(
        "std: +/- "
        + str(
            np.std(
                np.array(seconds_list)
                - seconds_list[0]
                - (MEASUREMENT_DELAY + 2 * ARDUINO_DELAY + IRRADITION_TIME)
            )
        )
    )


if __name__ == "__main__":

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

    if DEBUG:
        NAME += "_DEBUG"
        DIR_PATH = "Messungen/Debug/" + NAME + "/"
    else:
        DIR_PATH = "Messungen/" + NAME + "/"

    try:
        os.makedirs(DIR_PATH, 0o777)
    except OSError as error:
        print(error)
        print("(directory is already existent)")

    if not DEBUG:
        spectrometer_setup()
        ## bitte entfernen.
        if not CONTINOUS:
            arduino_setup("/dev/ttyUSB0", 1)

    """
    measurements = []

    for i in range (REPETITIONS):
        measurements.append(get_data())
        time.sleep(DELAY / 1000.0)
    """
    # minimal schneller als jedes Mal list.append()
    measurements = np.zeros([REPETITIONS, 2048, 2], dtype=float)

    if CONTINOUS and not DEBUG:
        turn_on_laser()

    seconds = time.time()

    if DEBUG:
        for i in range(REPETITIONS):
            measurements[i] = np.zeros([2048, 2], dtype=float)
    elif CONTINOUS:
        for i in range(REPETITIONS):
            measurements[i] = get_data()
            time.sleep(MEASUREMENT_DELAY / 1000.0)
            print(i)
    else:
        for i in range(REPETITIONS):
            turn_on_laser()
            time.sleep(IRRADITION_TIME / 1000.0)
            measurements[i] = get_data()
            turn_off_laser()
            # TODO: implement (Thread, da es lange dauert)
            # threading.Thread(target=make_plot, args=(measurements[i])).start()
            time.sleep(MEASUREMENT_DELAY / 1000.0)
            print(i)
            if time.time() - seconds > TIMEOUT:
                print("reached timeout!")
                break

    total_time_millis = int(round(time.time() * 1000)) - int(round(seconds * 1000))
    print("measurements took: {0} ms".format(total_time_millis))
    delays_time = (
        MEASUREMENT_DELAY + 2 * ARDUINO_DELAY + IRRADITION_TIME
    ) * REPETITIONS
    print("thereof delays: {0} ms".format(delays_time))
    print("a measurement took: {0} ms".format(total_time_millis / 1.0 / REPETITIONS))
    print("without delays:")
    print(
        "a measurement took: {0} ms".format(
            (total_time_millis - delays_time) / 1.0 / REPETITIONS
        )
    )

    # Spektrometer freigeben
    if not DEBUG:
        sn.reset(spectrometer)

    metadata = np.zeros(9, dtype=int)
    metadata[INTTIME_INDEX] = INTTIME
    metadata[INTENSITY_INDEX] = INTENSITY
    metadata[SCAN_AVG_INDEX] = SCAN_AVG
    metadata[SMOOTH_INDEX] = SMOOTH
    metadata[XTIMING_INDEX] = XTIMING
    metadata[REPETITIONS_INDEX] = REPETITIONS
    metadata[DELAY_INDEX] = DELAY
    metadata[IRRADITION_TIME_INDEX] = IRRADITION_TIME
    metadata[CONTINOUS_INDEX] = int(CONTINOUS)

    if OVERWRITE:
        # manche Dateisysteme unterstützen keinen Doppelpunkt im Dateinamen
        file_name = DIR_PATH + str(datetime.now()).replace(":", "_")
    else:
        file_name = DIR_PATH + "Messung"

    np.savez_compressed(file_name, np.array(measurements), np.array(metadata))
    os.chmod(file_name + ".npz", 0o777)

    plot_results([PlottingSettings(DIR_PATH)])
