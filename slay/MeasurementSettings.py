# prinzipiell häte "dataclasses-json" mehr Optionen
from dataclasses import dataclass, asdict
import json


@dataclass
class MeasurementSettings:
    @dataclass
    class SpectoSettings:
        INTTIME: int
        SCAN_AVG: int
        SMOOTH: int
        XTIMING: int

    @dataclass
    class LaserSettings:
        REPETITIONS: int
        MEASUREMENT_DELAY: int
        IRRADITION_TIME: int
        ARDUINO_DELAY: int
        INTENSITY_NKT: float
        INTENSITY_405: int
        NUM_PULSES_445: int
        PULSE_DELAY_445: int
        ND_NKT: int
        ND_405: int
        ND_445: int
        CONTINOUS: bool

    UNIQUE: bool
    TYPE: str
    FENSTER_KUEVETTE: int
    TIMEOUT: int
    WATCHDOG_GRACE: int
    specto: SpectoSettings
    laser: LaserSettings
    FUELLL_MENGE: int = 0  # in alten Messungen noch nicht vorhanden gewesen

    def save_as_json(self, json_file):
        json.dump(asdict(self), json_file, indent=4)

    @staticmethod
    def from_json(json_file_path):
        with open(json_file_path, "r") as file:
            data = json.load(file)

        def from_dict(cls, dict_data):
            if cls == MeasurementSettings:
                return cls(
                    specto=from_dict(
                        MeasurementSettings.SpectoSettings, dict_data.pop("specto")
                    ),
                    laser=from_dict(
                        MeasurementSettings.LaserSettings, dict_data.pop("laser")
                    ),
                    **dict_data
                )
            return cls(**dict_data)

        return from_dict(MeasurementSettings, data)


# MEASUREMENT_SETTINGS = {
#     "UNIQUE": True,  # neue Messungen überschreiben alte Messungen, wenn sie keinen eindeutigen Namen haben
#     "TYPE": "Bier",  # Chlorophyll, Kresse
#     # "ANAEROB": False,
#     "specto": {
#         "INTTIME": 2,  # int(1_000 * 60 * 1 / 2)  # 1-498000 ms
#         "SCAN_AVG": 1,  # > 1
#         "SMOOTH": 0,  # 1-4
#         "XTIMING": 3,  # 1-3
#     },
#     ## ACHTUNG: DELAY und IRRADITION_TIME sollten MINDESTENS 3 ms, sein, der Arduino schafft es nicht in kürzerer Zeit, alles anzustellen
#     "laser": {
#         "REPETITIONS": 100,  # wie häufig eine Messung wiederholt wird
#         "MEASUREMENT_DELAY": 3,  # Zeit in ms, die zwischen jeder Messung gewartet werden soll
#         "IRRADITION_TIME": 3,  # Zeit in ms, die auf das Chlorophyll gestrahlt wird
#         "ARDUINO_DELAY": 3,  # Zeit in ms, die auf den Arduino gewartet wird
#         "INTENSITY": 100,  # wie stark der Laser eingestellt ist (z. B. Frequenz oder Spannung, je nach Lasertyp)
#         "CONTINOUS": True,  # Laser durchgängig angeschaltet lassen oder nicht
#         "GRAUFILTER": False,  # ob ein Graufilter dazwischen ist oder nicht
#         "TIMEOUT": 4600,  # Sekunden, nach denen die Messung, unabhängig von REPETITIONS, beendet werden soll
#     },
#     # "indices": {
#     #     "INTTIME_INDEX": 0,
#     #     "INTENSITY_INDEX": 1,
#     #     "SCAN_AVG_INDEX": 2,
#     #     "SMOOTH_INDEX": 3,
#     #     "XTIMING_INDEX": 4,
#     #     "REPETITIONS_INDEX": 5,
#     #     "ARDUINO_DELAY_INDEX": 6,
#     #     "IRRADITION_TIME_INDEX": 7,
#     #     "CONTINOUS_INDEX": 8,
#     # },
# }
