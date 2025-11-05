#!/usr/bin/env python3
"""Simple test runner to validate unit tests without pytest."""

import sys
import os
import importlib.util
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_file(test_file_path):
    """Run tests from a specific file."""
    print(f"\n=== Running tests from {test_file_path} ===")
    
    try:
        # Load the test module
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)
        
        # Find test classes and methods
        test_count = 0
        passed_count = 0
        failed_count = 0
        
        for name in dir(test_module):
            obj = getattr(test_module, name)
            if isinstance(obj, type) and name.startswith('Test'):
                print(f"\n--- Running {name} ---")
                
                # Create instance of test class
                test_instance = obj()
                
                # Run test methods
                for method_name in dir(test_instance):
                    if method_name.startswith('test_'):
                        test_count += 1
                        try:
                            print(f"  {method_name}...", end=" ")
                            method = getattr(test_instance, method_name)
                            
                            # Handle async test methods
                            if hasattr(method, '__code__') and method.__code__.co_flags & 0x80:
                                import asyncio
                                asyncio.run(method())
                            else:
                                method()
                            
                            print("PASS")
                            passed_count += 1
                        except Exception as e:
                            print(f"FAIL - {e}")
                            failed_count += 1
                            if "--verbose" in sys.argv:
                                traceback.print_exc()
        
        print(f"\nResults: {passed_count} passed, {failed_count} failed, {test_count} total")
        return failed_count == 0
        
    except Exception as e:
        print(f"Error loading test file: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False

def main():
    """Main test runner."""
    print("Simple Test Runner")
    print("==================")
    
    # Test files to run
    test_files = [
        "tests/test_models.py"
    ]
    
    all_passed = True
    
    for test_file in test_files:
        if os.path.exists(test_file):
            success = run_test_file(test_file)
            all_passed = all_passed and success
        else:
            print(f"Test file not found: {test_file}")
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("All tests PASSED!")
        sys.exit(0)
    else:
        print("Some tests FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()