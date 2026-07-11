#!/bin/bash

# Define the path to the venv python
VENV_PYTHON=".env/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    echo "Running script using venv Python..."
    if [ "$#" -eq 0 ]; then
        echo "No arguments given, so using defaults:"
        $VENV_PYTHON script_new.py --token XRP --usdt-amount 5
    else
        # Forward any arguments passed to this shell script into Python
        $VENV_PYTHON script_new.py "$@"
    fi
else
    echo "Error: Virtual environment python not found at $VENV_PYTHON"
    exit 1
fi

