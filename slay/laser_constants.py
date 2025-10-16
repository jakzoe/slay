MEASUREMENT_SETTINGS = {
    "UNIQUE": True,  # neue Messungen überschreiben alte Messungen, wenn sie keinen eindeutigen Namen haben
    "TYPE": "Bier",  # Chlorophyll, Kresse
    # "ANAEROB": False,
    "specto": {
        "INTTIME": 2,  # int(1_000 * 60 * 1 / 2)  # 1-498000 ms
        "SCAN_AVG": 1,  # > 1
        "SMOOTH": 0,  # 1-4
        "XTIMING": 3,  # 1-3
    },
    ## ACHTUNG: DELAY und IRRADITION_TIME sollten MINDESTENS 3 ms, sein, der Arduino schafft es nicht in kürzerer Zeit, alles anzustellen
    "laser": {
        "REPETITIONS": 100,  # wie häufig eine Messung wiederholt wird
        "MEASUREMENT_DELAY": 3,  # Zeit in ms, die zwischen jeder Messung gewartet werden soll
        "IRRADITION_TIME": 3,  # Zeit in ms, die auf das Chlorophyll gestrahlt wird
        "ARDUINO_DELAY": 3,  # Zeit in ms, die auf den Arduino gewartet wird
        "INTENSITY": 100,  # wie stark der Laser eingestellt ist (z. B. Frequenz oder Spannung, je nach Lasertyp)
        "CONTINOUS": True,  # Laser durchgängig angeschaltet lassen oder nicht
        "GRAUFILTER": False,  # ob ein Graufilter dazwischen ist oder nicht
        "TIMEOUT": 4600,  # Sekunden, nach denen die Messung, unabhängig von REPETITIONS, beendet werden soll
    },
    # "indices": {
    #     "INTTIME_INDEX": 0,
    #     "INTENSITY_INDEX": 1,
    #     "SCAN_AVG_INDEX": 2,
    #     "SMOOTH_INDEX": 3,
    #     "XTIMING_INDEX": 4,
    #     "REPETITIONS_INDEX": 5,
    #     "ARDUINO_DELAY_INDEX": 6,
    #     "IRRADITION_TIME_INDEX": 7,
    #     "CONTINOUS_INDEX": 8,
    # },
}

if MEASUREMENT_SETTINGS["laser"]["GRAUFILTER"]:
    MEASUREMENT_SETTINGS["diagramm"]["NAME"] += " mit Graufilter"

# MEASUREMENT_SETTINGS["NAME"] += (
#     " mit " + str(MEASUREMENT_SETTINGS["laser"]["INTENSITY"]) + " %"
# )


def named_tuple_test():

    from collections import namedtuple
    import json

    # Define the nested named tuples
    SpectoSettings = namedtuple(
        "SpectoSettings", ["INTTIME", "SCAN_AVG", "SMOOTH", "XTIMING"]
    )
    LaserSettings = namedtuple(
        "LaserSettings",
        [
            "REPETITIONS",
            "MEASUREMENT_DELAY",
            "IRRADITION_TIME",
            "ARDUINO_DELAY",
            "INTENSITY",
            "CONTINOUS",
            "GRAUFILTER",
            "TIMEOUT",
        ],
    )
    MeasurementSettings = namedtuple(
        "MeasurementSettings", ["UNIQUE", "TYPE", "specto", "laser"]
    )

    # Create the named tuple instances
    specto_settings = SpectoSettings(INTTIME=2, SCAN_AVG=1, SMOOTH=0, XTIMING=3)
    laser_settings = LaserSettings(
        REPETITIONS=100,
        MEASUREMENT_DELAY=3,
        IRRADITION_TIME=3,
        ARDUINO_DELAY=3,
        INTENSITY=100,
        CONTINOUS=True,
        GRAUFILTER=False,
        TIMEOUT=4600,
    )
    measurement_settings = MeasurementSettings(
        UNIQUE=True, TYPE="Bier", specto=specto_settings, laser=laser_settings
    )

    print(measurement_settings.specto.INTTIME)
    print(measurement_settings.laser.REPETITIONS)

    # Convert named tuple to dictionary
    def namedtuple_to_dict(namedtuple_instance):
        if hasattr(namedtuple_instance, "_asdict"):
            return {
                k: namedtuple_to_dict(v) if hasattr(v, "_asdict") else v
                for k, v in namedtuple_instance._asdict().items()
            }
        return namedtuple_instance

    measurement_dict = namedtuple_to_dict(measurement_settings)
    print(measurement_dict)

    with open("measurement_settings.json", "w") as json_file:
        json.dump(measurement_dict, json_file, indent=4)

    with open("measurement_settings.json", "r") as json_file:
        measurement_dict_loaded = json.load(json_file)

    def dict_to_namedtuple(d, namedtuple_class):
        fields = namedtuple_class._fields
        kwargs = {}
        for field in fields:
            value = d[field]
            if isinstance(value, dict):
                nested_class = SpectoSettings if field == "specto" else LaserSettings
                kwargs[field] = dict_to_namedtuple(value, nested_class)
            else:
                kwargs[field] = value
        return namedtuple_class(**kwargs)

    measurement_settings_loaded = dict_to_namedtuple(
        measurement_dict_loaded, MeasurementSettings
    )

    assert measurement_settings_loaded == measurement_settings

    print(measurement_settings_loaded.specto.INTTIME)
    print(measurement_settings_loaded.laser.REPETITIONS)


named_tuple_test()
