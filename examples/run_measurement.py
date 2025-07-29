from slay.settings import MeasurementSettings
import os
import sys
from slay.measurement import Measurement

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

if __name__ == "__main__":

    measurement_settings = MeasurementSettings(
        UNIQUE=False,
        TYPE="Chloro_Jufo",  # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Neutral_Mit_Spiegel # Mittel_Bier_Indirekt # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Radieschen_Direkt_Unfokussiert # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Nur_Bodensatz_Also_Toll
        CUVETTE_WINDOWS=2,
        TIMEOUT=1000000,  # disable
        WATCHDOG_GRACE=200,
        FILLING_QUANTITY=3,  # in ml
        OXYGEN_SPEED=50,  # cm^3 / min
        specto=MeasurementSettings.SpectoSettings(
            INTTIME=10_000,  # 10000 # int(1000 * 60 * 0.5),
            SCAN_AVG=1,
            SMOOTH=0,
            XTIMING=3,
            AMPLIFICATION=False,
        ),
        laser=MeasurementSettings.LaserSettings(
            REPETITIONS=30,
            MEASUREMENT_DELAY=3,
            IRRADITION_TIME=3,
            SERIAL_DELAY=3,
            INTENSITY_NKT="0",  # "np.linspace(0, 1, 10)",  # in Prozent von 0 bis 1 #
            # INTENSITY_405="255",  # kaum noch sichtbar unter 60
            # NUM_PULSES_445="200",  # range(0, 200, 20) # 1234 heißt kein PWM
            # PULSE_DELAY_445="100",
            PWM_FREQ_405="2000",
            PWM_RES_BITS_405="13",
            PWM_DUTY_PERC_405="0.0035",  # np.linspace(0.2, 1, 5)
            #
            PWM_FREQ_445="2000",
            PWM_RES_BITS_445="13",
            PWM_DUTY_PERC_445="0.0037",  # np.linspace(0.2, 1, 5)
            #
            REPETITIONS_LTB="5",  # range(5,55,10)
            INTENSITY_LTB="8",
            ND_NKT=0,
            ND_405=0,
            ND_445=0,
            CONTINOUS=True,
            FOCUS_DIST=0,
        ),
    )
    # TODO: alle paar Sekunden Messergebnisse zwischenspeichern (Daten von einem separaten Process kopieren und speichern)

    # measurement_settings.print_status()
    # exit()
    dir_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "messungen/"
    )
    measurement = Measurement(
        SERIAL_PATH, NKT_PATH, LTB_PATH, CAM_PATH, measurement_settings, dir_path
    )

    # measurement.infinite_measuring()
    # exit()

    try:
        # aktuell kann man danach keine neue Messungg starten/muss ein neues Objekt initialisieren
        measurement.measure()
        measurement.save()
    except KeyboardInterrupt as e:
        print(e)
