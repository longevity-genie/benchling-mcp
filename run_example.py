#!/usr/bin/env python3
"""
Example script to demonstrate getting data from Benchling using the MCP server.
This script shows how to:
1. Load environment variables from .env file
2. Initialize the BenchlingMCP client
3. Fetch different types of data from Benchling
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    from eliot import start_action, to_file
    import json
    # Import our Benchling MCP server
    from benchling_mcp.server import BenchlingMCP, BenchlingResult
except ImportError as e:
    print(f"❌ Missing required dependency: {e}")
    print("Please run: uv sync")
    exit(1)


def setup_logging() -> None:
    """Setup eliot logging to file."""
    log_file = Path("benchling_example.log")
    to_file(open(log_file, "w"))


# Load environment variables from .env file
load_dotenv()


def format_result(result: BenchlingResult, title: str) -> None:
    """Pretty print a Benchling result."""
    print(f"\n=== {title} ===")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.count is not None:
        print(f"Count: {result.count}")
    
    # Print names of all items
    if result.data and isinstance(result.data, list) and len(result.data) > 0:
        print("Items:")
        for i, item in enumerate(result.data):
            if isinstance(item, dict):
                name = item.get('name', 'No name')
                item_id = item.get('id', 'No ID')
                item_type = item.get('type', 'Unknown type')
                print(f"  {i+1}. {name} (ID: {item_id})")
                if 'type' in item:
                    print(f"     Type: {item_type}")
            elif hasattr(item, 'name'):
                print(f"  {i+1}. {item.name}")
                if hasattr(item, 'id'):
                    print(f"     ID: {item.id}")
            else:
                print(f"  {i+1}. {item}")
    elif result.data:
        print("Data keys:", list(result.data.keys()) if isinstance(result.data, dict) else type(result.data))


async def demonstrate_benchling_data_retrieval() -> None:
    """Demonstrate various ways to get data from Benchling."""
    
    with start_action(action_type="benchling_demo"):
        # Get required environment variables
        api_key = os.getenv("BENCHLING_API_KEY")
        domain = os.getenv("BENCHLING_DOMAIN")
        
        if not api_key or not domain:
            print("❌ Missing required environment variables!")
            print("Please check your .env file contains:")
            print("BENCHLING_API_KEY=your_api_key_here")
            print("BENCHLING_DOMAIN=your_domain_here")
            raise ValueError("Missing BENCHLING_API_KEY or BENCHLING_DOMAIN environment variables")
        
        # Initialize Benchling MCP client
        print(f"\n🔧 Initializing Benchling MCP client for {domain}...")
        mcp = BenchlingMCP(api_key=api_key, domain=domain)
        print("✓ Benchling MCP client initialized")
        
        try:
            # 1. Get projects
            print("\n📁 Fetching projects...")
            projects_result = await mcp.get_projects(limit=5)
            format_result(projects_result, "Projects")
            
            # 2. Find ZELAR project
            zelar_project_id = None
            if projects_result.success and projects_result.data:
                for project in projects_result.data:
                    if isinstance(project, dict) and project.get('name', '').upper() == 'ZELAR':
                        zelar_project_id = project.get('id')
                        print(f"\n🎯 Found ZELAR project! ID: {zelar_project_id}")
                        break
                    elif hasattr(project, 'name') and project.name.upper() == 'ZELAR':
                        zelar_project_id = project.id
                        print(f"\n🎯 Found ZELAR project! ID: {zelar_project_id}")
                        break
            
            if not zelar_project_id:
                print("\n⚠️  ZELAR project not found. Fetching general data instead...")
                
                # 3. Get general notebook entries
                print("\n📝 Fetching notebook entries...")
                entries_result = await mcp.get_entries(limit=5)
                format_result(entries_result, "Notebook Entries")
                
                # 4. Get general DNA sequences
                print("\n🧬 Fetching DNA sequences...")
                dna_result = await mcp.get_dna_sequences(limit=5)
                format_result(dna_result, "DNA Sequences")
                
                # 5. Get general folders
                print("\n📂 Fetching folders...")
                folders_result = await mcp.get_folders(limit=5)
                format_result(folders_result, "Folders")
            else:
                # 3. Get ZELAR project entries
                print(f"\n📝 Fetching notebook entries from ZELAR project...")
                entries_result = await mcp.get_entries(project_id=zelar_project_id, limit=10)
                format_result(entries_result, "ZELAR Project - Notebook Entries")
                
                # 4. Get ZELAR project DNA sequences
                print(f"\n🧬 Fetching DNA sequences from ZELAR project...")
                dna_result = await mcp.get_dna_sequences(project_id=zelar_project_id, limit=10)
                format_result(dna_result, "ZELAR Project - DNA Sequences")
                
                # 5. Get ZELAR project RNA sequences
                print(f"\n🧪 Fetching RNA sequences from ZELAR project...")
                rna_result = await mcp.get_rna_sequences(project_id=zelar_project_id, limit=10)
                format_result(rna_result, "ZELAR Project - RNA Sequences")
                
                # 6. Get ZELAR project protein sequences
                print(f"\n🧬 Fetching protein sequences from ZELAR project...")
                aa_result = await mcp.get_aa_sequences(project_id=zelar_project_id, limit=10)
                format_result(aa_result, "ZELAR Project - Protein Sequences")
                
                # 7. Search within ZELAR project
                print(f"\n🔍 Searching entities in ZELAR project...")
                search_result = await mcp.search_entities(
                    query="ZELAR", 
                    entity_types=["entry", "dna_sequence", "rna_sequence", "aa_sequence"],
                    limit=5
                )
                format_result(search_result, "ZELAR Project - Search Results")
            
            # 8. Get general folders (folders are not project-specific in the same way)
            print("\n📂 Fetching folders...")
            folders_result = await mcp.get_folders(limit=5)
            format_result(folders_result, "Folders")
            
            # 9. Download CRISPRoff-v2.1 plasmid (auto-detects format, uses current directory)
            print("\n⬇️  Attempting to download CRISPRoff-v2.1 plasmid...")
            download_result = await mcp.download_sequence_by_name(
                name="CRISPRoff-v2.1",
                project_id=zelar_project_id if zelar_project_id else None
                # download_dir defaults to current directory "."
                # format defaults to "auto" (GenBank for plasmids, FASTA for others)
            )
            
            if download_result.success:
                print(f"✅ Download successful!")
                print(f"   File path: {download_result.data.get('file_path')}")
                print(f"   Sequence name: {download_result.data.get('sequence_name')}")
                print(f"   Format: {download_result.data.get('format')}")
                print(f"   Is plasmid: {download_result.data.get('is_plasmid')}")
                print(f"   Length: {download_result.data.get('length')} bp")
            else:
                print(f"❌ Download failed: {download_result.message}")
                
                # Try alternative search terms
                print("\n🔍 Trying alternative search terms...")
                for search_term in ["CRISPRoff", "v2.1", "crisproff"]:
                    print(f"   Searching for '{search_term}'...")
                    alt_download = await mcp.download_sequence_by_name(
                        name=search_term,
                        project_id=zelar_project_id if zelar_project_id else None
                        # Uses current directory and auto-format detection
                    )
                    if alt_download.success:
                        print(f"✅ Found and downloaded: {alt_download.data.get('sequence_name')}")
                        print(f"   File path: {alt_download.data.get('file_path')}")
                        print(f"   Format: {alt_download.data.get('format')}")
                        break
                else:
                    print("   No matching sequences found with alternative terms")
            
            print("\n✅ Demo completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error during demo: {e}")
            import traceback
            traceback.print_exc()
            raise


async def main() -> None:
    """Main entry point."""
    setup_logging()
    
    print("🚀 Benchling MCP Demo")
    print("=" * 50)
    
    try:
        await demonstrate_benchling_data_retrieval()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        print("Check your .env file and Benchling credentials.")
        return


if __name__ == "__main__":
    asyncio.run(main()) 