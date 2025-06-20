#!/usr/bin/env python3
"""
Simple example script to get data from Benchling.
This demonstrates the basic usage pattern.
"""

import asyncio
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Import our Benchling MCP server
from benchling_mcp.server import BenchlingMCP


async def main():
    """Get some entries from Benchling."""
    
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded environment from {env_file}")
    else:
        print("⚠ No .env file found. Make sure BENCHLING_API_KEY and BENCHLING_DOMAIN are set.")
    
    # Get credentials from environment
    api_key = os.getenv("BENCHLING_API_KEY")
    domain = os.getenv("BENCHLING_DOMAIN")
    
    if not api_key or not domain:
        print("❌ Missing credentials. Please check your .env file or environment variables.")
        print("Required: BENCHLING_API_KEY and BENCHLING_DOMAIN")
        return
    
    print(f"🔧 Connecting to Benchling at {domain}...")
    
    # Initialize the Benchling client
    mcp = BenchlingMCP(api_key=api_key, domain=domain)
    
    try:
        # Get some entries from Benchling
        print("📝 Fetching notebook entries...")
        result = await mcp.get_entries(limit=5)
        
        if result.success:
            print(f"✅ Found {result.count} entries")
            
            # Print details of each entry
            if result.data:
                for i, entry in enumerate(result.data, 1):
                    print(f"\n  Entry {i}:")
                    print(f"    Name: {entry.name}")
                    print(f"    ID: {entry.id}")
                    if hasattr(entry, 'created_at'):
                        print(f"    Created: {entry.created_at}")
                    if hasattr(entry, 'creator') and entry.creator:
                        print(f"    Creator: {entry.creator.name}")
        else:
            print(f"❌ Failed to get entries: {result.message}")
            
    except Exception as e:
        print(f"💥 Error: {e}")
        print("Check your API key and domain settings.")


if __name__ == "__main__":
    asyncio.run(main()) 