#!/bin/bash

# KubeVirt Portal - Local Development Setup Script
# This script sets up a local development environment

set -e  # Exit on error

echo "========================================"
echo "KubeVirt Portal - Development Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9 or higher is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ .env file created"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env file and configure:"
        echo "   - GIT_REPO_URL"
        echo "   - GIT_USERNAME"
        echo "   - GIT_TOKEN"
        echo ""
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
else
    echo "✓ .env file already exists"
    echo ""
fi

# Create required directories
echo "Creating required directories..."
mkdir -p /tmp/kubevirt-portal/clones
echo "✓ Directories created"
echo ""

# Verify template structure
echo "Verifying template structure..."
required_dirs=(
    "app/templates/base"
    "app/templates/profiles"
    "app/templates/snippets"
)

all_exist=true
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        all_exist=false
    fi
done

if [ "$all_exist" = true ]; then
    echo "✓ Template structure verified"
else
    echo "⚠️  Some template directories are missing"
fi
echo ""

# Test imports
echo "Testing Python imports..."
python3 << EOF
try:
    from app.schemas import VMConfigSchema
    from app.template_manager import TemplateManager
    from app.git_manager import GitOperationManager
    from app.constants import VM_NAME_PATTERN
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)
EOF
echo ""

# Check .env configuration
echo "Checking .env configuration..."
if grep -q "your-github-username" .env 2>/dev/null; then
    echo "⚠️  WARNING: .env file contains default values"
    echo "   Please update the following variables:"
    echo "   - GIT_REPO_URL"
    echo "   - GIT_USERNAME"
    echo "   - GIT_TOKEN"
    echo ""
    echo "To edit: nano .env"
    echo ""
    NEEDS_CONFIG=true
else
    echo "✓ .env file appears configured"
    NEEDS_CONFIG=false
fi
echo ""

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""

if [ "$NEEDS_CONFIG" = true ]; then
    echo "⚠️  Next steps:"
    echo "   1. Edit .env file: nano .env"
    echo "   2. Configure Git repository settings"
    echo "   3. Run: python run.py"
else
    echo "Ready to run!"
    echo ""
    echo "Start the application:"
    echo "   python run.py"
    echo ""
    echo "Or run in development mode:"
    echo "   FLASK_DEBUG=1 python run.py"
fi
echo ""
echo "For detailed documentation, see DEVELOPMENT.md"
echo ""

# Optional: Fetch noVNC assets for offline usage
read -p "Download local noVNC UI assets for offline use? [y/N] " RESP
if [[ "$RESP" =~ ^[Yy]$ ]]; then
    echo "Downloading noVNC (v1.5.0) assets..."
    NOVNC_VER="v1.5.0"
    TMPDIR=$(mktemp -d)
    curl -L -o "$TMPDIR/novnc.tar.gz" "https://github.com/novnc/noVNC/archive/refs/tags/${NOVNC_VER}.tar.gz"
    mkdir -p "$TMPDIR/novnc"
    tar -xzf "$TMPDIR/novnc.tar.gz" -C "$TMPDIR/novnc" --strip-components=1
    mkdir -p app/static/novnc
    cp -r "$TMPDIR/novnc/app" app/static/novnc/app
    cp -r "$TMPDIR/novnc/core" app/static/novnc/core
    rm -rf "$TMPDIR"
    echo "✓ noVNC assets installed to app/static/novnc/"
fi
