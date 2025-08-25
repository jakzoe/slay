import os
import sys
from slay.measurement import Measurement
from slay.settings import MeasurementSettings

try:
    SERIAL_PATH = sys.argv[1]
    if "none" == SERIAL_PATH:
        raise IndexError()
except IndexError:
    SERIAL_PATH = ""
    print("Could not find the serial port connected to the MCU.")

try:
    NKT_PATH = sys.argv[2]
    if "none" == NKT_PATH:
        raise IndexError()
except IndexError:
    NKT_PATH = ""
    print("Could not find the NKT LASER.")

try:
    LTB_PATH = sys.argv[3]
    if "none" == LTB_PATH:
        raise IndexError()
except IndexError:
    LTB_PATH = ""
    print("Could not find the LTB LASER.")

try:
    CAM_PATH = sys.argv[4]
    if "none" == CAM_PATH:
        raise IndexError()
except IndexError:
    CAM_PATH = ""
    print("Could not find the camera.")

try:
    CACHE_DIR = sys.argv[5]
    if "none" == CACHE_DIR:
        raise IndexError()
except IndexError:
    CACHE_DIR = ""
    print("No cache dir given.")

if __name__ == "__main__":

    measurement_settings = MeasurementSettings(
        UNIQUE=False,
        TYPE="Chlorophyll5HalbIsopropanol",
        CUVETTE_WINDOWS=4,
        TIMEOUT=1000000,  # disable
        WATCHDOG_GRACE=200,
        FILLING_QUANTITY=5 * 800,  # in ml
        OXYGEN_SPEED=-1,  # 50 cm^3 / min
        specto=MeasurementSettings.SpectoSettings(
            # 1-498_000 ms
            INTTIME=10_000,  # 10000 # int(1000 * 60 * 0.5),
            SCAN_AVG=1,
            SMOOTH=0,
            XTIMING=3,
            AMPLIFICATION=False,
        ),
        laser=MeasurementSettings.LaserSettings(
            REPETITIONS=50,
            MEASUREMENT_DELAY=3,
            IRRADITION_TIME=3,
            SERIAL_DELAY=3,
            INTENSITY_NKT="1",  # "np.linspace(0, 100, 10)",
            PWM_FREQ_405="2000",
            PWM_RES_BITS_405="13",
            PWM_DUTY_PERC_405="0.37",  # np.linspace(0.2, 1, 5)
            #
            PWM_FREQ_445="2000",
            PWM_RES_BITS_445="13",
            PWM_DUTY_PERC_445="0.2",  # np.linspace(1, 5, 5)
            #
            REPETITIONS_LTB="55",  # range(5,55,10)
            INTENSITY_LTB="100",
            ND_NKT=0,
            ND_405=0,
            ND_445=0,
            CONTINOUS=True,
            FOCUS_DIST=0,
        ),
    )

    # measurement_settings.print_status()
    # exit()

    # müssen relative Pfade sein. Docker kann auch nur auf Pfade zugreifen, wenn sie gemountet wurden.
    measurements_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "messungen/"
    )

    # TODO: am besten bei mehreren Plots ein Json file schreiben, welches die Pfade zu den verwendeten Messungen enthält? Und Ansonsten halt common path speichern
    # TODO: Trotz Docker Messungen read-only machen?
    # plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plots/")
    measurement = Measurement(
        SERIAL_PATH,
        NKT_PATH,
        LTB_PATH,
        CAM_PATH,
        CACHE_DIR,
        measurement_settings,
        measurements_dir,
    )

    # measurement.infinite_measuring()
    # exit()

    try:
        # aktuell kann man danach keine neue Messungg starten/muss ein neues Objekt initialisieren
        measurement.measure()
        measurement.save()
    except KeyboardInterrupt as e:
        print(e)
