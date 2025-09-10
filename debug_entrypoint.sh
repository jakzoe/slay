#!/bin/sh

[ -f /requirements.txt ] || /usr/local/bin/pip3 freeze > requirements.txt
[ -f /licenses.md ] || /usr/local/bin/pip-licenses --python=/usr/local/bin/python3 --format=markdown > licenses.md


/usr/local/bin/python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client examples/run_measurement.py
