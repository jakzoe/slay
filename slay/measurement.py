from slay.spectrum_plot import SpectrumPlot
from slay.settings import PlotSettings
from slay.settings import MeasurementSettings

from slay.lasers import NKT
from slay.lasers import LTB
from slay.lasers import LaserProtocolError
from slay.lasers import LaserError
from slay.camera import USBCamera
from slay.live_plotter import LivePlotter
from slay.backup_service import BackupService

import multiprocessing
from threading import Thread, Event, Lock

# Python 3.14 switched the default start method on Linux to "forkserver". This requires pickling the Process target.
# That fails because ThorlabsSpectrometer holds unpicklable C-extension handles (e.g. thorlabs_cct) though,
# so this would fail when not setting the method to fork.
try:
    multiprocessing.set_start_method("fork")
except RuntimeError:
    pass
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
        self.stop_event = Event()

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

    def _resolve_spectrometer_driver(self, specto):
        try:
            if isinstance(specto, MeasurementSettings.StellarnetSpectoSettings):
                if not self.is_docker():
                    raise RuntimeError("Not running in a docker container.")
                from slay.stellarnet import StellarnetSpectrometer as SpectrometerDriver
            elif isinstance(specto, MeasurementSettings.ThorlabsSpectoSettings):
                from slay.thorlabs import ThorlabsSpectrometer as SpectrometerDriver
            else:
                raise ValueError(f"Unknown spectrometer settings type: {type(specto)}")

            return SpectrometerDriver, False
        except Exception:
            print(
                f"\n Failed to load the spectrometer driver for {type(specto).__name__}.\n"
            )
            print(traceback.format_exc())

            print("Running in debug-mode.\n")
            from slay.virtual import Spectrometer as SpectrometerDriver

            return SpectrometerDriver, True

    def __init__(
        self,
        serial_path: str,
        nkt_path: str,
        ltb_path: str,
        cam_path: str,
        cache_dir: str,
        MEASUREMENT_SETTINGS: MeasurementSettings,
        measurements_dir: str,
    ):

        self.spectrometer_driver_a, self.DEBUG_a = self._resolve_spectrometer_driver(
            MEASUREMENT_SETTINGS.specto
        )
        self.spectrometer_b = None
        self.spectrometer_driver_b, self.DEBUG_b = (None, False)
        if MEASUREMENT_SETTINGS.specto_b is not None:
            self.spectrometer_driver_b, self.DEBUG_b = (
                self._resolve_spectrometer_driver(MEASUREMENT_SETTINGS.specto_b)
            )
        # ob irgendeine der Messungen (teilweise) synthetisch ist
        self.DEBUG = self.DEBUG_a or self.DEBUG_b

        self.MEASUREMENT_SETTINGS = MEASUREMENT_SETTINGS

        start_time = time.time()

        # für das Spektrometer und den LTb muss jeweils ziemlich lange gewartet werden
        # (bei dem Spektrometer je nach Integrationszeit, da bei der Initialisierung eine erste Messung durchgeführt wird)
        init_tasks = [
            (self.init_spectrometer, ("a",)),
            (self.init_mcu, (serial_path, 3)),
            (self.init_nkt, (nkt_path,)),
            (self.init_ltb, (ltb_path,)),
        ]
        if MEASUREMENT_SETTINGS.specto_b is not None:
            init_tasks.append((self.init_spectrometer, ("b",)))

        # ProcessPoolExecutor funktioniert nur, wenn die Funktionen/Argumente gepickelt werden können (außerhalb der Klasse definiert etc.)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(func, *args) for func, args in init_tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()

        # wird von mehreren Threads genutzt, daher lock
        self.mcu_lock = Lock()
        # bei zwei Spektrometern könnten beide gleichzeitig in die gemeinsamen settings schreiben
        self.settings_save_lock = Lock()

        # self.init_spectrometer()
        # self.init_mcu(serial_path, wait=3)
        # self.init_nkt(nkt_path)
        # self.init_ltb(ltb_path)

        self.messdata_a = SpectrumData(
            self.MEASUREMENT_SETTINGS.laser.num_gradiants,
            self.MEASUREMENT_SETTINGS.laser.REPETITIONS,
            self.get_wav("a"),
        )
        self.messdata_b = None
        if self.spectrometer_b is not None:
            self.messdata_b = SpectrumData(
                self.MEASUREMENT_SETTINGS.laser.num_gradiants,
                self.MEASUREMENT_SETTINGS.laser.REPETITIONS_B,
                self.get_wav("b"),
            )

        self.set_laser_powers(0)
        # aktuell noch keine Output-Power
        self.led_green()
        print(
            f"Finished initializing the measurement in {time.time() - start_time:.2f} seconds.",
            flush=True,
        )
        # Speicherort definieren
        measurement_type = "DEBUG" if self.DEBUG else self.MEASUREMENT_SETTINGS.TYPE

        self.measurement_save_dir = os.path.join(measurements_dir, measurement_type)
        # manche Dateisysteme unterstützen keinen Doppelpunkt im Dateinamen
        self.measurement_file_name = (
            "overwrite-messung"
            if not self.MEASUREMENT_SETTINGS.UNIQUE
            # ohne Mikrosekunden, für kürzere Dateinamen
            else datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S")
        )

        self.cam = USBCamera(
            cam_path,
            os.path.join(self.measurement_save_dir, self.measurement_file_name),
        )
        self.backup_service_a = BackupService(
            self, self.messdata_a, cache_dir, which="a"
        )
        self.backup_service_b = None
        if self.messdata_b is not None:
            self.backup_service_b = BackupService(
                self, self.messdata_b, cache_dir, which="b"
            )

    def set_laser_powers(self, index):

        max_pwm_counts_445 = (
            pow(2, self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_445[index]) - 1
        )
        max_pwm_counts_405 = (
            pow(2, self.MEASUREMENT_SETTINGS.laser.PWM_RES_BITS_405[index]) - 1
        )

        assert 0 <= self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_405[index] <= 100
        assert 0 <= self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_445[index] <= 100
        assert 0 <= self.MEASUREMENT_SETTINGS.laser.INTENSITY_NKT[index] <= 100

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
                (self.MEASUREMENT_SETTINGS.laser.PWM_DUTY_PERC_445[index] / 100.0)
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
            "ConMea", int(self.MEASUREMENT_SETTINGS.laser.CONTINUOUS)
        )

        self.set_firmware_variable(
            "ExpDel",
            (
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
                + (
                    self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
                    + self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY * 2
                    if not self.MEASUREMENT_SETTINGS.laser.CONTINUOUS
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
                    if not self.MEASUREMENT_SETTINGS.laser.CONTINUOUS
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
            max_freq * (self.MEASUREMENT_SETTINGS.laser.INTENSITY_NKT[index] / 100.0)
        )
        self.nkt.set_register("pulse_frequency", freq)
        print(f"NKT: Frequenz auf {freq} gesetzt.")
        # external trigger off (laser on on low signal)
        self.nkt.set_register("operating_mode", 5)

        # # falls er davor ausging, da [index-1] 0 war.
        # try:
        #     self.ltb.turn_laser_on()
        #     self.ltb.activate_external_trigger()
        # except LaserProtocolError as e:
        #     print(f"Could not run activate_external_trigger() again: {e} ", flush=True)
        self.ltb.set_hv_voltage(self.MEASUREMENT_SETTINGS.laser.INTENSITY_LTB[index])
        self.ltb.set_transmission(200)

        # wird jetzt auch über den mcu getriggert
        # self.ltb.set_repetition_rate(
        #     self.MEASUREMENT_SETTINGS.laser.REPETITIONS_LTB[index]
        # )

    def init_mcu(self, port, wait):
        """Verbindet sich mit dem ArduMMCUCUino."""
        try:
            # self.mcu = serial.Serial(port=port, baudrate=115200, timeout=5)
            self.mcu = serial.Serial()
            self.mcu.port = port
            self.mcu.baudrate = 115200
            self.mcu.timeout = 5
            # das Device nicht resetten, wenn es geöffnet wrid.
            self.mcu.dtr = False
            self.mcu.rts = False
            self.mcu.open()
            self.mcu.set_low_latency_mode(True)

            # auf den MCU warten
            if wait <= 1:
                print("mcu: waiting more than 1 second is recommended.")
                # 1 ist definitiv zu kurz (getestet)
            time.sleep(wait)
            self.mcu.flush()
        except serial.serialutil.SerialException as e:
            print(f"Failed to connect to the MCU: {e}")
            print("You may have to unplug and replug the MCU.")
            raise e

            from slay.virtual import MCU

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
        with self.mcu_lock:
            self.mcu.write(f"2{name}={value}\n".encode())
            time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def send_firmware_signal(self, signal):
        with self.mcu_lock:
            self.mcu.write(str(signal).encode())
            time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def turn_on_laser(self):
        """Sendet eine Eins als Byte zum MCU, welche ein Anschalten der Laser signalisiert."""
        with self.mcu_lock:
            self.mcu.write(b"1")
            time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def turn_off_laser(self):
        """Sendet eine Null als Byte zum MCU, welche ein Ausschalten der Laser signalisiert."""
        with self.mcu_lock:
            self.mcu.write(b"0")
            time.sleep(self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY / 1000.0)

    def init_spectrometer(self, which="a"):
        """Verbindet sich mit dem Spektrometer 'a' (Standard) oder 'b' (zweiter Winkel)."""

        specto = (
            self.MEASUREMENT_SETTINGS.specto
            if which == "a"
            else self.MEASUREMENT_SETTINGS.specto_b
        )
        driver = (
            self.spectrometer_driver_a if which == "a" else self.spectrometer_driver_b
        )

        print(
            f"Connecting to spectrometer {which}. Thus getting a first measurement, this might take a while....",
            flush=True,
        )
        spectrometer = driver(specto.device_index)
        spectrometer.configure(specto)

        if which == "a":
            self.spectrometer_a = spectrometer
        else:
            self.spectrometer_b = spectrometer

    def init_nkt(self, nkt_path):
        self.nkt = NKT(nkt_path)
        # erst später anschalten
        self.nkt.set_register("emission", 0)

    def init_ltb(self, ltb_path):

        self.ltb = LTB(port=ltb_path)
        print("setting LTB to stand by (should take 10 seconds until it warmed up)")
        # self.ltb.turn_laser_off()
        self.ltb.turn_laser_on()

        self.ltb_stop_event = Event()
        self.ltb_watchdog_thread = Thread(
            target=self.ltb_watchdog,
            args=(self.ltb_stop_event,),
            daemon=True,
        )
        self.ltb_watchdog_thread.start()

        # self.ltb.start_repetition_mode()
        try:
            self.ltb.activate_external_trigger()
        except LaserProtocolError as e:
            print(e)

    def get_wav(self, which="a"):
        spectrometer = self.spectrometer_a if which == "a" else self.spectrometer_b
        return spectrometer.get_wavelengths()

    def get_data(self, which="a"):
        """Liest die Daten des Spektrometers aus."""
        spectrometer = self.spectrometer_a if which == "a" else self.spectrometer_b
        return spectrometer.measure()

    def led_red(self):
        self.set_firmware_variable("SetLED", 511)

    def led_green(self):
        self.set_firmware_variable("SetLED", 151)

    def _try_stop_step(self, description, func):
        try:
            func()
        except Exception as e:
            print(f"stop_all_devices: '{description}' failed: {e}", flush=True)

    def stop_all_devices(self):

        # emission 0 gibt einen Fehler, wenn das external gate weiterhin on ist
        self._try_stop_step("turn_off_laser", self.turn_off_laser)
        self._try_stop_step("ltb.stop_operation", self.ltb.stop_operation)
        self._try_stop_step(
            "nkt emission off", lambda: self.nkt.set_register("emission", 0)
        )
        # manuelles triggern erlauben und (vorsichtshalber) die power runterstellen.
        self._try_stop_step("nkt power down", lambda: self.nkt.set_register("power", 1))
        # internal trigger
        self._try_stop_step(
            "nkt internal trigger", lambda: self.nkt.set_register("operating_mode", 0)
        )
        # Spektrometer freigeben
        self._try_stop_step("spectrometer_a.close", self.spectrometer_a.close)
        if self.spectrometer_b is not None:
            self._try_stop_step("spectrometer_b.close", self.spectrometer_b.close)
        self._try_stop_step("led_green", self.led_green)

        self._try_stop_step("ltb.close", self.ltb.close)
        self._try_stop_step("nkt.laser.close", self.nkt.laser.close)

        def close_mcu():
            with self.mcu_lock:
                self.mcu.close()

        self._try_stop_step("mcu.close", close_mcu)

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

    def time_measurement(self, measure, messdata, specto, repetitions, label=""):

        # watchdog updaten
        # self.send_firmware_signal("3")

        prefix = f"{label}: " if label else ""
        seconds = time.time()

        print(f"\n{prefix}repetitions:")
        for i in range(repetitions):
            measure(i)
            sys.stdout.write("\r")
            sys.stdout.write(f" {prefix}{i}")
            sys.stdout.flush()
            messdata.curr_measurement_index = i
            if time.time() - seconds > self.MEASUREMENT_SETTINGS.TIMEOUT:
                print(f"\n{prefix}reached timeout!")
                break

        # \r resetten
        print()
        print(f"{prefix}finished measurements")

        total_time_millis = int(round(time.time() * 1000)) - int(round(seconds * 1000))
        print(f"{prefix}measurements took: {total_time_millis} ms")
        if not self.MEASUREMENT_SETTINGS.laser.CONTINUOUS:
            delays_time = (
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY
                + 2 * self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY
                + self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME
            ) * repetitions
        else:
            delays_time = (
                self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY * repetitions
                + 2 * self.MEASUREMENT_SETTINGS.laser.SERIAL_DELAY
            )
        print(f"{prefix}thereof delays: {delays_time} ms")
        print(f"{prefix}a measurement took: {total_time_millis / 1.0 / repetitions} ms")
        print("without delays:")
        print(
            f"{prefix}a measurement took: {(total_time_millis - delays_time) / 1.0 / repetitions} ms"
        )
        print(
            f"{prefix}(should be roughly {specto.INTTIME})",
            flush=True,
        )

    def _watchdog_wait(self, stop_event, seconds):
        if stop_event is not None:
            stop_event.wait(seconds)
        else:
            time.sleep(seconds)

    def mcu_watchdog(self, stop_event=None):
        while stop_event is None or not stop_event.is_set():
            self.send_firmware_signal("3")
            self._watchdog_wait(
                stop_event,
                self.MEASUREMENT_SETTINGS.specto.INTTIME / 1000.0
                + self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0,
            )

    def ltb_watchdog(self, stop_event=None):
        """Docs: If there is no communication between the laser and the computer for more than 30 seconds, the laser will be switched into the standby mode."""
        while stop_event is None or not stop_event.is_set():
            try:
                status = self.ltb.get_version_info()
                # print(f"LTB status: {status}", flush=True)
                # if "WARNING" in status:
                #     print(status, flush=True)
            except LaserError as e:
                print(f"ltb_watchdog: {e}, retrying next cycle", flush=True)
            self._watchdog_wait(stop_event, 5)

    def continuous_measurement(
        self, spectrometer, messdata, specto, repetitions, label=""
    ):

        def measure(i):
            messdata.measurements[messdata.curr_gradiant][i] = spectrometer.measure()
            messdata.timestamps[messdata.curr_gradiant][i] = time.time()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.time_measurement(measure, messdata, specto, repetitions, label)

    def pulse_measurement(self):

        if self.mcu is None:
            print("Arduino not set up! Can not measure.")
            return

        def measure(i):
            self.turn_on_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.IRRADITION_TIME / 1000.0)
            self.messdata_a.measurements[self.messdata_a.curr_gradiant][i] = (
                self.get_data("a")
            )
            self.messdata_a.timestamps[self.messdata_a.curr_gradiant][i] = time.time()
            self.turn_off_laser()
            time.sleep(self.MEASUREMENT_SETTINGS.laser.MEASUREMENT_DELAY / 1000.0)

        self.led_red()
        # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
        self.nkt.set_register("emission", 1)
        self.time_measurement(
            measure,
            self.messdata_a,
            self.MEASUREMENT_SETTINGS.specto,
            self.MEASUREMENT_SETTINGS.laser.REPETITIONS,
        )

    def _measure_task(self):
        dual = self.spectrometer_b is not None

        for gradient in range(self.MEASUREMENT_SETTINGS.laser.num_gradiants):
            self.messdata_a.curr_gradiant = gradient
            self.messdata_a.curr_measurement_index = -1
            if dual:
                self.messdata_b.curr_gradiant = gradient
                self.messdata_b.curr_measurement_index = -1

            self.set_laser_powers(gradient)

            if self.MEASUREMENT_SETTINGS.laser.CONTINUOUS:
                self.led_red()
                # auch, wenn Emission schon an ist, wird der LASER extern vom Arduino getriggert
                # (Emission muss jedoch erst an sein, bevor der LASER extern getriggert werden kann)
                self.nkt.set_register("emission", 1)
                self.turn_on_laser()
                print("turned on lasers", flush=True)

                if dual:
                    thread_b = Thread(
                        target=self.continuous_measurement,
                        args=(
                            self.spectrometer_b,
                            self.messdata_b,
                            self.MEASUREMENT_SETTINGS.specto_b,
                            self.MEASUREMENT_SETTINGS.laser.REPETITIONS_B,
                            "B",
                        ),
                    )
                    thread_b.start()
                    self.continuous_measurement(
                        self.spectrometer_a,
                        self.messdata_a,
                        self.MEASUREMENT_SETTINGS.specto,
                        self.MEASUREMENT_SETTINGS.laser.REPETITIONS,
                        "A",
                    )
                    thread_b.join()
                else:
                    self.continuous_measurement(
                        self.spectrometer_a,
                        self.messdata_a,
                        self.MEASUREMENT_SETTINGS.specto,
                        self.MEASUREMENT_SETTINGS.laser.REPETITIONS,
                    )
            else:
                self.pulse_measurement()

        self.messdata_a.stop_event.set()
        if dual:
            self.messdata_b.stop_event.set()

    def measure(self, gui=True):

        print("staring a measurement", flush=True)

        # Use Threads instead of Processes: Thorlabs's .NET/pythonnet runtime is already loaded due to init_spectrometer, and CoreCLR
        # does not support being forked - forking here (even when not touching the spectrometer at all) corrupts method
        # binding for anything the spectrometer driver hasn't already been asked to do.
        # Thus, when later calling back to it via stop_all_devices() we would get "'MethodObject' object is not
        # callable".
        # ltb_watchdog läuft bereits seit init_ltb, da die Spektrometer teilweise eine erste Messung zur Initialisierung brauchen und der Laser dabei wieder in den Standby gehen könnte
        mcu_stop = Event()
        mcu_p = Thread(
            target=self.mcu_watchdog,
            args=(mcu_stop,),
            daemon=True,
        )

        measure_p = Thread(
            target=self._measure_task,
            daemon=True,
        )

        backup_p_a = Thread(
            target=self.backup_service_a.start,
            daemon=True,
        )
        backup_p_b = (
            Thread(target=self.backup_service_b.start, daemon=True)
            if self.backup_service_b is not None
            else None
        )
        print("made threads", flush=True)
        try:
            self.cam.start()
            print("started cam", flush=True)
            if self.MEASUREMENT_SETTINGS.UNIQUE:
                backup_p_a.start()
                if backup_p_b is not None:
                    backup_p_b.start()
            if self.MEASUREMENT_SETTINGS.laser.CONTINUOUS:
                mcu_p.start()
            print("staring a measurement process", flush=True)
            measure_p.start()

            if gui:
                # desto langsamer das Spektrometer, desto mehr Zeit wird pro Frame/Repetition benötigt
                interval = max(self.MEASUREMENT_SETTINGS.measurement_time, 300)
                if self.messdata_b is not None:
                    interval = max(
                        interval, self.MEASUREMENT_SETTINGS.measurement_time_b
                    )

                live_plotter = LivePlotter(dual=self.messdata_b is not None)
                live_plotter.start(
                    self.messdata_a.measurements.shape[0]
                    * self.messdata_a.measurements.shape[1],
                    interval,
                    self.messdata_a,
                    self.messdata_b,
                )

            measure_p.join()
        except KeyboardInterrupt:
            print("Interrupted! Shutting down.")
        finally:
            self.ltb_stop_event.set()
            mcu_stop.set()

            if self.ltb_watchdog_thread.ident is not None:
                self.ltb_watchdog_thread.join(timeout=10)
                if self.ltb_watchdog_thread.is_alive():
                    print("ltb_watchdog did not stop in time!", flush=True)
            if mcu_p.ident is not None:
                mcu_p.join(timeout=10)
                if mcu_p.is_alive():
                    print("mcu_watchdog did not stop in time!", flush=True)

            if self.cam.process.is_alive():
                self.cam.stop()

            self.stop_all_devices()

    def _save_targets(self, which=None):
        """Returned für jedes zu speichernde Spektrometer (None=alle) [Dateisuffix, messdata, Spektrometer] zum speichern"""
        dual = self.messdata_b is not None
        targets = []
        if which in (None, "a"):
            targets.append(("-a" if dual else "", self.messdata_a, "a"))
        if which in (None, "b") and dual:
            targets.append(("-b", self.messdata_b, "b"))
        return targets

    def save(
        self,
        plt_only=False,
        measurements_only=False,
        cache_path: str = "",
        # eventuell nur eines speichern: JSON settings werden so oder so geschrieben
        which=None,
    ):
        """Schreibt die Messdaten in einen spezifizierten Ordner."""
        # gemeinsame Typen werden in einem gemeinsamen Ordner gespeichert

        # impliziert, dass zum cache geschrieben werden soll
        if cache_path:
            assert not plt_only and measurements_only
            print(f"saving to cache: {cache_path}", flush=True)

        save_dir = cache_path if cache_path else self.measurement_save_dir
        os.makedirs(save_dir, 0o777, exist_ok=True)

        if not plt_only:
            # kann von den Backup-Threads beider Spektrometer gleichzeitig aufgerufen werden
            with self.settings_save_lock:
                with open(
                    os.path.join(save_dir, self.measurement_file_name + ".json"),
                    "w",
                    encoding="utf-8",
                ) as json_file:
                    self.MEASUREMENT_SETTINGS.save_as_json(json_file)

        for suffix, messdata, spectrometer in self._save_targets(which):
            file_name = self.measurement_file_name + suffix

            if not plt_only:
                np.savez_compressed(
                    os.path.join(save_dir, file_name),
                    np.array(messdata.measurements),
                    np.array(messdata.wav),
                    np.array(messdata.timestamps),
                )
                os.chmod(os.path.join(save_dir, file_name + ".npz"), 0o777)

            if not measurements_only:
                SpectrumPlot.plot_results(
                    [
                        PlotSettings(
                            os.path.join(
                                self.measurement_save_dir,
                                file_name + ".npz",
                            ),
                            True,
                            zoom_start=400,
                            zoom_end=1000,
                        )
                    ],
                    self.MEASUREMENT_SETTINGS,
                    which=spectrometer,
                    # der Plot wird ohnehin gespeichert. Bei einem jeweiligen einzelnen Aufruf würde WebAgg sonst blockieren
                    show_plots=False,
                )
