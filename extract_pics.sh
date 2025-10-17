#!/bin/bash

rm -r messungen_pics/
# damit die Bilder die gleiche Struktur behalten
rsync -av --exclude='*.npz' --exclude='*.json' messungen/ messungen_pics/