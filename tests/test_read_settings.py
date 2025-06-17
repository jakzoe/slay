import unittest
import json
from tempfile import NamedTemporaryFile
from slay.settings import MeasurementSettings


class TestReadSettings(unittest.TestCase):

    def setUp(self):
        # neues Format und neue Namen, muss ich noch zu Ende ändern
        assert False
        self.settings = MeasurementSettings(
            UNIQUE=True,
            TYPE="Test",
            CUVETTE_WINDOWS=1,
            TIMEOUT=10,
            WATCHDOG_GRACE=5,
            specto=MeasurementSettings.SpectoSettings(
                INTTIME=100, SCAN_AVG=10, SMOOTH=2, XTIMING=20
            ),
            laser=MeasurementSettings.LaserSettings(
                REPETITIONS=5,
                MEASUREMENT_DELAY=100,
                IRRADITION_TIME=200,
                SERIAL_DELAY=50,
                INTENSITY_NKT=1.5,
                PWM_FREQ_405=2000,
                PWM_RES_BITS_405=13,
                PWM_DUTY_PERC_405=42,
                PWM_FREQ_445=2000,
                PWM_RES_BITS_445=13,
                PWM_DUTY_PERC_445=42,
                ND_NKT=0,
                ND_405=1,
                ND_445=2,
                CONTINOUS=False,
            ),
            FILLING_QUANTITY=0,
        )

        self.settings_as_json = {
            "UNIQUE": True,
            "TYPE": "Test",
            "FENSTER_KUEVETTE": 1,
            "TIMEOUT": 10,
            "WATCHDOG_GRACE": 5,
            "specto": {"INTTIME": 100, "SCAN_AVG": 10, "SMOOTH": 2, "XTIMING": 20},
            "laser": {
                "REPETITIONS": 5,
                "MEASUREMENT_DELAY": 100,
                "IRRADITION_TIME": 200,
                "ARDUINO_DELAY": 50,
                "INTENSITY_NKT": 1.5,
                "INTENSITY_405": 3,
                "NUM_PULSES_445": 7,
                "PULSE_DELAY_445": 25,
                "ND_NKT": 0,
                "ND_405": 1,
                "ND_445": 2,
                "CONTINOUS": False,
            },
            "FILLING_QUANTITY": 0,
        }

    def test_save_as_json(self):
        with NamedTemporaryFile(delete=False, mode="w") as temp_file:
            self.settings.save_as_json(temp_file)
            temp_file_path = temp_file.name

        with open(temp_file_path, "r", encoding="utf-8") as file:
            loaded_data = json.load(file)

        self.assertEqual(loaded_data, self.settings_as_json)

    def test_from_json(self):

        with NamedTemporaryFile(delete=False, mode="w") as temp_file:
            json.dump(self.settings_as_json, temp_file)
            temp_file_path = temp_file.name

        loaded_settings = MeasurementSettings.from_json(temp_file_path)

        self.assertEqual(loaded_settings, self.settings)

    def test_from_json_with_missing(self):
        json_data_with_removed = self.settings_as_json.copy()
        json_data_with_removed.pop("FILLING_QUANTITY")

        with NamedTemporaryFile(delete=False, mode="w") as temp_file:
            json.dump(json_data_with_removed, temp_file)
            temp_file_path = temp_file.name

        loaded_settings = MeasurementSettings.from_json(temp_file_path)

        self.assertEqual(loaded_settings, self.settings)


if __name__ == "__main__":
    unittest.main()
