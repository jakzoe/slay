# from typing import Any, Dict


class MeasurementSettings:
    class SpectoSettings:
        def __init__(self, INTTIME: int, SCAN_AVG: int, SMOOTH: int, XTIMING: int):
            self.INTTIME = INTTIME
            self.SCAN_AVG = SCAN_AVG
            self.SMOOTH = SMOOTH
            self.XTIMING = XTIMING

    class LaserSettings:

        def __init__(
            self,
            REPETITIONS: int,
            MEASUREMENT_DELAY: int,
            IRRADITION_TIME: int,
            ARDUINO_DELAY: int,
            INTENSITY_NKT: float,
            INTENSITY_405: int,
            NUM_PULSES_445: int,
            PULSE_DELAY_445: int,
            ND_NKT: int,
            ND_405: int,
            ND_445: int,
            CONTINOUS: bool,
        ):
            self.REPETITIONS = REPETITIONS
            self.MEASUREMENT_DELAY = MEASUREMENT_DELAY
            self.IRRADITION_TIME = IRRADITION_TIME
            self.ARDUINO_DELAY = ARDUINO_DELAY
            self.INTENSITY_NKT = INTENSITY_NKT
            self.INTENSITY_405 = INTENSITY_405
            self.NUM_PULSES_445 = NUM_PULSES_445
            self.PULSE_DELAY_445 = PULSE_DELAY_445

            self.ND_NKT = ND_NKT
            self.ND_405 = ND_405
            self.ND_445 = ND_445
            self.CONTINOUS = CONTINOUS

    def __init__(
        self,
        UNIQUE: bool,
        TYPE: str,
        FENSTER_KUEVETTE: int,
        TIMEOUT: int,
        WATCHDOG_GRACE: int,
        FUELLL_MENGE: int,
        specto: SpectoSettings,  # Dict[str, Any],
        laser: LaserSettings,  # Dict[str, Any],
    ):
        self.UNIQUE = UNIQUE
        self.TYPE = TYPE
        self.FENSTER_KUEVETTE = FENSTER_KUEVETTE
        self.TIMEOUT = TIMEOUT
        self.WATCHDOG_GRACE = WATCHDOG_GRACE
        self.FUELLL_MENGE = FUELLL_MENGE
        self.specto = specto  # self.SpectoSettings(**specto)
        self.laser = laser  # self.LaserSettings(**laser)

    def save_as_json(self, json_file):
        import json

        def to_dict(obj):
            if hasattr(obj, "__dict__"):
                return {k: to_dict(v) for k, v in obj.__dict__.items()}
            else:
                return obj

        json.dump(to_dict(self), json_file, indent=4)

    @staticmethod
    def from_json(json_file_path):
        def from_dict(cls, dict_data):
            if cls == MeasurementSettings.SpectoSettings:
                return cls(
                    INTTIME=dict_data["INTTIME"],
                    SCAN_AVG=dict_data["SCAN_AVG"],
                    SMOOTH=dict_data["SMOOTH"],
                    XTIMING=dict_data["XTIMING"],
                )
            elif cls == MeasurementSettings.LaserSettings:
                return cls(
                    REPETITIONS=dict_data["REPETITIONS"],
                    MEASUREMENT_DELAY=dict_data["MEASUREMENT_DELAY"],
                    IRRADITION_TIME=dict_data["IRRADITION_TIME"],
                    ARDUINO_DELAY=dict_data["ARDUINO_DELAY"],
                    INTENSITY_NKT=dict_data["INTENSITY_NKT"],
                    INTENSITY_405=dict_data["INTENSITY_405"],
                    NUM_PULSES_445=dict_data["NUM_PULSES_445"],
                    PULSE_DELAY_445=dict_data["PULSE_DELAY_445"],
                    ND_NKT=dict_data["ND_NKT"],
                    ND_405=dict_data["ND_405"],
                    ND_445=dict_data["ND_445"],
                    CONTINOUS=dict_data["CONTINOUS"],
                )
            elif cls == MeasurementSettings:
                specto_obj = from_dict(
                    MeasurementSettings.SpectoSettings, dict_data["specto"]
                )
                laser_obj = from_dict(
                    MeasurementSettings.LaserSettings, dict_data["laser"]
                )
                return cls(
                    UNIQUE=dict_data["UNIQUE"],
                    TYPE=dict_data["TYPE"],
                    FENSTER_KUEVETTE=dict_data["FENSTER_KUEVETTE"],
                    TIMEOUT=dict_data["TIMEOUT"],
                    WATCHDOG_GRACE=dict_data["WATCHDOG_GRACE"],
                    FUELLL_MENGE=dict_data.get("FUELLL_MENGE", 0),
                    specto=specto_obj,
                    laser=laser_obj,
                )

        import json

        with open(json_file_path, "r") as file:
            data = json.load(file)
            return from_dict(MeasurementSettings, data)


