## === Einstellung des Spektroskops ===

INTTIME = 1  # 1-498000 ms
SCAN_AVG = 1  # > 1
SMOOTH = 0  # 1-4
XTIMING = 3  # 1-4

## === Einstellung des Diagramms ===

NAME = "ZZZ Langzeitmessung mit Superkontinuumlaser mit Blaulichtlasern"
# neue Messungen überschreiben alte Messungen
OVERWRITE = True

## === Einstellungen des Lasers ===

# wie häufig eine Messung wiederholt wird
REPETITIONS = 10  #  29.8 TiB for an a

## ACHTUNG: DELAY und IRRADITION_TIME sollten MINDESTENS 3 ms, sein, der Arduino schafft es nicht in kürzerer Zeit, alles anzustellen
# Zeit in ms, die zwischen jeder Messung gewartet werden soll
MEASUREMENT_DELAY = 3
# Zeit in ms, die auf das Chlorophyll gestrahlt wird
IRRADITION_TIME = 3
# Zeit in ms, die auf den Arduino gewartet wird
ARDUINO_DELAY = 3
# wie stark der Laser eingestellt ist (z. B. Frequenz oder Spannung, je nach Lasertyp)
INTENSITY = 100
# Laser durchgängig angeschaltet lassen oder nicht
CONTINOUS = True
# ob ein Graufilter dazwischen ist oder nicht
GRAUFILTER = False
# Sekunden, nach denen die Messung, unabhängig von REPETITIONS, beendet werden soll
TIMEOUT = 4600


if GRAUFILTER:
    NAME += " mit Graufilter"

NAME += " mit " + str(INTENSITY) + " %"

DEBUG = False

# === Indices ===
INTTIME_INDEX = 0
INTENSITY_INDEX = 1
SCAN_AVG_INDEX = 2
SMOOTH_INDEX = 3
XTIMING_INDEX = 4
REPETITIONS_INDEX = 5
ARDUINO_DELAY_INDEX = 6
IRRADITION_TIME_INDEX = 7
CONTINOUS_INDEX = 8
