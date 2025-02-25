# prinzipiell hätte das Package "dataclasses-json" mehr Optionen
from dataclasses import dataclass, asdict, fields
import json
import ast
import numpy as np


@dataclass
class MeasurementSettings:
    @dataclass
    class SpectoSettings:
        INTTIME: int
        SCAN_AVG: int
        SMOOTH: int
        XTIMING: int
        AMPLIFICATION: bool = False

    @dataclass
    class LaserSettings:
        REPETITIONS: int  # wie häufig eine Messung wiederholt wird
        MEASUREMENT_DELAY: int  # ms, die zwischen jeder Messung gewartet werden sollen
        IRRADITION_TIME: int  # ms, die auf das Chlorophyll gestrahlt wird. Mind. 3 ms, ist sonst zu schnell für den Arduino
        ARDUINO_DELAY: int  # ms, die auf den Arduino gewartet wird. Mind. 3 ms, ist sonst zu schnell für den Arduino
        INTENSITY_NKT: str  # in Prozent
        INTENSITY_405: str  # PWM-Signal des Arduinos (0-255)
        NUM_PULSES_445: str  # Pulse, die der Arduino sendet. In Clock-Zyklen.
        PULSE_DELAY_445: str  # Pause zwischen den Pulsen
        ND_NKT: int  # ND-Wert des Filters, der dazwischen ist
        ND_405: int
        ND_445: int
        CONTINOUS: bool  # Laser durchgängig angeschaltet lassen oder nicht
        INTENSITY_LTB: str = (
            "0"  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        )
        REPETITIONS_LTB: str = (
            "0"  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        )

        def __post_init__(self):
            self.convert_string_values()

        def restricted_eval(self, expr):
            allowed_funcs = {"range", "linspace"}
            allowed_ops = {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow}

            assert expr != ""
            node = ast.parse(expr, mode="eval")

            def validate(n):
                if isinstance(n, ast.Expression):
                    return validate(n.body)  # Root node
                elif isinstance(n, ast.BinOp):
                    if type(n.op) not in allowed_ops:
                        raise ValueError(f"Disallowed operator: {type(n.op).__name__}")
                    if not isinstance(
                        n.left, (ast.Constant, ast.BinOp)
                    ) or not isinstance(n.right, (ast.Constant, ast.BinOp)):
                        raise ValueError(
                            "Only constant values and valid operations are allowed."
                        )
                    return validate(n.left) and validate(n.right)
                elif isinstance(n, ast.UnaryOp):
                    return isinstance(n.op, (ast.UAdd, ast.USub)) and isinstance(
                        n.operand, ast.Constant
                    )
                elif isinstance(n, ast.Constant):
                    if not isinstance(n.value, (int, float)):
                        raise ValueError("Only numeric constants are allowed.")
                    return True
                elif isinstance(n, ast.Call):
                    if (
                        (
                            isinstance(n.func, ast.Name)
                            and hasattr(n.func, "id")
                            and n.func.id in allowed_funcs
                        )
                        or isinstance(n.func, ast.Attribute)
                        and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "np"
                        and n.func.attr in allowed_funcs
                    ):
                        for arg in n.args:
                            if not isinstance(arg, ast.Constant) or not isinstance(
                                arg.value, (int, float)
                            ):
                                raise ValueError(
                                    "Arguments to functions are set to be integers or floats."
                                )
                        return True
                    else:
                        raise ValueError(
                            f"Only the following functions are allowed: {allowed_funcs}"
                        )
                else:
                    raise ValueError(f"Disallowed expression type: {type(n).__name__}")

            validate(node.body)

            if (
                isinstance(node.body, ast.Call)
                and isinstance(node.body.func, ast.Name)
                and node.body.func.id == "range"
            ):
                # range zu einer list parsen
                return list(eval(expr))

            if (
                isinstance(node.body, ast.Call)
                and isinstance(node.body.func, ast.Attribute)
                and isinstance(node.body.func.value, ast.Name)
                and node.body.func.value.id == "np"
            ):
                # numpy array zu einer list parsen
                return eval(expr).tolist()

            return eval(compile(node, "<string>", "eval"), {"np": np})

        def convert_string_values(self):

            no_list_fields = []
            max_len = 1

            for field in fields(self):
                if field.type == str:
                    value = getattr(self, field.name)
                    if isinstance(value, str):
                        try:
                            new_val = self.restricted_eval(value)
                            try:
                                if max_len == 1:
                                    max_len = len(new_val)
                                else:
                                    if max_len != len(new_val):
                                        raise ValueError(
                                            f"The number of values per parameter should be equal for all parameters (error on {new_val})."
                                        )
                            except TypeError:
                                no_list_fields.append(field)
                            setattr(self, field.name, new_val)  # Store evaluated value
                        except ValueError as e:
                            raise ValueError(
                                f"Invalid value for {field.name}: {value} ({e})"
                            ) from e
                    elif isinstance(value, list):
                        if max_len == 1:
                            max_len = len(getattr(self, field.name))
                        else:
                            if max_len != len(getattr(self, field.name)):
                                raise ValueError(
                                    f"The number of values per parameter should be equal for all parameters (error on {field.name})."
                                )

            # um nicht jedes Mal prüfen zu müssen, ob es sich um einen einzelnen Wert oder eine Liste handelt, alle Parameter zu Listen machen, falls Listen genutzt werden (Gradient-Measurement)
            for field in no_list_fields:
                setattr(self, field.name, [getattr(self, field.name)] * max_len)

            self.num_gradiants = max_len

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
                    **dict_data,
                )
            return cls(**dict_data)

        return from_dict(MeasurementSettings, data)

    def print_status(self):
        print("running with the following settings:")

        def print_fields(obj):
            for field in obj.__dict__:
                value = obj.__dict__[field]
                print(f"{field}: {type(value).__name__} = {value}")

        print_fields(self)
        print_fields(self.specto)
        print_fields(self.laser)
