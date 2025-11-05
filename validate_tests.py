#!/usr/bin/env python3
"""Validate test files for syntax and basic structure."""

import ast
import os
import sys

def validate_test_file(file_path):
    """Validate a test file for syntax and structure."""
    print(f"Validating {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        tree = ast.parse(content, filename=file_path)
        
        # Count test classes and methods
        test_classes = 0
        test_methods = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                test_classes += 1
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_methods += 1
        
        print(f"  [OK] Syntax valid")
        print(f"  [OK] Found {test_classes} test classes")
        print(f"  [OK] Found {test_methods} test methods")
        
        # Check for required imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        required_imports = ['pytest', 'custom_components.irrigation_addon']
        missing_imports = []
        for req in required_imports:
            if not any(req in imp for imp in imports):
                missing_imports.append(req)
        
        if missing_imports:
            print(f"  [WARN] Missing imports: {missing_imports}")
        else:
            print(f"  [OK] All required imports present")
        
        return True
        
    except SyntaxError as e:
        print(f"  [ERROR] Syntax error: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] Error: {e}")
        return False

def main():
    """Main validation function."""
    print("Test File Validator")
    print("===================")
    
    test_files = [
        "tests/test_models.py",
        "tests/test_coordinator.py", 
        "tests/test_config_flow.py",
        "tests/test_storage.py"
    ]
    
    all_valid = True
    
    for test_file in test_files:
        if os.path.exists(test_file):
            valid = validate_test_file(test_file)
            all_valid = all_valid and valid
        else:
            print(f"Test file not found: {test_file}")
            all_valid = False
        print()
    
    if all_valid:
        print("[SUCCESS] All test files are valid!")
        return 0
    else:
        print("[ERROR] Some test files have issues!")
        return 1

if __name__ == "__main__":
    sys.exit(main())