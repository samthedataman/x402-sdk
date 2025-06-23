# Publishing to PyPI

This guide explains how to publish the x402 SDK packages to PyPI.

## Prerequisites

1. PyPI account at https://pypi.org
2. Test PyPI account at https://test.pypi.org (recommended for testing)
3. API tokens for both accounts
4. Python build tools installed

## Setup

### 1. Install Build Tools

```bash
pip install --upgrade pip setuptools wheel twine build
```

### 2. Configure PyPI Credentials

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
repository = https://test.pypi.org/legacy/
```

## Building Packages

### Build fast-x402

```bash
cd packages/fast-x402
python -m build
```

This creates files in `dist/`:
- `fast-x402-1.0.0.tar.gz` (source distribution)
- `fast_x402-1.0.0-py3-none-any.whl` (wheel)

### Build x402-langchain

```bash
cd packages/x402-langchain
python -m build
```

## Testing Publication

Always test on TestPyPI first:

```bash
# Upload to TestPyPI
cd packages/fast-x402
twine upload --repository testpypi dist/*

cd packages/x402-langchain
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ fast-x402
pip install --index-url https://test.pypi.org/simple/ x402-langchain
```

## Publishing to PyPI

Once tested, publish to production PyPI:

```bash
# Upload fast-x402
cd packages/fast-x402
twine upload dist/*

# Upload x402-langchain
cd packages/x402-langchain
twine upload dist/*
```

## Verification

After publishing:

1. Check package pages:
   - https://pypi.org/project/fast-x402/
   - https://pypi.org/project/x402-langchain/

2. Test installation:
   ```bash
   pip install fast-x402
   pip install x402-langchain
   ```

## Version Management

To release a new version:

1. Update version in `setup.py` and `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.0.1`
4. Build and publish new version

## Automated Publishing

Use GitHub Actions for automated publishing on release:

1. Add PyPI API token as GitHub secret: `PYPI_API_TOKEN`
2. Create release on GitHub
3. CI/CD will automatically build and publish

## Troubleshooting

### "Package already exists" Error
- You can't overwrite existing versions
- Increment version number and republish

### Authentication Issues
- Ensure you're using API tokens, not username/password
- Check token has upload permissions

### Build Issues
- Ensure all dependencies are listed in setup.py
- Run tests before building: `pytest tests/`

## Security Notes

- Never commit PyPI tokens to git
- Use GitHub secrets for CI/CD
- Regularly rotate API tokens
- Enable 2FA on PyPI account

## Maintenance

Regular maintenance tasks:

1. Update dependencies: `pip-compile --upgrade`
2. Run security checks: `safety check`
3. Update documentation
4. Monitor for issues on GitHub

## Support

For issues with publishing:
- PyPI documentation: https://packaging.python.org
- GitHub Issues: https://github.com/x402/x402-sdk/issues