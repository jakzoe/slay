import sys


class PlottingSettings:
    """Wrapper, welcher die Einstellungen für einen Plot enthält."""

    file_path = ""

    # Angabe: Wellenlänge
    zoom_start = 0
    zoom_end = 0

    # nur einen Ausschnitt/Batch aus den Messungen zur Durchschnittsberechnung etc. nutzten.
    # Angabe: Index
    interval_start = 0
    interval_end = 0

    normalize_integrationtime = False
    normalize_power = False

    def __init__(
        self,
        file_path,
        zoom_start=0,
        zoom_end=sys.maxsize,
        interval_start=0,
        interval_end=sys.maxsize,
        normalize_integrationtime=False,
        normalize_power=False,
    ):
        self.file_path = file_path

        self.zoom_start = zoom_start
        self.zoom_end = zoom_end

        self.interval_start = interval_start
        self.interval_end = interval_end

        self.normalize_integrationtime = normalize_integrationtime
        self.normalize_power = normalize_power

    def sliced(self) -> bool:
        """Prüft, ob das Bild ein Ausschnitt einer Messreihe ist."""
        return not (self.interval_start == 0 and self.interval_end == sys.maxsize)

    def zoom(self) -> bool:
        """Prüft, ob das Bild ein Ausschnitt des Spektrums, welches das Spektrometer messen kann, ist."""
        return not (
            self.zoom_start == 0
            and (self.zoom_end == sys.maxsize or self.zoom_end == 2048)
        )
