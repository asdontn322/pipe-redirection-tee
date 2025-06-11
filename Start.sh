#!/bin/bash
if ! command -v cmatrix &> /dev/null; then
    echo "cmatrix not installed, skipping animation"
    sleep 1
else
    cmatrix -bs -u 5 &
    CMATRIX_PID=$!
    sleep 2
    kill $CMATRIX_PID
fi
clear
if [ -f "butterterm_cosmic.py" ]; then
    python3 butterterm_cosmic.py
else
    echo "butterterm_cosmic.py not found"
    exit 1
fi
