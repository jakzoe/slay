import numpy as np


# spectrometer, wav = sn.array_get_spec(0)
def array_get_spec(*args, **kwargs):
    return None, np.random.rand(2048, 1)


# sn.getDeviceId(spectrometer))
def getDeviceId(*args, **kwargs):
    return -1


# sn.ext_trig(spectrometer, True)
def ext_trig(arg, *args, **kwargs):
    pass


# sn.setParam(spectrometer, INTTIME, SCAN_AVG, SMOOTH, XTIMING, True)
def setParam(arg, *args, **kwargs):
    pass


# var = sn.array_spectrum(spectrometer, wav)
def array_spectrum(arg, *args, **kwargs):
    return np.random.rand(2048, 2)


# var = sn.getSpectrum_Y(spectrometer)
def getSpectrum_Y(arg, *args, **kwargs):
    return (
        np.random.rand(
            2048,
        )
        * 100
    )


# sn.reset(spectrometer)
def reset(arg, *args, **kwargs):
    pass
