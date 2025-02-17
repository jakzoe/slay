# prinzipiell hätte das Package "dataclasses-json" mehr Optionen
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
        REPETITIONS: int  # wie häufig eine Messung wiederholt wird
        MEASUREMENT_DELAY: int  # ms, die zwischen jeder Messung gewartet werden sollen
        IRRADITION_TIME: int  # ms, die auf das Chlorophyll gestrahlt wird. Mind. 3 ms, ist sonst zu schnell für den Arduino
        ARDUINO_DELAY: int  # ms, die auf den Arduino gewartet wird. Mind. 3 ms, ist sonst zu schnell für den Arduino
        INTENSITY_NKT: float  # in Prozent
        INTENSITY_405: int  # PWM-Signal des Arduinos (0-255)
        NUM_PULSES_445: int  # Pulse, die der Arduino sendet. In Clock-Zyklen.
        PULSE_DELAY_445: int  # Pause zwischen den Pulsen
        ND_NKT: int  # ND-Wert des Filters, der dazwischen ist
        ND_405: int
        ND_445: int
        CONTINOUS: bool  # Laser durchgängig angeschaltet lassen oder nicht
        INTENSITY_LTB: int = (
            0  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        )
        REPETITIONS_LTB: int = (
            0  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        )

    UNIQUE: bool  # neue Messungen überschreiben alte Messungen, wenn sie keinen eindeutigen Namen haben
    TYPE: str  # Name der Messung
    FENSTER_KUEVETTE: (
        int  # Anzahl der Fenster der verwendeten Küvette. Normalerweise zwei oder vier.
    )
    TIMEOUT: int  # Sekunden, nach denen die Messung, unabhängig von REPETITIONS, beendet werden soll
    WATCHDOG_GRACE: int  # besteht für eine bestimmte Zeit keine Kommunikation zwischen Arduino und Software: Abbruch
    specto: SpectoSettings
    laser: LaserSettings
    FUELLL_MENGE: int = (
        0  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
    )

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
