class StellarnetSpectrometer:
    def __init__(self, index):
        # from stellarnet.stellarnet_driverLibs import stellarnet_driver3 as driver
        from driverLibs import stellarnet_driver3 as driver  # type: ignore

        self._driver = driver
        self._handle = driver.array_get_spec_only(index)

        # hat scheinbar nichts mit external triggering zu tun: Mein Spektrometer hat das Modul beispielsweise gar nicht. Es schaltet lediglich ein Timeout aus oder an, welches einen Fehler schmeißt, wenn das Readout zu lange dauert
        driver.ext_trig(self._handle, True)

    def configure(self, specto_settings):
        self._driver.setParam(
            self._handle,
            specto_settings.INTTIME,
            specto_settings.SCAN_AVG,
            specto_settings.SMOOTH,
            specto_settings.XTIMING,
            # ignoriert die erste Messung, da diese durch die Änderung der Integrationszeit ungenau sein kann
            True,
        )

    def get_wavelengths(self):
        # es gibt 2048 Elemente, jede der 864 Wellenlängen ist immer mit zwei
        # bis drei Nachkommastellen vertreten (wav[0], wav[-1] -> 285.24, 1149.48...)
        return self._driver.getSpectrum_X(self._handle).reshape(-1)

    def measure(self):
        return self._driver.getSpectrum_Y(self._handle)

    def close(self):
        self._driver.reset(self._handle)
