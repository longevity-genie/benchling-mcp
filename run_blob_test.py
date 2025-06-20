#!/usr/bin/env python3
"""
Simple test runner for GenBank blob upload test.
"""

import subprocess
import sys

def main():
    """Run the GenBank blob upload test."""
    print("🧪 Running GenBank Blob Upload Test")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test/test_upload_genbank_blob.py", 
            "-v", "-s"
        ], check=True)
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed!")
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 