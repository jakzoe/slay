from MeasurementSettings import MeasurementSettings
import os
import sys
from Lasermessung import Lasermessung

try:
    ARDUINO_PATH = sys.argv[1]
    if "none" == ARDUINO_PATH:
        raise IndexError()
except IndexError:
    ARDUINO_PATH = ""
    print("could not find Arduino control unit")

try:
    NKT_PATH = sys.argv[2]
    if "none" == NKT_PATH:
        raise IndexError()
except IndexError:
    NKT_PATH = ""
    print("could not find NKT LASER")

try:
    LTB_PATH = sys.argv[3]
    if "none" == LTB_PATH:
        raise IndexError()
except IndexError:
    LTB_PATH = ""
    print("could not find LTB LASER")


if __name__ == "__main__":

    measurement_settings = MeasurementSettings(
        UNIQUE=True,
        TYPE="Chloro_Jufo",  # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Neutral_Mit_Spiegel # Mittel_Bier_Indirekt # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Radieschen_Direkt_Unfokussiert # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Nur_Bodensatz_Also_Toll
        FENSTER_KUEVETTE=2,
        TIMEOUT=1000000,  # disable
        WATCHDOG_GRACE=200,
        FUELLL_MENGE=3,  # in ml
        OXYGEN_SPEED=50,  # cm^3 / min
        specto=MeasurementSettings.SpectoSettings(
            INTTIME=10000,  # int(1000 * 60 * 0.5),
            SCAN_AVG=1,
            SMOOTH=0,
            XTIMING=3,
            AMPLIFICATION=False,
        ),
        laser=MeasurementSettings.LaserSettings(
            REPETITIONS=100,
            MEASUREMENT_DELAY=3,
            IRRADITION_TIME=3,
            ARDUINO_DELAY=3,
            INTENSITY_NKT="0",  # "np.linspace(0, 1, 10)",  # in Prozent von 0 bis 1 #
            INTENSITY_405="255",  # kaum noch sichtbar unter 60
            NUM_PULSES_445="200",  # range(0, 200, 20) # 1234 heißt kein PWM
            PULSE_DELAY_445="1",
            REPETITIONS_LTB="0",
            INTENSITY_LTB="0",
            ND_NKT=0,
            ND_405=0,
            ND_445=0,
            CONTINOUS=True,
            FOCUS_DIST=0,
        ),
    )
    # TODO: alle paar Sekunden Messergebnisse zwischenspeichern (Daten von einem separaten Process kopieren und speichern)

    measurement_settings.print_status()
    # exit()
    measurement = Lasermessung(ARDUINO_PATH, NKT_PATH, LTB_PATH, measurement_settings)

    # measurement.infinite_measuring()
    # exit()

    measurement.measure()
    DIR_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "messungen/"
    )
    measurement.save(DIR_PATH)
