#!/usr/bin/env python3
"""Comprehensive test runner for the Irrigation Addon."""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"\nCompleted in {duration:.2f} seconds")
        print(f"Exit code: {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def check_python_environment():
    """Check if Python environment is properly set up."""
    print("Checking Python environment...")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check if we can import required modules
    required_modules = ['ast', 'json', 're', 'datetime', 'pathlib']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            missing_modules.append(module)
            print(f"❌ {module} not available")
    
    if missing_modules:
        print(f"❌ Missing required modules: {missing_modules}")
        return False
    
    return True


def validate_test_files():
    """Validate that all test files exist and are syntactically correct."""
    print("\nValidating test files...")
    
    test_files = [
        "tests/test_models.py",
        "tests/test_coordinator.py", 
        "tests/test_config_flow.py",
        "tests/test_storage.py",
        "tests/test_integration.py",
        "tests/test_frontend.py"
    ]
    
    all_valid = True
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ {test_file} not found")
            all_valid = False
            continue
        
        # Check syntax
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, test_file, 'exec')
            print(f"✅ {test_file} syntax valid")
            
        except SyntaxError as e:
            print(f"❌ {test_file} syntax error: {e}")
            all_valid = False
        except Exception as e:
            print(f"❌ {test_file} error: {e}")
            all_valid = False
    
    return all_valid


def run_syntax_validation():
    """Run syntax validation on all Python files."""
    print("\nRunning syntax validation...")
    
    python_files = []
    
    # Find all Python files in custom_components
    if os.path.exists("custom_components"):
        for root, dirs, files in os.walk("custom_components"):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
    
    # Add test files
    if os.path.exists("tests"):
        for root, dirs, files in os.walk("tests"):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
    
    syntax_errors = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, py_file, 'exec')
            print(f"✅ {py_file}")
            
        except SyntaxError as e:
            syntax_errors.append((py_file, str(e)))
            print(f"❌ {py_file}: {e}")
        except Exception as e:
            syntax_errors.append((py_file, str(e)))
            print(f"❌ {py_file}: {e}")
    
    if syntax_errors:
        print(f"\n❌ Found {len(syntax_errors)} syntax errors")
        return False
    else:
        print(f"\n✅ All {len(python_files)} Python files have valid syntax")
        return True


def run_import_validation():
    """Validate that imports work correctly."""
    print("\nValidating imports...")
    
    # Add current directory to Python path
    sys.path.insert(0, os.getcwd())
    
    import_tests = [
        ("custom_components.irrigation_addon.const", "DOMAIN"),
        ("custom_components.irrigation_addon.models", "Room"),
        ("custom_components.irrigation_addon.models", "IrrigationEvent"),
        ("custom_components.irrigation_addon.models", "Shot"),
    ]
    
    import_errors = []
    
    for module_name, attribute in import_tests:
        try:
            module = __import__(module_name, fromlist=[attribute])
            getattr(module, attribute)
            print(f"✅ {module_name}.{attribute}")
        except ImportError as e:
            import_errors.append((module_name, str(e)))
            print(f"❌ {module_name}: {e}")
        except AttributeError as e:
            import_errors.append((module_name, str(e)))
            print(f"❌ {module_name}.{attribute}: {e}")
        except Exception as e:
            import_errors.append((module_name, str(e)))
            print(f"❌ {module_name}: {e}")
    
    if import_errors:
        print(f"\n❌ Found {len(import_errors)} import errors")
        return False
    else:
        print(f"\n✅ All imports successful")
        return True


def run_pytest_if_available():
    """Run pytest if available."""
    print("\nChecking for pytest...")
    
    # Check if pytest is available
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ pytest available")
            print(f"Version: {result.stdout.strip()}")
            
            # Run pytest
            return run_command(
                "python -m pytest tests/ -v --tb=short",
                "Running pytest test suite"
            )
        else:
            print("❌ pytest not available")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ pytest not available")
        return False


def run_manual_test_validation():
    """Run manual test validation without pytest."""
    print("\nRunning manual test validation...")
    
    # Run the validation script
    if os.path.exists("validate_tests.py"):
        return run_command(
            "python validate_tests.py",
            "Manual test validation"
        )
    else:
        print("❌ validate_tests.py not found")
        return False


def generate_test_report():
    """Generate a test report."""
    print("\nGenerating test report...")
    
    report_lines = [
        "# Irrigation Addon Test Report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Test Files Status",
    ]
    
    test_files = [
        "tests/test_models.py",
        "tests/test_coordinator.py", 
        "tests/test_config_flow.py",
        "tests/test_storage.py",
        "tests/test_integration.py",
        "tests/test_frontend.py"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count test methods
                test_count = content.count('def test_')
                class_count = content.count('class Test')
                
                report_lines.append(f"- ✅ {test_file}: {class_count} test classes, {test_count} test methods")
                
            except Exception as e:
                report_lines.append(f"- ❌ {test_file}: Error reading file - {e}")
        else:
            report_lines.append(f"- ❌ {test_file}: File not found")
    
    report_lines.extend([
        "",
        "## Implementation Files Status",
    ])
    
    impl_files = [
        "custom_components/irrigation_addon/__init__.py",
        "custom_components/irrigation_addon/models.py",
        "custom_components/irrigation_addon/coordinator.py",
        "custom_components/irrigation_addon/config_flow.py",
        "custom_components/irrigation_addon/storage.py",
        "custom_components/irrigation_addon/services.py"
    ]
    
    for impl_file in impl_files:
        if os.path.exists(impl_file):
            report_lines.append(f"- ✅ {impl_file}")
        else:
            report_lines.append(f"- ❌ {impl_file}: Not found")
    
    # Write report
    try:
        with open("test_report.md", "w", encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        
        print("✅ Test report generated: test_report.md")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")
        return False


def main():
    """Main test runner function."""
    print("🧪 Irrigation Addon Test Runner")
    print("=" * 60)
    
    start_time = time.time()
    results = {}
    
    # Run all validation steps
    steps = [
        ("Environment Check", check_python_environment),
        ("Test File Validation", validate_test_files),
        ("Syntax Validation", run_syntax_validation),
        ("Import Validation", run_import_validation),
        ("Pytest Execution", run_pytest_if_available),
        ("Manual Validation", run_manual_test_validation),
        ("Report Generation", generate_test_report)
    ]
    
    for step_name, step_function in steps:
        print(f"\n🔍 {step_name}")
        print("-" * 40)
        
        try:
            results[step_name] = step_function()
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results[step_name] = False
    
    # Summary
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for step_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{step_name:.<40} {status}")
    
    print(f"\nResults: {passed}/{total} steps passed")
    print(f"Total time: {total_time:.2f} seconds")
    
    if passed == total:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} steps failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())