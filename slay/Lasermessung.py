from multiprocessing import Process
from Laserplot import Laserplot
from PlottingSettings import PlottingSettings

from NKT import LaserController

from MeasurementSettings import MeasurementSettings

import traceback
import serial
import sys
import os
import time
import datetime
import numpy as np
import threading

np.set_printoptions(suppress=True)

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
        self.timestamps = np.zeros(length, dtype=float)
        self.wav = wav
        self.curr_measurement_index = -1

    def get_data(self):
        return self.measurements, self.wav, self.curr_measurement_index


class Lasermessung:
    """Wrapper für die Durchführung von slay."""

    def is_docker(self):
        from pathlib import Path

        cgroup = Path("/proc/self/cgroup")
        return (
            Path("/.dockerenv").is_file()
            or cgroup.is_file()
            and "docker" in cgroup.read_text()
        )

    def __init__(
        self,
        arduino_path: str,
        laser_path: str,
        MEASUREMENT_SETTINGS: MeasurementSettings,
    ):

        try:

            if not self.is_docker():
                raise RuntimeError("Not running in a docker container.")
            # from stellarnet.stellarnet_driverLibs import stellarnet_driver3 as sn
            from driverLibs import stellarnet_driver3 as sn

            # print(sn.version())

            DEBUG = False
        except Exception:
            print("\n Failed to load the stellarnet library.\n")
            print(traceback.format_exc())

            # exit()
            print("Running in debug-mode.\n")
            import VirtualSpectrometer as sn

            DEBUG = True

        self.sn = sn
        self.DEBUG = DEBUG

        self.MEASUREMENT_SETTINGS = MEASUREMENT_SETTINGS
        self.spectrometer_setup()
        self.arduino_setup(arduino_path, 3)  # 1 ist definitiv zu kurz (getestet)

        self.set_arduino_variable(
            "PWM405", self.MEASUREMENT_SETTINGS.laser.INTENSITY_405
        )
        self.set_arduino_variable(
            "Num445", self.MEASUREMENT_SETTINGS.laser.NUM_PULSES_445
        )
        self.set_arduino_variable(
            "Del445", self.MEASUREMENT_SETTINGS.laser.PULSE_DELAY_445
        )
        self.set_arduino_variable(
            "ConMea", int(self.MEASUREMENT_SETTINGS.laser.CONTINOUS)
        )
        self.set_arduino_variable(
            "ExpDel",
            (
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
                + (
                    self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
                    + self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY * 2
                    if not self.MEASUREMENT_SETTINGS.laser.CONTINOUS
                    else 0
                )
                + self.MEASUREMENT_SETTINGS.specto.INTTIME
                + self.MEASUREMENT_SETTINGS.WATCHDOG_GRACE
            ),
        )

        print(
            "Watchdog gesetzt auf: "
            + str(
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
                + (
                    self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
                    + self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY * 2
                    if not self.MEASUREMENT_SETTINGS.laser.CONTINOUS
                    else 0
                )
                + self.MEASUREMENT_SETTINGS.specto.INTTIME
                + self.MEASUREMENT_SETTINGS.WATCHDOG_GRACE
            )
        )

        self.nkt = LaserController(laser_path)
        # erst später anschalten
        self.nkt.set_register("emission", 0)

        max_freq = self.nkt.get_register("max_frequency")  # 21502
        print(f"max freq is {max_freq}")
        # um auch Bruchteile zu erlauben
        freq = int(max_freq / 100 * self.MEASUREMENT_SETTINGS.laser.INTENSITY_NKT)
        self.nkt.set_register("pulse_frequency", freq)
        print(f"Frequenz auf {freq} gesetzt.")
        self.nkt.set_register("operating_mode", 4)  # external trigger high signl
        self.led_green()

        # measurements = []

        # for i in range (self.MEASUREMENT_SETTINGS["laser"]["REPETITIONS"]):
        #     measurements.append(get_data())
        #     time.sleep(self.MEASUREMENT_SETTINGS["DELAY"] / 1000.0)

        # minimal schneller als jedes Mal list.append()
        self.messdata = Messdata(
            self.MEASUREMENT_SETTINGS.laser.REPETITIONS, self.get_wav()
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

            class Arduino:
                def write(self, value):
                    pass

            self.arduino = Arduino()

    def set_arduino_variable(self, name, value):
        if (
            len(str(value)) > 5 and "ExpDel" not in name
        ):  # int hat fünf chars als Maximum der Dezimalschreibweise. ExpDel ist schon auf long umgestellt (zehn Chars)
            print(
                f"Der Wert {value} für {name} ist wahrscheinlich zu groß und wird ein roll-over erzeugen.",
                flush=True,
            )
        if len(name) > 6:
            print(
                f"Die Länge des Namens ist aktuell auf drei Chars gestellt. {name} auf {value} zu setzen ist daher wahrscheinlich eine schlechte Idee.",
                flush=True,
            )
        # 2 ist der Char-Code für "Variable setzen" (siehe Arduino-Code)
        self.arduino.write(f"2{name}={value}\n".encode())
        time.sleep(self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY / 1000.0)

    def send_arduino_signal(self, signal):
        self.arduino.write(str(signal).encode())
        time.sleep(self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY / 1000.0)

    def turn_on_laser(self):
        """Sendet eine Eins als Byte zum Arduino, welche ein Anschalten der Laser signalisiert."""
        self.arduino.write(b"1")
        time.sleep(self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY / 1000.0)

    def turn_off_laser(self):
        """Sendet eine Null als Byte zum Arduino, welche ein Ausschalten der Laser signalisiert."""
        self.arduino.write(b"0")
        time.sleep(self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY / 1000.0)

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

        # stellarnet_driver3.TimeoutError: Read spectrum
        # aber wir haben doch auch kein externes Triggern aktiviert? Also unser Spektrometer
        # hat das Modul einfach nicht...ist USB "externes Triggern"?
        # self.sn.ext_trig(self.spectrometer, False)
        self.sn.ext_trig(self.spectrometer, True)

        # True ignoriert die ersten Messdaten, da diese ungenau sein können
        # (durch Änderung der Integrationszeit)
        self.sn.setParam(
            self.spectrometer,
            self.MEASUREMENT_SETTINGS.specto.INTTIME,
            self.MEASUREMENT_SETTINGS.specto.SCAN_AVG,
            self.MEASUREMENT_SETTINGS.specto.SMOOTH,
            self.MEASUREMENT_SETTINGS.specto.XTIMING,
            True,
        )

    def get_wav(self):
        return self.sn.getSpectrum_X(self.spectrometer).reshape(
            2048,
        )

    def get_data(self):
        """Liest die Daten des Spektrometers aus."""

        # print(threading.current_thread() == threading.main_thread())

        # start_time = time.time()
        # var = sn.array_spectrum(spectrometer, wav)
        # print((time.time() - start_time) * 1000)
        # return var
        # print(sn.array_spectrum(spectrometer, wav).shape)  # (2048, 2)
        # print(sn.getSpectrum_Y(spectrometer).shape)  # (2048,)

        # return sn.array_spectrum(spectrometer, wav)
        return self.sn.getSpectrum_Y(self.spectrometer)

    def led_red(self):
        self.set_arduino_variable("SetLED", 511)

    def led_green(self):
        self.set_arduino_variable("SetLED", 151)

    def stop_all_devices(self):
        # emission 0 gibt einen Fehler, wenn external gate weiterhin "LASER AN!!!!" schreit
        self.turn_off_laser()
        self.nkt.set_register("emission", 0)
        # manuelles triggern erlauben und (vorsichtshalber) die power runterstellen.
        self.nkt.set_register("power", 1)
        self.nkt.set_register("operating_mode", 0)  # internal trigger
        # Spektrometer freigeben
        self.sn.reset(self.spectrometer)
        self.led_green()

    def test_measurement_duration(self, iters: int):
        """Misst die Zeit, die ein Messvorgang dauert."""

        seconds_list = [time.time()]

        for _ in range(iters):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME / 1000.0)
            self.get_data()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)
            # print(i)
            seconds_list.append(time.time())

        total_time_millis = int(round(time.time() * 1000)) - int(
            round(seconds_list[0] * 1000)
        )

        print(f"measurements took: {total_time_millis} ms")
        delays_time = (
            self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
            + 2 * self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY
            + self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
        ) * iters
        print(f"thereof delays: {delays_time} ms")
        print(f"a measurement took: {total_time_millis / 1.0 / iters} ms")
        print(f"std: +/- {np.std(np.array(seconds_list) - seconds_list[0])}")
        print("without delays:")
        print(
            f"a measurement took: {(total_time_millis - delays_time) / 1.0 / iters} ms"
        )
        print(
            f"std: +/- {np.std(np.array(seconds_list) - seconds_list[0] - (delays_time))}"
        )

    def time_measurement(self, measure):

        seconds = time.time()

        print("\nrepetitions:")
        for i in range(self.MEASUREMENT_SETTINGS.laser.REPETITIONS):
            measure(i)
            sys.stdout.write("\r")
            sys.stdout.write(" " + str(i))
            sys.stdout.flush()
            self.messdata.curr_measurement_index = i
            if time.time() - seconds > self.MEASUREMENT_SETTINGS.TIMEOUT:
                print("\nreached timeout!")
                break

        # \r resetten
        print()
        print("finished measurements")

        total_time_millis = int(round(time.time() * 1000)) - int(round(seconds * 1000))
        print(f"measurements took: {total_time_millis} ms")
        delays_time = (
            self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
            + 2 * self.MEASUREMENT_SETTINGS.laser.ARDUINO_DELAY
            + self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
        ) * self.MEASUREMENT_SETTINGS.laser.REPETITIONS
        print(f"thereof delays: {delays_time} ms")
        print(
            f"a measurement took: {total_time_millis / 1.0 / self.MEASUREMENT_SETTINGS.laser.REPETITIONS} ms"
        )
        print("without delays:")
        print(
            f"a measurement took: {(total_time_millis - delays_time) / 1.0 / self.MEASUREMENT_SETTINGS.laser.REPETITIONS} ms"
        )

    def watchdog_wrap(self, watchdog_target, func, timeout_sec=3):
        p = Process(
            target=watchdog_target,
            daemon=True,
        )
        p.start()

        func()

        p.terminate()
        p.join(timeout=timeout_sec)
        if p.is_alive():
            p.kill()

    def continuous_measurement(self):

        # if self.arduino is None:
        #     print("Arduino not set up! Can not measure.")
        #     return

        def measure(i):
            self.messdata.measurements[i] = self.get_data()
            self.messdata.timestamps[i] = time.time()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.led_red()
        # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
        # (Emission muss jedoch erst an sein, bevor der LASER extern getriggert werden kann)
        self.nkt.set_register("emission", 1)

        def send_and_wait():
            while True:
                self.send_arduino_signal("3")
                time.sleep(
                    self.MEASUREMENT_SETTINGS.specto.INTTIME / 1000
                    + self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000
                )

        def measure_func():
            self.turn_on_laser()
            print("turned on lasers", flush=True)
            self.time_measurement(measure)
            self.stop_all_devices()

        self.watchdog_wrap(send_and_wait, measure_func)

    def pulse_measurement(self):

        if self.arduino is None:
            print("Arduino not set up! Can not measure.")
            return

        def measure(i):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME / 1000.0)
            self.messdata.measurements[i] = self.get_data()
            self.messdata.timestamps[i] = time.time()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.led_red()
        # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
        self.nkt.set_register("emission", 1)
        self.time_measurement(measure)
        self.stop_all_devices()

    def infinite_measuring(self, gui=True, nkt_on=True):
        if nkt_on:
            self.nkt.set_register("operating_mode", 0)  # internal trigger
            self.nkt.set_register("emission", 1)

        def send_and_wait():
            while True:
                self.send_arduino_signal("3")
                time.sleep(
                    self.MEASUREMENT_SETTINGS.specto.INTTIME / 1000
                    + self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000
                )
                data = self.arduino.read(self.arduino.inWaiting())
                if data != b"":
                    print(
                        "in waiting: " + str(data),
                        flush=True,
                    )  # flushInput()

        def infinite_measure():
            self.turn_on_laser()

            if gui:
                self.enable_gui()
            try:
                while True:
                    next_measurement_index = (
                        self.messdata.curr_measurement_index + 1
                    ) % len(self.messdata.measurements)
                    self.messdata.measurements[next_measurement_index] = self.get_data()
                    time.sleep(
                        self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0
                    )
                    self.messdata.curr_measurement_index = next_measurement_index
            except KeyboardInterrupt:
                self.disable_gui()
                self.sn.reset(self.spectrometer)
                self.stop_all_devices()

        self.watchdog_wrap(send_and_wait, infinite_measure)

    def measure(self, gui=True, thread=True):

        if gui:
            self.enable_gui()

        def run():
            if self.MEASUREMENT_SETTINGS.laser.CONTINOUS:
                self.continuous_measurement()
            else:
                self.pulse_measurement()

        if thread:
            t = threading.Thread(
                target=run,
                daemon=True,  # Main-Thread soll nicht auf den Thread warten
            )
            t.start()
            t.join()
        else:
            run()

        if gui:
            self.disable_gui()

    def save(self, DIR_PATH, plt_only=False, measurements_only=False):
        """Schreibt die Messdaten in einen spezifizierten Ordner."""
        # gemeinsame Typen werden in einem gemeinsamen Ordner gespeichert

        name = "DEBUG" if self.DEBUG else self.MEASUREMENT_SETTINGS.TYPE
        name += (
            "/Kontinuierlich" if self.MEASUREMENT_SETTINGS.laser.CONTINOUS else "/Puls"
        )

        type_dir = DIR_PATH + name + "/"
        os.makedirs(type_dir, 0o777, exist_ok=True)

        code_name = "overwrite-messung"
        if self.MEASUREMENT_SETTINGS.UNIQUE:
            # manche Dateisysteme unterstützen keinen Doppelpunkt im Dateinamen
            code_name = str(datetime.datetime.now()).replace(":", "_")

        file_name = type_dir + code_name

        if not plt_only:
            with open(
                file_name + ".json",
                "w",
                encoding="utf-8",
            ) as json_file:
                self.MEASUREMENT_SETTINGS.save_as_json(json_file)

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
                np.array(self.messdata.timestamps),
            )
            os.chmod(file_name + ".npz", 0o777)

        if not measurements_only:
            if not hasattr(self, "plot"):
                self.plot = Laserplot()

            self.plot.plot_results(
                [PlottingSettings(type_dir, code_name, True)],
                self.MEASUREMENT_SETTINGS,
            )

    # def get_measurement_data(self):
    #     """Gibt alle notwendigen Daten zurück, die für eine Auswertung benötigt werden."""
    #     return self.MEASUREMENT_SETTINGS, self.messdata.measurements, self.messdata.wav

    def plot_path(self, settings, mSettings=None):

        if not hasattr(self, "plot"):
            self.plot = Laserplot()

        self.plot.plot_results(
            settings,
            self.MEASUREMENT_SETTINGS if mSettings == None else mSettings,
        )

    def enable_gui(self):
        self.plot = Laserplot()
        self.plot.start_gui(self.MEASUREMENT_SETTINGS.laser.REPETITIONS, self.messdata)

    def disable_gui(self):
        self.plot.stop_gui()
        del self.plot

    # def plot(self, settings, measurement_data, wav):
    #     self.plot.plot_results(
    #         [PlottingSettings(DIR_PATH)], settings, measurement_data, wav
    #     )
