#!/bin/bash
python -m venv $(pwd)/venv
source $(pwd)/venv/bin/activate

pip install --upgrade pip
pip install --upgrade requests 
pip install --upgrade PySocks
pip install --upgrade netifaces
pip install --upgrade notify2 dbus-python

python test_node.py

sleep 4
deactivate