# def create_object_from_json(json_data, class_map):
#     # Check if the json_data is a dictionary and matches a known class
#     if isinstance(json_data, dict):
#         class_name = json_data.get("class_name")
#         if class_name in class_map:
#             # Instantiate the corresponding class
#             class_obj = class_map[class_name]
#             return class_obj(
#                 **{
#                     key: create_object_from_json(value, class_map)
#                     for key, value in json_data.items()
#                     if key != "class_name"  # Exclude the class_name field
#                 }
#             )
#         # Process as a generic dictionary if not mapped to a class
#         return {
#             key: create_object_from_json(value, class_map)
#             for key, value in json_data.items()
#         }
#     elif isinstance(json_data, list):
#         # Process lists recursively
#         return [create_object_from_json(item, class_map) for item in json_data]
#     else:
#         # Return primitive values directly
#         return json_data


# def object_from_json(path) -> MeasurementSettings:
#     import json

#     with open(path, "r", encoding="utf-8") as file:
#         json_data = json.load(file)

#     class_map = {
#         "SpectoSettings": MeasurementSettings.SpectoSettings,
#         "LaserSettings": MeasurementSettings.LaserSettings,
#         "MeasurementSettings": MeasurementSettings,
#     }

#     # Explicitly instantiate the root object as MeasurementSettings
#     return create_object_from_json(json_data, class_map)


# from collections import namedtuple
# import json

# SpectoSettings = namedtuple(
#     "SpectoSettings", ["INTTIME", "SCAN_AVG", "SMOOTH", "XTIMING"]
# )
# LaserSettings = namedtuple(
#     "LaserSettings",
#     [
#         "REPETITIONS",
#         "MEASUREMENT_DELAY",
#         "IRRADITION_TIME",
#         "ARDUINO_DELAY",
#         "INTENSITY",
#         "CONTINOUS",
#         "GRAUFILTER",
#         "TIMEOUT",
#     ],
# )
# MeasurementSettings = namedtuple(
#     "MeasurementSettings", ["UNIQUE", "TYPE", "specto", "laser"]
# )


# def namedtuple_to_dict(namedtuple_instance):
#     if hasattr(namedtuple_instance, "_asdict"):
#         return {
#             k: namedtuple_to_dict(v) if hasattr(v, "_asdict") else v
#             for k, v in namedtuple_instance._asdict().items()
#         }
#     return namedtuple_instance


# def save_measurement_settings(measurement_dict, path="measurement_settings.json"):
#     if not isinstance(measurement_dict, dict):
#         measurement_dict = namedtuple_to_dict(measurement_dict)
#     with open(path, "w") as json_file:
#         json.dump(measurement_dict, json_file, indent=4)


# def load_measurement_settings(path="measurement_settings.json"):
#     with open(path, "r") as json_file:
#         return json.load(json_file)


# def dict_to_namedtuple(d, namedtuple_class):
#     fields = namedtuple_class._fields
#     kwargs = {}
#     for field in fields:
#         value = d[field]
#         if isinstance(value, dict):
#             nested_class = SpectoSettings if field == "specto" else LaserSettings
#             kwargs[field] = dict_to_namedtuple(value, nested_class)
#         else:
#             kwargs[field] = value
#     return namedtuple_class(**kwargs)


# measurement_settings_loaded = dict_to_namedtuple(
#     load_measurement_settings(), MeasurementSettings
# )

# assert measurement_settings_loaded == measurement_settings

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
