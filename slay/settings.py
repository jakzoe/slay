# prinzipiell hätte das Package "dataclasses-json" mehr Optionen
from dataclasses import dataclass, asdict, fields
import json
import ast
import numpy as np
import sys


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
        SERIAL_DELAY: int  # ms, die auf den MCU gewartet wird. Mind. 3 ms, ist sonst zu schnell für den Arduino
        INTENSITY_NKT: str  # in Prozent bis 1

        PWM_FREQ_405: str
        PWM_RES_BITS_405: str
        PWM_DUTY_PERC_405: str  # in Prozent bis 1, wird später in Counts umgerechnet

        PWM_FREQ_445: str
        PWM_RES_BITS_445: str
        PWM_DUTY_PERC_445: str
        # INTENSITY_405: str  # PWM-Signal
        # NUM_PULSES_445: str  # Pulse, die der Arduino sendet. In Clock-Zyklen.
        # PULSE_DELAY_445: str  # Pause zwischen den Pulsen

        ND_NKT: int  # ND-Wert des Filters, der dazwischen ist
        ND_405: int
        ND_445: int
        CONTINOUS: bool  # Laser durchgängig angeschaltet lassen oder nicht
        # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        INTENSITY_LTB: str = "0"
        # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
        REPETITIONS_LTB: str = "0"
        # # z. B. mit einem Blatt testen, wie weit der Fokuspunkt der Diodenlaser von der Küvette entfernt sind
        FOCUS_DIST: int = 0

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
                return list(eval(expr))  # pylint: disable=eval-used

            if (
                isinstance(node.body, ast.Call)
                and isinstance(node.body.func, ast.Attribute)
                and isinstance(node.body.func.value, ast.Name)
                and node.body.func.value.id == "np"
            ):
                # numpy array zu einer list parsen
                return eval(expr).tolist()  # pylint: disable=eval-used

            return eval(  # pylint: disable=eval-used
                compile(node, "<string>", "eval"),
                {"np": np},
            )

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
                            setattr(self, field.name, new_val)
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
    CUVETTE_WINDOWS: (
        int  # Anzahl der Fenster der verwendeten Küvette. Normalerweise zwei oder vier.
    )
    TIMEOUT: int  # Sekunden, nach denen die Messung, unabhängig von REPETITIONS, beendet werden soll
    WATCHDOG_GRACE: int  # besteht für eine bestimmte Zeit keine Kommunikation zwischen Arduino und Software: Abbruch
    specto: SpectoSettings
    laser: LaserSettings
    FILLING_QUANTITY: int = (
        0  # in alten Messungen noch nicht vorhanden gewesen, deshalb default 0
    )
    OXYGEN_SPEED: int = 0  # wie viel Luft pro Minute gepumpt wird.

    def save_as_json(self, json_file):
        json.dump(asdict(self), json_file, indent=4)

    @staticmethod
    def from_json(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as file:
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


class PlotSettings:
    """Wrapper, welcher die Einstellungen für einen Plot enthält."""

    default_min = 0
    default_max = sys.maxsize

    def __init__(
        self,
        file_path,
        code_name,
        smooth,
        grad_start=default_min,
        grad_end=default_max,
        zoom_start=default_min,
        zoom_end=default_max,
        single_wav=default_min,
        interval_start=default_min,
        interval_end=default_max,
        normalize_integrationtime=False,
        normalize_power=False,
        color=None,
        line_style="-",
        scatter=False,
        interpolate=False,
    ):
        self.file_path = file_path
        # Name des Plots beim Speichern. Der "Code" repräsentiert den Code-Namen des "Plot-Projekts"
        self.code_name = code_name
        self.smooth = smooth

        self.grad_start = grad_start
        self.grad_end = grad_end

        # Angabe: Anfang/Ende der Wellenlänge(n), die geplottet werden sollen
        # ist zoom_start + 1 == zoom_end, wird die eine Wellenlänge von zoom_start über der Zeit geplottet
        # Angabe: Wellenlänge
        self.zoom_start_wav = zoom_start
        self.zoom_end_wav = zoom_end
        # nicht default (default ist kein Zoom)
        self.zoomed = not (
            self.zoom_start_wav == self.default_min
            and self.zoom_end_wav == self.default_max
        )

        self.single_wav = single_wav
        # prinzipiell ist single_wav das gleiche wie zoom_start_wav + 1 == zoom_end_wav
        if single_wav:
            if (
                self.zoom_start_wav != self.single_wav
                or self.zoom_end_wav != self.single_wav + 1
            ) and self.zoomed:
                raise ValueError(
                    "Setting zoom and single_wav at the same time is not allowed."
                )
            self.zoom_start_wav = self.single_wav
            self.zoom_end_wav = self.single_wav + 1

        # Index (wird später umgerechnet)
        self.zoom_start = self.default_min
        self.zoom_end = self.default_max

        # nur einen Ausschnitt/Batch aus den Messungen zur Durchschnittsberechnung etc. nutzten.
        # Angabe: Sekunden
        self.interval_start_time = interval_start
        self.interval_end_time = interval_end
        self.sliced = not (
            self.interval_start_time == self.default_min
            and self.interval_end_time == self.default_max
        )

        # Index (wird später umgerechnet)
        self.interval_start = self.default_min
        self.interval_end = self.default_max

        self.normalize_integrationtime = normalize_integrationtime
        self.normalize_power = normalize_power
        self.color = color
        self.line_style = line_style
        self.scatter = scatter
        self.interpolate = interpolate

    def zoom(self) -> bool:
        """Prüft, ob das Bild ein Ausschnitt des Spektrums, welches das Spektrometer messen kann, ist."""
        return not (
            self.zoom_start == self.default_min
            and (self.zoom_end == self.default_max or self.zoom_end == 2048)
        )
