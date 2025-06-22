from slay.spectrum_plot import SpectrumPlot
from slay.settings import PlotSettings
from slay.settings import MeasurementSettings

from slay.lasers import NKT
from slay.lasers import LTB


from multiprocessing import Process
import threading
import concurrent.futures
import traceback
import serial
import sys
import os
import time
import datetime
import numpy as np


np.set_printoptions(suppress=True)

# Formatierung von Fehlern
try:
    from IPython.core import ultratb

    sys.excepthook = ultratb.FormattedTB()
except Exception as e:
    print(f"Failed to load IPython for the formatting of errors: {e}")


class SpectrumData:
    def __init__(self, num_gradiants, repetitions, wav):
        self.measurements = np.zeros(
            (num_gradiants, repetitions, len(wav)), dtype=float
        )
        self.timestamps = np.zeros((num_gradiants, repetitions), dtype=float)
        self.wav = wav
        self.curr_gradiant = -1
        self.curr_measurement_index = -1

    def get_data(self):
        return self.measurements, self.wav, self.curr_measurement_index


class Measurement:
    """Wrapper für die Durchführung von slay."""

    def is_docker(self):
        from pathlib import Path

        cgroup = Path("/proc/self/cgroup")
        return (
            Path("/.dockerenv").is_file()
            or cgroup.is_file()
            and "docker" in cgroup.read_text(encoding="utf-8")
        )

    def __init__(
        self,
        serial_path: str,
        nkt_path: str,
        ltb_path: str,
        MEASUREMENT_SETTINGS: MeasurementSettings,
    ):

        try:

            if not self.is_docker():
                raise RuntimeError("Not running in a docker container.")
            # from stellarnet.stellarnet_driverLibs import stellarnet_driver3 as sn
            from driverLibs import stellarnet_driver3 as sn  # type: ignore

            # print(sn.version())

            DEBUG = False
        except Exception:
            print("\n Failed to load the stellarnet library.\n")
            print(traceback.format_exc())

            # exit()
            print("Running in debug-mode.\n")
            from slay.virtual import Spectrometer as sn

            DEBUG = True

        self.sn = sn
        self.DEBUG = DEBUG

        self.MEASUREMENT_SETTINGS = MEASUREMENT_SETTINGS

        start_time = time.time()

        # für das Spektrometer und den LTb muss jeweils ziemlich lange gewartet werden
        # (bei dem Spektrometer je nach Integrationszeit, da bei der Initialisierung eine erste Messung durchgeführt wird)
        self.init_tasks = (
            (self.init_spectrometer, ()),
            (self.init_mcu, (serial_path, 3)),
            (self.init_nkt, (nkt_path,)),
            (self.init_ltb, (ltb_path,)),
        )

        # ProcessPoolExecutor funktioniert nur, wenn die Funktionen/Argumente gepickelt werden können (außerhalb der Klasse definiert etc.)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(func, *args) for func, args in self.init_tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()

        # self.init_spectrometer()
        # self.init_mcu(serial_path, wait=3)
        # self.init_nkt(nkt_path)
        # self.init_ltb(ltb_path)

        print(
            f"Finished initializing the measurement in {time.time() - start_time:.2f} seconds."
        )
        self.messdata = SpectrumData(
            self.MEASUREMENT_SETTINGS.laser.num_gradiants,
            self.MEASUREMENT_SETTINGS.laser.REPETITIONS,
            self.get_wav(),
        )

        self.set_laser_powers(0)
        # aktuell noch keine Output-Power
        self.led_green()
        print("Finished initializing the measurement.")

    def set_laser_powers(self, index):

        max_pwm_counts_445 = (
            pow(2, self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_445[index]) - 1
        )
        max_pwm_counts_405 = (
            pow(2, self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_405[index]) - 1
        )

        assert self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_405[index] <= 1
        assert self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_445[index] <= 1
        assert self.MEASUREMENT_SETTINGS.laser.INTENSITY_NKT[index] <= 1

        self.set_firmware_variable(
            "Dut405",
            int(
                self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_405[index]
                * max_pwm_counts_405
            ),
        )
        self.set_firmware_variable(
            "Dut445",
            int(
                self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_445[index]
                * max_pwm_counts_445
            ),
        )
        self.set_firmware_variable(
            "Frq405", self.MEASUREMENT_SETTINGS.laser.PWM_FREQ_405[index]
        )
        self.set_firmware_variable(
            "Frq445", self.MEASUREMENT_SETTINGS.laser.PWM_FREQ_445[index]
        )
        self.set_firmware_variable(
            "Res405", self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_405[index]
        )
        self.set_firmware_variable(
            "Res445", self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_445[index]
        )
        self.set_firmware_variable(
            "FrqLTB", self.MEASUREMENT_SETTINGS.laser.REPETITIONS_LTB[index]
        )

        self.set_firmware_variable(
            "ConMea", int(self.MEASUREMENT_SETTINGS.laser.CONTINOUS)
        )

        self.set_firmware_variable(
            "ExpDel",
            (
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
                + (
                    self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
                    + self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY * 2
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
                    + self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY * 2
                    if not self.MEASUREMENT_SETTINGS.laser.CONTINOUS
                    else 0
                )
                + self.MEASUREMENT_SETTINGS.specto.INTTIME
                + self.MEASUREMENT_SETTINGS.WATCHDOG_GRACE
            )
        )

        max_freq = self.nkt.get_register("max_frequency")  # 21502
        print(f"NKT: max freq is {max_freq}")
        # um auch Bruchteile zu erlauben
        freq = int(
            max_freq / 100 * self.MEASUREMENT_SETTINGS.laser.INTENSITY_NKT[index]
        )
        self.nkt.set_register("pulse_frequency", freq)
        print(f"NKT: Frequenz auf {freq} gesetzt.")
        self.nkt.set_register("operating_mode", 4)  # external trigger high signl

        self.ltb.set_hv_voltage(self.MEASUREMENT_SETTINGS.laser.INTENSITY_LTB[index])
        # wird jetzt auch über den mcu getriggert
        # self.ltb.set_repetition_rate(
        #     self.MEASUREMENT_SETTINGS.laser.REPETITIONS_LTB[index]
        # )

    def init_mcu(self, port, wait):
        """Verbindet sich mit dem ArduMMCUCUino."""
        try:
            self.mcu = serial.Serial(port=port, baudrate=115200, timeout=5)
            # auf den MCU warten
            if wait <= 1:
                print("mcu: waiting more than 1 second is recommended.")
                # 1 ist definitiv zu kurz (getestet)
            time.sleep(wait)
            self.mcu.flush()
        except serial.serialutil.SerialException as e:
            print(f"Failed to connect to the MCU: {e}")
            print(
                "You may have to unplug and replug the MCU or (on Linux) run:\nsudo modprobe -r ftdi_sio && sudo modprobe ftdi_sio"
            )

            class MCU:
                def write(self, value):
                    pass

            self.mcu = MCU()

    def set_firmware_variable(self, name, value):
        # # int hat fünf chars als Maximum der Dezimalschreibweise. ExpDel ist schon auf long umgestellt (zehn Chars)
        if "ExpDel" not in name:
            if len(str(value)) > 5:
                print(
                    f"Der Wert {value} für {name} ist wahrscheinlich zu groß und wird ein roll-over erzeugen.",
                    flush=True,
                )
        elif len(str(value)) > 10:
            print(
                f"Der Wert {value} für {name} ist wahrscheinlich zu groß und wird ein roll-over erzeugen.",
                flush=True,
            )
        if len(name) > 6:
            print(
                f"Die Länge des Namens ist aktuell auf sechs Chars gestellt. {name} auf {value} zu setzen ist daher wahrscheinlich eine schlechte Idee.",
                flush=True,
            )
        print(f"sending: 2{name}={value}")
        # 2 ist der Char-Code für "Variable setzen" (siehe Firmware-Code)
        self.mcu.write(f"2{name}={value}\n".encode())
        time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def send_firmware_signal(self, signal):
        self.mcu.write(str(signal).encode())
        time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def turn_on_laser(self):
        """Sendet eine Eins als Byte zum MCU, welche ein Anschalten der Laser signalisiert."""
        self.mcu.write(b"1")
        time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def turn_off_laser(self):
        """Sendet eine Null als Byte zum MCU, welche ein Ausschalten der Laser signalisiert."""
        self.mcu.write(b"0")
        time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def init_spectrometer(self):
        """Verbindet sich mit dem Spektrometer."""

        print(
            "Connecting to the spectrometer. Thus getting a first measurement, this might take a while....",
            flush=True,
        )
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

    def init_nkt(self, nkt_path):
        self.nkt = NKT(nkt_path)
        # erst später anschalten
        self.nkt.set_register("emission", 0)

    def init_ltb(self, ltb_path):

        self.ltb = LTB(port=ltb_path)
        print("setting LTB to stand by (should take 10 seconds until it warmed up)")
        self.ltb.turn_laser_off()
        self.ltb.turn_laser_on()
        # self.ltb.start_repetition_mode()
        self.ltb.activate_external_trigger()

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
        self.set_firmware_variable("SetLED", 511)

    def led_green(self):
        self.set_firmware_variable("SetLED", 151)

    def stop_all_devices(self):
        # emission 0 gibt einen Fehler, wenn external gate weiterhin "LASER AN!!!!" schreit
        self.turn_off_laser()
        self.ltb.stop_operation()
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
            + 2 * self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY
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

        # watchdog updaten
        # self.send_firmware_signal("3")

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
            + 2 * self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY
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
            self.messdata.measurements[self.messdata.curr_gradiant][i] = self.get_data()
            self.messdata.timestamps[self.messdata.curr_gradiant][i] = time.time()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.led_red()
        # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
        # (Emission muss jedoch erst an sein, bevor der LASER extern getriggert werden kann)
        self.nkt.set_register("emission", 1)

        def send_and_wait():
            while True:
                self.send_firmware_signal("3")
                time.sleep(
                    self.MEASUREMENT_SETTINGS.specto.INTTIME / 1000
                    + self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000
                )

        def measure_func():
            self.turn_on_laser()
            print("turned on lasers", flush=True)
            self.time_measurement(measure)

        self.watchdog_wrap(send_and_wait, measure_func)

    def pulse_measurement(self):

        if self.mcu is None:
            print("Arduino not set up! Can not measure.")
            return

        def measure(i):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME / 1000.0)
            self.messdata.measurements[self.messdata.curr_gradiant][i] = self.get_data()
            self.messdata.timestamps[self.messdata.curr_gradiant][i] = time.time()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.led_red()
        # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
        self.nkt.set_register("emission", 1)
        self.time_measurement(measure)

    def infinite_measuring(self, gui=True, nkt_on=True):
        if nkt_on:
            self.nkt.set_register("operating_mode", 0)  # internal trigger
            self.nkt.set_register("emission", 1)

        def send_and_wait():
            while True:
                self.send_firmware_signal("3")
                time.sleep(
                    self.MEASUREMENT_SETTINGS.specto.INTTIME / 1000
                    + self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000
                )
                data = self.mcu.read(self.mcu.inWaiting())
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
                    ) % len(self.messdata.measurements[self.messdata.curr_gradiant])
                    self.messdata.measurements[self.messdata.curr_gradiant][
                        next_measurement_index
                    ] = self.get_data()
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

        for self.messdata.curr_gradiant in range(
            self.MEASUREMENT_SETTINGS.laser.num_gradiants
        ):

            self.set_laser_powers(self.messdata.curr_gradiant)

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

        self.stop_all_devices()

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
                self.plot = SpectrumPlot()

            self.plot.plot_results(
                [PlotSettings(type_dir, code_name, True)],
                self.MEASUREMENT_SETTINGS,
            )

    def plot_path(self, settings, mSettings=None):

        if not hasattr(self, "plot"):
            self.plot = SpectrumPlot()

        self.plot.plot_results(
            settings,
            self.MEASUREMENT_SETTINGS if mSettings == None else mSettings,
        )

    def enable_gui(self):
        self.plot = SpectrumPlot()
        self.plot.start_gui(self.MEASUREMENT_SETTINGS.laser.REPETITIONS, self.messdata)

    def disable_gui(self):
        self.plot.stop_gui()
        del self.plot

    # def plot(self, settings, measurement_data, wav):
    #     self.plot.plot_results(
    #         [PlottingSettings(DIR_PATH)], settings, measurement_data, wav
    #     )
