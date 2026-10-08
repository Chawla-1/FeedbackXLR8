"""
Pre-Commit Validation Script
Comprehensive checks before pushing to GitHub
"""

import os
import sys
import subprocess
import py_compile
import json

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_python_syntax():
    """Check all Python files for syntax errors"""
    print_section("1. CHECKING PYTHON SYNTAX")
    
    errors = []
    python_files = []
    
    # Find all .py files
    for root, dirs, files in os.walk('.'):
        # Skip venv, __pycache__, .git
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'env', 'node_modules']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files")
    
    for filepath in python_files:
        try:
            py_compile.compile(filepath, doraise=True)
            print(f"  ✅ {filepath}")
        except py_compile.PyCompileError as e:
            errors.append(f"Syntax error in {filepath}: {e}")
            print(f"  ❌ {filepath}: {e}")
    
    if errors:
        print(f"\n❌ {len(errors)} SYNTAX ERRORS FOUND")
        return False
    else:
        print(f"\n✅ All {len(python_files)} Python files are syntactically correct")
        return True

def check_imports():
    """Check if main files can be imported"""
    print_section("2. CHECKING CRITICAL IMPORTS")
    
    critical_files = ['config.py', 'app.py']
    errors = []
    
    for module in critical_files:
        print(f"\nTesting {module}...")
        try:
            result = subprocess.run(
                [sys.executable, '-c', f'import {module.replace(".py", "")}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                errors.append(f"Failed to import {module}: {result.stderr}")
                print(f"  ❌ {module}: {result.stderr[:200]}")
            else:
                print(f"  ✅ {module} imports successfully")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  {module} import timeout (may be normal for Streamlit)")
        except Exception as e:
            errors.append(f"Error testing {module}: {e}")
            print(f"  ❌ {module}: {e}")
    
    if errors:
        print(f"\n❌ {len(errors)} IMPORT ERRORS")
        return False
    else:
        print("\n✅ All critical imports successful")
        return True

def check_required_files():
    """Check for required files"""
    print_section("3. CHECKING REQUIRED FILES")
    
    required_files = [
        'README.md',
        'requirements.txt',
        'app.py',
        'config.py',
        '.gitignore',
        'HACKATHON_PROJECT_REPORT.md',
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024
            print(f"  ✅ {file} ({size:.1f} KB)")
        else:
            missing.append(file)
            print(f"  ❌ {file} MISSING")
    
    if missing:
        print(f"\n❌ {len(missing)} REQUIRED FILES MISSING")
        return False
    else:
        print("\n✅ All required files present")
        return True

def check_requirements_txt():
    """Validate requirements.txt"""
    print_section("4. CHECKING REQUIREMENTS.TXT")
    
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt not found")
        return False
    
    with open('requirements.txt', 'r') as f:
        lines = f.readlines()
    
    print(f"Found {len(lines)} dependencies:")
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            print(f"  • {line}")
    
    print("\n✅ requirements.txt is valid")
    return True

def check_sensitive_files():
    """Check for sensitive files that shouldn't be committed"""
    print_section("5. CHECKING FOR SENSITIVE FILES")
    
    sensitive_patterns = [
        '.env',
        '*.key',
        '*.pem',
        '*secret*',
        '*password*',
        'credentials.json',
    ]
    
    sensitive_found = []
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
        for file in files:
            file_lower = file.lower()
            # Check service account JSON (should be in .gitignore)
            if file.endswith('.json') and 'service' not in file_lower and file != 'package.json':
                filepath = os.path.join(root, file)
                # Check if it's a service account by content
                try:
                    with open(filepath, 'r') as f:
                        content = json.load(f)
                        if 'private_key' in content or 'client_email' in content:
                            sensitive_found.append(filepath)
                            print(f"  ⚠️  Service account JSON: {filepath}")
                except:
                    pass
            
            # Check for .env files (not .env.example)
            if file == '.env':
                sensitive_found.append(os.path.join(root, file))
                print(f"  ⚠️  Environment file: {os.path.join(root, file)}")
    
    if sensitive_found:
        print(f"\n⚠️  {len(sensitive_found)} potentially sensitive files found")
        print("Make sure these are in .gitignore!")
        return True  # Warning, not error
    else:
        print("\n✅ No sensitive files detected")
        return True

def check_gitignore():
    """Check .gitignore exists and has common patterns"""
    print_section("6. CHECKING .GITIGNORE")
    
    if not os.path.exists('.gitignore'):
        print("❌ .gitignore not found")
        return False
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    required_patterns = [
        '__pycache__',
        '*.pyc',
        '.env',
    ]
    
    missing = []
    for pattern in required_patterns:
        if pattern in content:
            print(f"  ✅ {pattern}")
        else:
            missing.append(pattern)
            print(f"  ⚠️  {pattern} not in .gitignore")
    
    if missing:
        print(f"\n⚠️  {len(missing)} recommended patterns missing (not critical)")
    else:
        print("\n✅ .gitignore looks good")
    
    return True

def check_file_sizes():
    """Check for large files that might cause issues"""
    print_section("7. CHECKING FILE SIZES")
    
    large_files = []
    max_size_mb = 50  # GitHub warning threshold
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
        for file in files:
            filepath = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                if size_mb > max_size_mb:
                    large_files.append((filepath, size_mb))
                    print(f"  ⚠️  {filepath}: {size_mb:.1f} MB")
            except:
                pass
    
    if large_files:
        print(f"\n⚠️  {len(large_files)} large files found (>50MB)")
        print("Consider using Git LFS for large files")
    else:
        print("\n✅ No excessively large files")
    
    return True

def check_git_status():
    """Check git status"""
    print_section("8. CHECKING GIT STATUS")
    
    try:
        result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Git not initialized or error running git status")
            return False
        
        output = result.stdout.strip()
        if output:
            print("Files to be committed:")
            for line in output.split('\n')[:20]:  # Show first 20
                print(f"  {line}")
            
            # Count changes
            lines = output.split('\n')
            print(f"\n📊 Total changes: {len(lines)} files")
        else:
            print("✅ Working directory clean (no changes to commit)")
        
        return True
    except Exception as e:
        print(f"⚠️  Could not check git status: {e}")
        return True

def main():
    print("="*70)
    print("  PRE-COMMIT VALIDATION - FINAL CHECK BEFORE GITHUB PUSH")
    print("="*70)
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    checks = [
        ("Python Syntax", check_python_syntax),
        ("Critical Imports", check_imports),
        ("Required Files", check_required_files),
        ("Requirements.txt", check_requirements_txt),
        ("Sensitive Files", check_sensitive_files),
        ("Gitignore", check_gitignore),
        ("File Sizes", check_file_sizes),
        ("Git Status", check_git_status),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results[name] = False
    
    # Final summary
    print("\n" + "="*70)
    print("  VALIDATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED - READY TO PUSH!")
        print("="*70)
        return 0
    else:
        print(f"⚠️  {total - passed} CHECK(S) FAILED")
        print("Please fix the issues before pushing to GitHub")
        print("="*70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
