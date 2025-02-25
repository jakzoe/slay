import sys


class PlottingSettings:
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
