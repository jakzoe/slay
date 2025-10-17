import sys


class PlottingSettings:
    """Wrapper, welcher die Einstellungen für einen Plot enthält."""

    def __init__(
        self,
        file_path,
        code_name,
        smooth,
        zoom_start=0,
        zoom_end=sys.maxsize,
        interval_start=0,
        interval_end=sys.maxsize,
        normalize_integrationtime=False,
        normalize_power=False,
        color=None,
        line_style="-",
        scatter=False,
        # focus_wavelength=None,  # zeigt die Stärke der Wellenlänge über die Zeit an. Zoom wird damit ignoriert.
    ):
        self.file_path = file_path
        # Name des Plots beim Speichern. Der "Code" repräsentiert den Code-Namen des "Plot-Projekts"
        self.code_name = code_name
        self.smooth = smooth

        # Angabe: Anfang/Ende der Wellenlänge(n), die geplottet werden sollen
        # ist zoom_start + 1 == zoom_end, wird die eine Wellenlänge von zoom_start über der Zeit geplottet
        # Angabe: Wellenlänge
        self.zoom_start_wav = zoom_start
        self.zoom_end_wav = zoom_end

        self.zoom_start = 0
        self.zoom_end = sys.maxsize

        # nur einen Ausschnitt/Batch aus den Messungen zur Durchschnittsberechnung etc. nutzten.
        # Angabe: Sekunden
        self.interval_start_time = interval_start
        self.interval_end_time = interval_end
        self.sliced = not (
            self.interval_start_time == 0 and self.interval_end_time == sys.maxsize
        )

        # Index (wird später umgerechnet)
        self.interval_start = 0
        self.interval_end = sys.maxsize

        self.normalize_integrationtime = normalize_integrationtime
        self.normalize_power = normalize_power
        self.color = color
        self.line_style = line_style
        self.scatter = scatter
        # self.focus_wavelength = focus_wavelength

    # doof, weil interval_end später auf die Länge des Arrays gesetzt wird
    # def sliced(self) -> bool:
    #     """Prüft, ob das Bild ein Ausschnitt einer Messreihe ist."""
    #     return not (self.interval_start == 0 and self.interval_end == sys.maxsize)

    def zoom(self) -> bool:
        """Prüft, ob das Bild ein Ausschnitt des Spektrums, welches das Spektrometer messen kann, ist."""
        return not (
            self.zoom_start == 0
            and (self.zoom_end == sys.maxsize or self.zoom_end == 2048)
        )
