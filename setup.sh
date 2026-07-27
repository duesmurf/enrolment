#!/bin/bash
# ============================================================
# Student Enrolment Agent - Quick Setup Script
# Run this in Git Bash on Windows: bash setup.sh
# ============================================================

echo ""
echo "============================================"
echo "  Student Enrolment Agent - Quick Setup"
echo "============================================"
echo ""

# Check Python
echo "[1/4] Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "  ERROR: Python not found!"
    echo "  Install Python from: https://www.python.org/downloads/"
    exit 1
fi
echo "  Found: $($PYTHON --version)"

# Create virtual environment
echo ""
echo "[2/4] Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "  Created: ./venv"
else
    echo "  Already exists: ./venv"
fi

# Activate and install
echo ""
echo "[3/4] Installing dependencies..."
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
pip install -r requirements.txt --quiet
echo "  Done!"

# Create directories
echo ""
echo "[4/4] Setting up project structure..."
mkdir -p credentials
mkdir -p output
cp -n .env.example .env 2>/dev/null || true
echo "  Created: credentials/ output/ .env"

# Check for credentials
echo ""
echo "============================================"
if [ -f "credentials/credentials.json" ]; then
    echo "  READY! Credentials found."
    echo ""
    echo "  Run:  python main.py --demo    (test)"
    echo "  Run:  python main.py           (full pipeline)"
else
    echo "  ALMOST READY!"
    echo ""
    echo "  Next step: Place your credentials.json file:"
    echo "    cp ~/Downloads/credentials.json credentials/"
    echo ""
    echo "  Then run:  python main.py --setup  (verify)"
    echo "  Then run:  python main.py --demo   (test)"
fi
echo "============================================"
echo ""
