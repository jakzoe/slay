import traceback
import serial
import sys
import os
import time
import datetime
import json
import numpy as np

np.set_printoptions(suppress=True)

from Laserplot import Laserplot
from PlottingSettings import PlottingSettings


# Formatierung von Fehlern
try:
    from IPython.core import ultratb

    sys.excepthook = ultratb.FormattedTB(
        color_scheme="Linux", call_pdb=False  # mode="Verbose",
    )
except Exception as e:
    print(f"Failed to load IPython for the formatting of errors: {e}")


class Messdata:
    def __init__(self, length, wav):
        self.measurements = np.zeros([length, len(wav)], dtype=float)
        self.wav = wav
        self.curr_measurement_index = -1


class Lasermessung:
    """Wrapper für die Durchführung von slay."""

    def __init__(self, arduino_path, MEASUREMENT_SETTINGS):

        try:
            # from stellarnet.stellarnet_driverLibs import stellarnet_driver3 as sn
            from driverLibs import stellarnet_driver3 as sn

            # print(sn.version())

            DEBUG = False
        except Exception:
            print("\n Failed to load the stellarnet library.\n")
            print(traceback.format_exc())

            # exit()
            print("Running in debug-mode.\n")
            import virtual_spectrometer as sn

            DEBUG = True

        self.sn = sn
        self.DEBUG = DEBUG

        self.MEASUREMENT_SETTINGS = MEASUREMENT_SETTINGS
        self.spectrometer_setup()
        self.arduino_setup(arduino_path, 1)

        # measurements = []

        # for i in range (self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]):
        #     measurements.append(get_data())
        #     time.sleep(self.MEASUREMENT_SETTINGS["DELAY"] / 1000.0)

        # minimal schneller als jedes Mal list.append()
        self.messdata = Messdata(
            self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"], self.get_wav()
        )

    def arduino_setup(self, port, wait):
        try:
            """Verbindet sich mit dem Arduino."""
            self.arduino = serial.Serial(port=port, baudrate=9600, timeout=5)
            # auf den Arduino warten
            time.sleep(wait)
            self.arduino.flush()
        except serial.serialutil.SerialException as e:
            print(f"Failed to connect to the Arduino: {e}")
            self.arduino = None

    def turn_on_laser(self):
        """Sendet eine Eins als Byte zum Arduino, welche ein Anschalten der Laser signalisiert."""
        self.arduino.write(b"1\n")
        time.sleep(self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"] / 1000.0)

    def turn_off_laser(self):
        """Sendet eine Null als Byte zum Arduino, welche ein Ausschalten der Laser signalisiert."""
        self.arduino.write(b"0\n")
        time.sleep(self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"] / 1000.0)

    def spectrometer_setup(self):
        """Verbindet sich mit dem Spektrometer."""

        self.spectrometer = self.sn.array_get_spec_only(0)

        # es gibt 2048 Elemente:
        # Jede der 864 Wellenlängen ist immer mit zwei bis drei Nachkommastellen vertreten
        # print(wav[0], wav[-1]) -> 285.24 1149.4808101739814
        # for i in wav:
        #     print(i)
        # print(len(wav))

        # print(spectrometer)
        # print("\nDevice ID: ", sn.getDeviceId(spectrometer))

        self.sn.ext_trig(self.spectrometer, True)
        # True ignoriert die ersten Messdaten, da diese ungenau sein können
        # (durch Änderung der Integrationszeit)

        self.sn.setParam(
            self.spectrometer,
            self.MEASUREMENT_SETTINGS["specto"]["INTTIME"],
            self.MEASUREMENT_SETTINGS["specto"]["SCAN_AVG"],
            self.MEASUREMENT_SETTINGS["specto"]["SMOOTH"],
            self.MEASUREMENT_SETTINGS["specto"]["XTIMING"],
            True,
        )

    def get_wav(self):
        return self.sn.getSpectrum_X(self.spectrometer).reshape(
            2048,
        )

    def get_data(self):
        """Liest die Daten des Spektrometers aus."""
        # start_time = time.time()
        # var = sn.array_spectrum(spectrometer, wav)
        # print((time.time() - start_time) * 1000)
        # return var
        # print(sn.array_spectrum(spectrometer, wav).shape)  # (2048, 2)
        # print(sn.getSpectrum_Y(spectrometer).shape)  # (2048,)

        # return sn.array_spectrum(spectrometer, wav)
        return self.sn.getSpectrum_Y(self.spectrometer)

    def test_measurement_duration(self, iters: int):
        """Misst die Zeit, die ein Messvorgang dauert."""

        seconds_list = [time.time()]

        for _ in range(iters):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS["IRRADITION_TIME"] / 1000.0)
            self.get_data()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"] / 1000.0)
            # print(i)
            seconds_list.append(time.time())

        total_time_millis = int(round(time.time() * 1000)) - int(
            round(seconds_list[0] * 1000)
        )
        print(f"measurements took: {total_time_millis} ms")
        delays_time = (
            self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"]
            + 2 * self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"]
            + self.MEASUREMENT_SETTINGS["IRRADITION_TIME"]
        ) * iters
        print(f"thereof delays: {delays_time} ms")
        print(f"a measurement took: {total_time_millis / 1.0 / iters} ms")
        print("std: +/- " + str(np.std(np.array(seconds_list) - seconds_list[0])))
        print("without delays:")
        print(
            f"a measurement took: {(total_time_millis - delays_time) / 1.0 / iters} ms"
        )
        print(
            "std: +/- "
            + str(
                np.std(
                    np.array(seconds_list)
                    - seconds_list[0]
                    - (
                        self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"]
                        + 2 * self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"]
                        + self.MEASUREMENT_SETTINGS["IRRADITION_TIME"]
                    )
                )
            )
        )

    def time_measurement(self, measure):

        seconds = time.time()

        print("\nrepetitions:")
        for i in range(self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]):
            measure(i)
            sys.stdout.write("\r")
            sys.stdout.write(" " + str(i))
            sys.stdout.flush()
            self.messdata.curr_measurement_index = i
            # print(i)
            if time.time() - seconds > self.MEASUREMENT_SETTINGS["TIMEOUT"]:
                print("\nreached timeout!")
                break

        # \r resetten
        print()

        total_time_millis = int(round(time.time() * 1000)) - int(round(seconds * 1000))
        print(f"measurements took: {total_time_millis} ms")
        delays_time = (
            self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"]
            + 2 * self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"]
            + self.MEASUREMENT_SETTINGS["IRRADITION_TIME"]
        ) * self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]
        print(f"thereof delays: {delays_time} ms")
        print(
            f'a measurement took: {total_time_millis / 1.0 / self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]} ms'
        )
        print("without delays:")
        print(
            f'a measurement took: {(total_time_millis - delays_time) / 1.0 / self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]} ms'
        )

        # Spektrometer freigeben
        self.sn.reset(self.spectrometer)

    def continuous_measurement(self):

        if self.arduino is None:
            print("Arduino not set up! Can not measure.")
            return

        def measure(i):
            self.messdata.measurements[i] = self.get_data()
            time.sleep(self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"] / 1000.0)

        # TODO: turn on!
        self.time_measurement(measure)
        # TODO: turn off!

    def pulse_measurement(self):

        if self.arduino is None:
            print("Arduino not set up! Can not measure.")
            return

        def measure(i):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS["IRRADITION_TIME"] / 1000.0)
            self.messdata.measurements[i] = self.get_data()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"] / 1000.0)

        self.time_measurement(measure)

    def infinite_measuring(self):
        try:
            while True:
                next_measurement_index = (
                    self.messdata.curr_measurement_index + 1
                ) % len(self.messdata.measurements)
                self.messdata.measurements[next_measurement_index] = self.get_data()
                time.sleep(
                    self.MEASUREMENT_SETTINGS["laser"]["MEASUREMENT_DELAY"] / 1000.0
                )
                self.messdata.curr_measurement_index = next_measurement_index
        except KeyboardInterrupt:
            self.sn.reset(self.spectrometer)
            return

    def measure(self):
        if self.MEASUREMENT_SETTINGS["laser"]["CONTINOUS"]:
            self.continuous_measurement()
        else:
            self.pulse_measurement()

    def save(self, DIR_PATH):
        """Schreibt die Messdaten in einen spezifizierten Ordner."""
        # gemeinsame Typen werden in einem gemeinsamen Ordner gespeichert

        name = "DEBUG" if self.DEBUG else self.MEASUREMENT_SETTINGS["TYPE"]
        name += (
            "/Kontinuierlich"
            if self.MEASUREMENT_SETTINGS["laser"]["CONTINOUS"]
            else "/Puls"
        )

        type_dir = DIR_PATH + name + "/"
        os.makedirs(type_dir, 0o777, exist_ok=True)

        if self.MEASUREMENT_SETTINGS["UNIQUE"]:
            # manche Dateisysteme unterstützen keinen Doppelpunkt im Dateinamen
            file_name = type_dir + str(datetime.datetime.now()).replace(":", "_")
        else:
            file_name = type_dir + "overwrite-messung"

        with open(
            file_name + ".json",
            "w",
            encoding="utf-8",
        ) as json_file:
            json.dump(self.MEASUREMENT_SETTINGS, json_file, indent=4)

        # metadata = np.zeros(9, dtype=int)
        # metadata[0] = self.MEASUREMENT_SETTINGS["INTTIME"]
        # metadata[1] = self.MEASUREMENT_SETTINGS["INTENSITY"]
        # metadata[2] = self.MEASUREMENT_SETTINGS["SCAN_AVG"]
        # metadata[3] = self.MEASUREMENT_SETTINGS["SMOOTH"]
        # metadata[4] = self.MEASUREMENT_SETTINGS["XTIMING"]
        # metadata[5] = self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]
        # metadata[6] = self.MEASUREMENT_SETTINGS["ARDUINO_DELAY"]
        # metadata[7] = self.MEASUREMENT_SETTINGS["IRRADITION_TIME"]
        # metadata[8] = int(self.MEASUREMENT_SETTINGS["laser"]["CONTINOUS"])

        np.savez_compressed(
            file_name,
            np.array(self.messdata.measurements),
            np.array(self.messdata.wav),
        )
        os.chmod(file_name + ".npz", 0o777)

        if not hasattr(self, "plot"):
            self.plot = Laserplot()

        self.plot.plot_results(
            [PlottingSettings(file_name)],
            self.MEASUREMENT_SETTINGS,
            self.messdata.measurements,
            self.messdata.wav,
        )

    def get_measurement_data(self):
        """Gibt alle notwendigen Daten zurück, die für eine Auswertung benötigt werden."""
        return self.MEASUREMENT_SETTINGS, self.messdata.measurements, self.messdata.wav

    def enable_gui(self):
        self.plot = Laserplot()
        self.plot.start_gui_thread(
            self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"], self.messdata
        )

    # def plot(self, settings, measurement_data, wav):
    #     self.plot.plot_results(
    #         [PlottingSettings(DIR_PATH)], settings, measurement_data, wav
    #     )
