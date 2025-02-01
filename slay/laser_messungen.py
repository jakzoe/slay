from MeasurementSettings import MeasurementSettings
import os
import sys
from Lasermessung import Lasermessung

try:
    ARDUINO_PATH = sys.argv[1]
except IndexError:
    ARDUINO_PATH = ""
    print("could not find Arduino control unit")

try:
    NKT_PATH = sys.argv[2]
except IndexError:
    NKT_PATH = ""
    print("could not find NKT LASER")

if __name__ == "__main__":

    measurement_settings = MeasurementSettings(
        UNIQUE=False,
        TYPE="Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Nur_Bodensatz_Also_Toll",  # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Neutral_Mit_Spiegel # Mittel_Bier_Indirekt # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Blub # Radieschen_Direkt_Unfokussiert # Chlorophyll_Ohne_Amp_Rhombus_Unfokussiert_Nur_Bodensatz_Also_Toll
        FENSTER_KUEVETTE=2,
        TIMEOUT=1000000,  # disable
        WATCHDOG_GRACE=200,
        FUELLL_MENGE=0.810,  # in ml
        specto=MeasurementSettings.SpectoSettings(
            INTTIME=10,  # int(1000 * 60 * 0.5),
            SCAN_AVG=1,
            SMOOTH=0,
            XTIMING=3,  # int(1000 * 60 * 0.3)
        ),
        laser=MeasurementSettings.LaserSettings(
            REPETITIONS=25000,
            MEASUREMENT_DELAY=3,
            IRRADITION_TIME=3,
            ARDUINO_DELAY=3,
            INTENSITY_NKT=1,  # in Prozent
            INTENSITY_405=0,  # kaum noch sichtbar unter 60
            NUM_PULSES_445=50,  # 1234 ist kein PWM
            PULSE_DELAY_445=10,
            ND_NKT=0,
            ND_405=0,
            ND_445=0,
            CONTINOUS=True,
        ),
    )

    measurement = Lasermessung(ARDUINO_PATH, NKT_PATH, measurement_settings)

    # measurement.infinite_measuring()
    # exit()

    measurement.measure()
    DIR_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "messungen/"
    )
    measurement.save(DIR_PATH)
