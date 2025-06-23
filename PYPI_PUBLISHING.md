# 📦 Publishing x402 SDKs to PyPI

This guide explains how to publish both x402 SDK packages to PyPI with their shared modules.

## 🏗️ Architecture Decision: Shared Module Handling

We chose **Option 1: Include shared code in both packages** for simplicity and reliability:

- Each package contains its own copy of the shared modules
- No complex dependency management between packages
- Users can install either package independently
- Slightly larger package size (acceptable tradeoff)

### Alternative approaches considered:
- **Option 2**: Separate `x402-shared` package (adds complexity)
- **Option 3**: Git submodules (complicates installation)
- **Option 4**: Namespace packages (Python version compatibility issues)

## 📋 Pre-Publishing Checklist

### 1. Version Updates
- [x] Updated version to 1.1.0 in both setup.py files
- [x] Updated __version__ in __init__.py files
- [x] Created CHANGELOG entries

### 2. Shared Module Integration
- [x] Copied shared modules to each package
- [x] Updated imports to use local shared modules
- [x] Added shared modules to MANIFEST.in
- [x] Added package_data in setup.py

### 3. Dependencies
- [x] Removed sys.path manipulations
- [x] Added mnemonic dependency
- [x] Relaxed version constraints for compatibility

## 🚀 Publishing Steps

### Step 1: Clean Previous Builds
```bash
cd packages/fast-x402
rm -rf dist/ build/ *.egg-info/

cd ../x402-langchain
rm -rf dist/ build/ *.egg-info/
```

### Step 2: Build Both Packages
```bash
# Build fast-x402
cd packages/fast-x402
python -m build

# Build x402-langchain
cd ../x402-langchain
python -m build
```

### Step 3: Test Locally
```bash
# Create test virtualenv
python -m venv test-env
source test-env/bin/activate  # or test-env\Scripts\activate on Windows

# Install from built wheels
pip install packages/fast-x402/dist/fast_x402-1.1.0-py3-none-any.whl
pip install packages/x402-langchain/dist/x402_langchain-1.1.0-py3-none-any.whl

# Test imports
python -c "from fast_x402 import EnhancedX402Provider; print('✅ fast-x402 works')"
python -c "from x402_langchain import EnhancedX402Client; print('✅ x402-langchain works')"

deactivate
```

### Step 4: Upload to TestPyPI
```bash
# Upload to TestPyPI first
twine upload --repository testpypi packages/fast-x402/dist/*
twine upload --repository testpypi packages/x402-langchain/dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ fast-x402
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ x402-langchain
```

### Step 5: Upload to Production PyPI
```bash
# Once verified on TestPyPI
twine upload packages/fast-x402/dist/*
twine upload packages/x402-langchain/dist/*
```

## 🔑 PyPI Configuration

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN

[testpypi]
username = __token__
password = pypi-YOUR-TEST-API-TOKEN
repository = https://test.pypi.org/legacy/
```

## 📝 Post-Publishing

### Update Installation Docs
```markdown
# Installation
pip install fast-x402 x402-langchain

# With CLI tools
pip install fast-x402[cli]

# Development installation
pip install fast-x402[dev] x402-langchain[dev]
```

### Verify Installation
```bash
# Test CLI
x402 --help
x402 create test-project

# Test imports
python -c "from fast_x402 import create_provider; p = create_provider(); print(p)"
python -c "from x402_langchain import create_smart_agent; a = create_smart_agent(); print(a)"
```

## 🐛 Troubleshooting

### Import Errors
If users report import errors with shared modules:
1. Check MANIFEST.in includes shared files
2. Verify package_data in setup.py
3. Ensure __init__.py files exist in shared/

### Version Conflicts
If dependency conflicts arise:
1. Use compatible version ranges (>=, not ^)
2. Test with minimum supported versions
3. Document known incompatibilities

### Missing CLI
If `x402` command not found:
1. Ensure entry_points defined in setup.py
2. Check pip installed with correct extras
3. Try `python -m fast_x402.cli`

## 🎉 Success Metrics

After publishing:
- [ ] Both packages visible on PyPI
- [ ] Installation works without errors
- [ ] CLI tool accessible via `x402` command
- [ ] Shared functionality works in both packages
- [ ] Documentation updated with install instructions

## 🔄 Future Improvements

For version 2.0:
- Consider namespace packages if Python 3.9+ only
- Evaluate monorepo tools like `hatch`
- Add automated PyPI publishing via GitHub Actions
- Create consolidated documentation site