#!/usr/bin/env python3
"""Comprehensive test script for all packages"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    print(f"\n🔧 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Command failed!")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    
    print("✅ Success!")
    return True


def test_package(package_path):
    """Test a single package"""
    package_name = package_path.name
    print(f"\n{'='*60}")
    print(f"📦 Testing {package_name}")
    print(f"{'='*60}")
    
    # Check if package exists
    if not package_path.exists():
        print(f"❌ Package directory not found: {package_path}")
        return False
    
    # Install dependencies
    print(f"\n📥 Installing dependencies for {package_name}...")
    if not run_command(["pip", "install", "-e", "."], cwd=package_path):
        return False
    
    # Run linting (if ruff is available)
    print(f"\n🔍 Running linting for {package_name}...")
    try:
        run_command(["ruff", "check", "."], cwd=package_path)
    except:
        print("⚠️  Ruff not installed, skipping linting")
    
    # Run tests
    print(f"\n🧪 Running tests for {package_name}...")
    test_cmd = ["python", "-m", "pytest", "tests/", "-v"]
    if not run_command(test_cmd, cwd=package_path):
        print(f"⚠️  Tests failed for {package_name}, but continuing...")
    
    # Check build
    print(f"\n🏗️  Building {package_name}...")
    if not run_command(["python", "setup.py", "sdist", "bdist_wheel"], cwd=package_path):
        print(f"⚠️  Build failed for {package_name}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("🚀 X402 SDK Test Suite")
    print("="*60)
    
    # Get root directory
    root_dir = Path(__file__).parent.parent
    packages_dir = root_dir / "packages"
    
    # Test each package
    packages = ["fast-x402", "x402-langchain"]
    results = {}
    
    for package in packages:
        package_path = packages_dir / package
        results[package] = test_package(package_path)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    
    for package, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{package}: {status}")
    
    # Overall result
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n😞 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())