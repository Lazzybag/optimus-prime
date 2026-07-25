#!/bin/bash

# Liquid Staking Protocol Discovery Bot - Automated Setup
# This script sets up the complete environment for the bot

echo ""
echo "================================================================================="
echo "🚀 LIQUID STAKING PROTOCOL DISCOVERY BOT - SETUP"
echo "================================================================================="
echo ""

# Check Python version
echo "📋 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.7 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install requirements
echo "📚 Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check .env file
echo "🔐 Checking environment configuration..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    if grep -q "GITHUB_PAT=your_github_pat_token_here" .env; then
        echo "⚠️  GITHUB_PAT not set. Please edit .env file and add your GitHub PAT:"
        echo "   1. Go to: https://github.com/settings/tokens"
        echo "   2. Generate new token (classic)"
        echo "   3. Set scopes: repo:status, public_repo, read:repo_hook"
        echo "   4. Copy token and paste in .env file"
        echo ""
    else
        echo "✅ GITHUB_PAT appears to be configured"
    fi
else
    echo "❌ .env file not found!"
    exit 1
fi
echo ""

# Summary
echo "================================================================================="
echo "✅ SETUP COMPLETE!"
echo "================================================================================="
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Edit your GitHub PAT in .env file:"
echo "   - Open .env file"
echo "   - Replace 'your_github_pat_token_here' with your actual token"
echo "   - Save the file"
echo ""
echo "2. Run the bot:"
echo "   source venv/bin/activate  (if not already activated)"
echo "   python main.py"
echo ""
echo "================================================================================="
echo ""
