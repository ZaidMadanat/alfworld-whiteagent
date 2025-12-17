#!/bin/bash
# Setup script for creating a virtual environment

set -e

echo "Setting up virtual environment..."

# Use Python 3.12.1 (or python3 if 3.12.1 not available)
PYTHON_CMD="python3"
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version

# Create virtual environment
echo "Creating virtual environment in .venv/..."
$PYTHON_CMD -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if .env exists, if not copy from .env.example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Copying .env.example to .env..."
        cp .env.example .env
        echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    else
        echo "Creating .env file..."
        echo "OPENAI_API_KEY=" > .env
        echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    fi
else
    echo "✓ .env file already exists"
fi

echo ""
echo "✓ Virtual environment setup complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Don't forget to add your OPENAI_API_KEY to the .env file!"

