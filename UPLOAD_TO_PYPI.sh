#!/bin/bash
# PyPI Upload Script for x402 SDKs

echo "🚀 Uploading x402 SDKs to PyPI"
echo "================================"

# Check if .pypirc exists
if [ ! -f ~/.pypirc ]; then
    echo "❌ ERROR: ~/.pypirc not found!"
    echo "Please create ~/.pypirc with your PyPI credentials"
    echo "See .pypirc.template for the format"
    exit 1
fi

# Check if packages exist
if [ ! -f packages/fast-x402/dist/fast_x402-1.1.0-py3-none-any.whl ]; then
    echo "❌ ERROR: fast-x402 package not built!"
    echo "Run: cd packages/fast-x402 && python -m build"
    exit 1
fi

if [ ! -f packages/x402-langchain/dist/x402_langchain-1.1.0-py3-none-any.whl ]; then
    echo "❌ ERROR: x402-langchain package not built!"
    echo "Run: cd packages/x402-langchain && python -m build"
    exit 1
fi

# Prompt for confirmation
echo ""
echo "📦 Packages to upload:"
echo "  - fast-x402 v1.1.0"
echo "  - x402-langchain v1.1.0"
echo ""
read -p "Upload to PyPI? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Uploading fast-x402..."
    twine upload packages/fast-x402/dist/*
    
    echo ""
    echo "📤 Uploading x402-langchain..."
    twine upload packages/x402-langchain/dist/*
    
    echo ""
    echo "✅ Upload complete!"
    echo ""
    echo "🎉 Your packages are now live on PyPI!"
    echo "   pip install fast-x402"
    echo "   pip install x402-langchain"
else
    echo "❌ Upload cancelled"
fi