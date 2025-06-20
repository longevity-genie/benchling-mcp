#!/usr/bin/env python3
"""
Example script for running Benchling MCP judge tests.

This script demonstrates how to run the judge tests that evaluate
the quality of responses from the Benchling MCP server using LLM judges.

Requirements:
- .env file with BENCHLING_API_KEY and BENCHLING_DOMAIN
- LLM API keys for the judge system (e.g., GEMINI_API_KEY)
- Access to actual Benchling data
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Run the judge tests with proper environment setup."""
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["BENCHLING_API_KEY", "BENCHLING_DOMAIN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        return 1
    
    # Check if we have LLM API access
    llm_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    has_llm = any(os.getenv(var) for var in llm_vars)
    
    if not has_llm:
        print(f"⚠️  No LLM API keys found ({', '.join(llm_vars)})")
        print("Judge tests require LLM access for evaluation")
        return 1
    
    print("🧪 Running Benchling MCP Judge Tests...")
    print("This will test the quality of Benchling MCP responses using LLM judges")
    print()
    
    # Run the judge tests
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test/test_judge.py", 
            "-v",
            "--tb=short"
        ], check=False)
        
        if result.returncode == 0:
            print("\n✅ All judge tests passed!")
        else:
            print(f"\n❌ Some judge tests failed (exit code: {result.returncode})")
            
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 