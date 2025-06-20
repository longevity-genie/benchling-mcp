#!/usr/bin/env python3
"""
Simple script to run the GenBank upload/delete test.

This script runs the test that:
1. Uploads test_CRISPRoff-v21.gb to the ZELAR project
2. Verifies the sequence exists
3. Archives (deletes) the uploaded sequence

Usage:
    python run_genbank_test.py
    
Requirements:
    - .env file with BENCHLING_API_KEY and BENCHLING_DOMAIN
    - test_CRISPRoff-v21.gb file in the test directory
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the GenBank upload test."""
    
    # Get the test file path
    test_file = Path(__file__).parent / "test" / "test_upload_genbank.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)
    
    print("🚀 Running GenBank upload/delete test...")
    print(f"📁 Test file: {test_file}")
    print("-" * 60)
    
    try:
        # Run the specific test with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            str(test_file), 
            "-v",  # Verbose output
            "-s",  # Don't capture output (show print statements)
            "--tb=short"  # Shorter traceback format
        ], check=True)
        
        print("-" * 60)
        print("✅ Test completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print("-" * 60)
        print(f"❌ Test failed with exit code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error running test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 