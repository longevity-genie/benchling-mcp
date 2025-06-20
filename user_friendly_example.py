#!/usr/bin/env python3
"""
User-Friendly Benchling MCP Example

This example demonstrates how to use the new user-friendly methods that work with
human-readable names instead of cryptic IDs.

Features demonstrated:
1. Find project by name instead of ID
2. Find folders by name within a project
3. Upload sequences using names instead of IDs
"""

import asyncio
import os
from dotenv import load_dotenv
from benchling_mcp.server import BenchlingMCP

# Load environment variables
load_dotenv()

async def main():
    """Demonstrate user-friendly Benchling operations."""
    
    # Initialize Benchling MCP
    api_key = os.getenv("BENCHLING_API_KEY")
    domain = os.getenv("BENCHLING_DOMAIN")
    
    if not api_key or not domain:
        print("❌ Missing BENCHLING_API_KEY or BENCHLING_DOMAIN environment variables")
        return
    
    benchling_mcp = BenchlingMCP(api_key=api_key, domain=domain)
    
    print("🧬 Benchling MCP User-Friendly Demo")
    print("=" * 50)
    
    # Example 1: Find project by name
    print("\n📋 Example 1: Finding project by name...")
    project_result = await benchling_mcp.get_project_by_name("ZELAR")
    
    if project_result.success:
        project_id = project_result.data["id"]
        project_name = project_result.data["name"]
        print(f"✅ Found project '{project_name}' with ID: {project_id}")
    else:
        print(f"❌ Could not find project: {project_result.message}")
        return
    
    # Example 2: Find folders by name within the project
    print(f"\n📂 Example 2: Finding folders in '{project_name}' project...")
    
    # Look for a specific folder
    folder_result = await benchling_mcp.get_folder_by_name(
        folder_name="benchling_test",
        project_name_or_id="ZELAR"  # Using project name instead of ID!
    )
    
    if folder_result.success and folder_result.data:
        folder_id = folder_result.data[0]["id"]
        folder_name = folder_result.data[0]["name"]
        print(f"✅ Found folder '{folder_name}' with ID: {folder_id}")
    else:
        print(f"📁 No 'benchling_test' folder found: {folder_result.message}")
        print("   You could create one using create_folder() method")
    
    # Example 3: Get sequences from project using name
    print(f"\n🧬 Example 3: Getting DNA sequences from '{project_name}' project...")
    
    sequences_result = await benchling_mcp.get_dna_sequences(
        project_id=project_id,  # We got this from the name lookup above
        limit=5
    )
    
    if sequences_result.success and sequences_result.data:
        print(f"✅ Found {sequences_result.count} sequences:")
        for i, seq in enumerate(sequences_result.data[:3]):  # Show first 3
            seq_name = seq.get("name", "Unknown")
            seq_id = seq.get("id", "Unknown")
            seq_length = seq.get("length", "Unknown")
            print(f"   [{i+1}] '{seq_name}' (ID: {seq_id}, Length: {seq_length} bp)")
    else:
        print(f"❌ Could not get sequences: {sequences_result.message}")
    
    # Example 4: Search for sequences by name
    print(f"\n🔍 Example 4: Searching for CRISPR-related sequences...")
    
    search_result = await benchling_mcp.get_dna_sequences(
        name="CRISPR",  # Search by name
        limit=3
    )
    
    if search_result.success and search_result.data:
        print(f"✅ Found {search_result.count} CRISPR-related sequences:")
        for seq in search_result.data:
            seq_name = seq.get("name", "Unknown")
            seq_id = seq.get("id", "Unknown")
            print(f"   • '{seq_name}' (ID: {seq_id})")
    else:
        print(f"❌ No CRISPR sequences found: {search_result.message}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed! The new user-friendly methods make it much easier")
    print("   to work with Benchling using human-readable names instead of IDs.")
    print("\n📚 Available user-friendly methods:")
    print("   • get_project_by_name(project_name)")
    print("   • get_folder_by_name(folder_name, project_name_or_id)")
    print("   • All existing methods can use the resolved IDs")

if __name__ == "__main__":
    asyncio.run(main()) 