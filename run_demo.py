#!/usr/bin/env python3
"""
ArbiterOS-Core Demo Runner

This script provides an easy way to run the ArbiterOS-Core demo
and test the system functionality.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "pydantic",
        "langgraph", 
        "langchain",
        "openai"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required dependencies are installed!")
    return True


def run_basic_test():
    """Run the basic functionality test."""
    print("\n🧪 Running basic functionality test...")
    
    try:
        result = subprocess.run([
            sys.executable, "test_basic.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Basic test passed!")
            return True
        else:
            print(f"❌ Basic test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Basic test timed out")
        return False
    except Exception as e:
        print(f"❌ Basic test error: {e}")
        return False


def run_demo():
    """Run the full demo."""
    print("\n🚀 Running ArbiterOS-Core demo...")
    
    try:
        result = subprocess.run([
            sys.executable, "demo.py"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Demo completed successfully!")
            return True
        else:
            print(f"❌ Demo failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Demo timed out")
        return False
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return False


def show_usage():
    """Show usage information."""
    print("\n📚 Usage Examples:")
    print("  python run_demo.py test     - Run basic tests")
    print("  python run_demo.py demo     - Run full demo")
    print("  python run_demo.py all     - Run tests and demo")
    print("  python run_demo.py check   - Check dependencies only")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🚀 ArbiterOS-Core Demo Runner")
        print("=" * 50)
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "check":
        check_dependencies()
        
    elif command == "test":
        if check_dependencies():
            run_basic_test()
        else:
            print("❌ Cannot run tests - missing dependencies")
            
    elif command == "demo":
        if check_dependencies():
            run_demo()
        else:
            print("❌ Cannot run demo - missing dependencies")
            
    elif command == "all":
        if check_dependencies():
            print("\n" + "="*50)
            if run_basic_test():
                print("\n" + "="*50)
                run_demo()
            else:
                print("❌ Skipping demo due to test failures")
        else:
            print("❌ Cannot run - missing dependencies")
            
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()


if __name__ == "__main__":
    main()
