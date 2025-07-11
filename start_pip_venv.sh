#!/bin/bash

# Create and activate virtual environment in current directory
python -m venv ./venv
source ./venv/bin/activate

# Upgrade pip and install full zignode package with optional extras
pip install --upgrade pip
pip install --upgrade "zignode[full]"

echo "#!/usr/bin/python"           > test_node_tmp.py
echo "# -*- coding: utf-8 -*-"    >> test_node_tmp.py
echo "import zignode"             >> test_node_tmp.py
echo "def test_function_01(arg):" >> test_node_tmp.py
echo "  frame=zignode.frame(arg)" >> test_node_tmp.py
echo "  return frame"             >> test_node_tmp.py
echo "zignode.auto(locals())"     >> test_node_tmp.py

# Run test script
python test_node_tmp.py

# Wait for a few seconds to let async tasks (if any) complete
sleep 1

# Deactivate the virtual environment
deactivate
