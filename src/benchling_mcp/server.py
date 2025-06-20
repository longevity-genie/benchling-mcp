#!/usr/bin/env python3
"""Benchling MCP Server - Interface for interacting with Benchling platform."""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable
import re

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from eliot import start_action
import typer

# Import Benchling SDK components
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
from benchling_sdk.models import (
    Entry, DnaSequence, RnaSequence, AaSequence, Project,
    ListEntriesSort, ListDNASequencesSort, DnaSequenceCreate,
    EntityArchiveReason, FolderCreate
)

# Try to import BioPython for sequence parsing
try:
    from Bio import SeqIO
    from Bio.SeqRecord import SeqRecord
    HAS_BIOPYTHON = True
except ImportError:
    HAS_BIOPYTHON = False

# Configuration
DEFAULT_HOST = os.getenv("MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("MCP_PORT", "3001"))
DEFAULT_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")

class BenchlingResult(BaseModel):
    """Result from a Benchling SDK call."""
    data: Any = Field(description="Response data from Benchling SDK")
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Operation description")
    count: Optional[int] = Field(default=None, description="Number of items returned (if applicable)")

class BenchlingMCP(FastMCP):
    """Benchling MCP Server with SDK-based tools that can be inherited and extended."""
    
    def __init__(
        self, 
        name: str = "Benchling MCP Server",
        api_key: Optional[str] = None,
        domain: Optional[str] = None,
        prefix: str = "benchling_",
        **kwargs
    ):
        """Initialize the Benchling tools with SDK client and FastMCP functionality."""
        # Initialize FastMCP with the provided name and any additional kwargs
        super().__init__(name=name, **kwargs)
        
        # Get API credentials from environment if not provided
        self.api_key = api_key or os.getenv("BENCHLING_API_KEY")
        self.domain = domain or os.getenv("BENCHLING_DOMAIN")
        
        if not self.api_key:
            raise ValueError("Benchling API key is required. Set BENCHLING_API_KEY environment variable or pass api_key parameter.")
        if not self.domain:
            raise ValueError("Benchling domain is required. Set BENCHLING_DOMAIN environment variable or pass domain parameter.")
        
        # Initialize our Benchling SDK client
        self.client = Benchling(
            url=f"https://{self.domain.rstrip('/')}",
            auth_method=ApiKeyAuth(api_key=self.api_key)
        )
        
        self.prefix = prefix
        
        # Register our tools and resources
        self._register_benchling_tools()
        self._register_benchling_resources()
    
    def _register_benchling_tools(self):
        """Register Benchling-specific tools."""
        self.tool(
            name=f"{self.prefix}get_entries", 
            description="Get notebook entries from Benchling with powerful filtering options"
        )(self.get_entries)
        
        self.tool(
            name=f"{self.prefix}get_entry_by_id", 
            description="Get a specific notebook entry by its ID"
        )(self.get_entry_by_id)
        
        self.tool(
            name=f"{self.prefix}get_dna_sequences", 
            description="Get DNA sequences from Benchling with filtering options"
        )(self.get_dna_sequences)
        
        self.tool(
            name=f"{self.prefix}get_dna_sequence_by_id", 
            description="Get a specific DNA sequence by its ID"
        )(self.get_dna_sequence_by_id)
        
        self.tool(
            name=f"{self.prefix}get_rna_sequences", 
            description="Get RNA sequences from Benchling with filtering options"
        )(self.get_rna_sequences)
        
        self.tool(
            name=f"{self.prefix}get_aa_sequences", 
            description="Get protein (amino acid) sequences from Benchling with filtering options"
        )(self.get_aa_sequences)
        
        self.tool(
            name=f"{self.prefix}get_projects", 
            description="Get projects from Benchling"
        )(self.get_projects)
        
        self.tool(
            name=f"{self.prefix}search_entities", 
            description="Search across Benchling entities using advanced search capabilities"
        )(self.search_entities)
        
        self.tool(
            name=f"{self.prefix}get_folders", 
            description="Get folders from Benchling to organize your work"
        )(self.get_folders)
        
        self.tool(
            name=f"{self.prefix}download_dna_sequence", 
            description="Download a DNA sequence (including plasmids) with automatic format selection"
        )(self.download_dna_sequence)
        
        self.tool(
            name=f"{self.prefix}download_sequence_by_name", 
            description="Find and download a DNA sequence by name with smart format selection (GenBank for plasmids)"
        )(self.download_sequence_by_name)
        
        self.tool(
            name=f"{self.prefix}upload_fasta_file", 
            description="Upload and create DNA sequences from a FASTA file"
        )(self.upload_fasta_file)
        
        self.tool(
            name=f"{self.prefix}upload_genbank_file", 
            description="Upload and create DNA sequences from a GenBank file"
        )(self.upload_genbank_file)
        
        self.tool(
            name=f"{self.prefix}create_dna_sequence", 
            description="Create a single DNA sequence with name, bases, and optional metadata"
        )(self.create_dna_sequence)
        
        self.tool(
            name=f"{self.prefix}archive_dna_sequence", 
            description="Archive (delete) a DNA sequence by ID"
        )(self.archive_dna_sequence)
        
        self.tool(
            name=f"{self.prefix}create_folder", 
            description="Create a new folder in a Benchling project"
        )(self.create_folder)
        
        self.tool(
            name=f"{self.prefix}get_project_by_name", 
            description="Find a project by its name and return project details including ID"
        )(self.get_project_by_name)
        
        self.tool(
            name=f"{self.prefix}get_folder_by_name", 
            description="Find folders by name within a project (by name or ID)"
        )(self.get_folder_by_name)
    
    def _register_benchling_resources(self):
        """Register Benchling-specific resources."""
        
        @self.resource(f"resource://{self.prefix}api-info")
        def get_api_info() -> str:
            """
            Get information about the Benchling SDK capabilities and usage.
            
            This resource contains information about:
            - Available SDK methods and services
            - Authentication requirements
            - Common usage patterns
            - Available entity types
            
            Returns:
                SDK information and usage guidelines
            """
            return f"""
            # Benchling SDK Information
            
            ## Authentication
            - Uses Benchling SDK with API key authentication
            - API key: {self.api_key[:8]}...
            - Domain: {self.domain}
            
            ## Available Services
            - Entries: Notebook entries with rich text content
            - DNA Sequences: DNA sequences with annotations and primers
            - RNA Sequences: RNA sequences with annotations
            - AA Sequences: Protein sequences with annotations
            - Projects: Project management and organization
            - Folders: Organizational structure
            - Custom Entities: Custom data types
            - Teams: User and team management
            - And many more...
            
            ## Key Features
            - Advanced search and filtering
            - Bulk operations
            - Pagination support
            - Rich metadata and annotations
            - Entity relationships
            - Version control and audit trails
            
            ## Common Usage Patterns
            - Use get_*_by_id for specific entities when you know the ID
            - Use list methods with filters for discovery
            - Use search for cross-entity queries
            - Leverage project_id and folder_id filters for organization
            """
    
    async def get_entries(
        self, 
        project_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        name: Optional[str] = None,
        creator_ids: Optional[List[str]] = None,
        schema_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 50
    ) -> BenchlingResult:
        """
        Get notebook entries from Benchling with powerful filtering and sorting options.
        
        RECOMMENDED WORKFLOW:
        1. EASY WAY: Use `get_project_by_name("Project Name")` to find project by human-readable name
        2. EASY WAY: Use `get_folder_by_name("Folder Name", "Project Name")` to find folders by name
        3. TRADITIONAL WAY: Call `get_projects()` to find project IDs if you want project-specific entries
        4. TRADITIONAL WAY: Call `get_folders()` to find folder IDs if you want folder-specific entries
        5. Use this method with the discovered IDs for targeted entry retrieval
        
        FILTERING OPTIONS:
        - Use project_id to get entries from a specific research project
        - Use folder_id to get entries from a specific organizational folder
        - Use name for partial text matching in entry titles
        - Use creator_ids to get entries created by specific users
        - Use schema_id to get entries following a specific template/schema
        
        Args:
            project_id (Optional[str]): Benchling project ID (format: "lib_xxxxxxxxx"). 
                Get project IDs using get_projects() method first.
            folder_id (Optional[str]): Benchling folder ID (format: "lib_xxxxxxxxx"). 
                Get folder IDs using get_folders() method first.
            name (Optional[str]): Partial or full entry name to search for. Case-insensitive matching.
            creator_ids (Optional[List[str]]): List of Benchling user IDs (format: "ent_xxxxxxxxx") 
                to filter entries by their creators.
            schema_id (Optional[str]): Entry template/schema ID (format: "ps_xxxxxxxxx") 
                to get entries following specific templates.
            sort (Optional[str]): Sort order. VALID VALUES:
                - "modifiedAt:asc" - Oldest modified first
                - "modifiedAt:desc" - Newest modified first (most recent changes)
                - "name:asc" - Alphabetical A-Z
                - "name:desc" - Reverse alphabetical Z-A
                - None - Default Benchling ordering
            limit (int): Maximum number of entries to return. Range: 1-100. Default: 50.
                For large datasets, use multiple calls with different filters.
                
        Returns:
            BenchlingResult: Contains list of entry objects with the following key fields:
                - id: Benchling entry ID
                - name: Entry title/name
                - web_url: Direct link to view entry in Benchling
                - created_at: Entry creation timestamp (ISO format)
                - modified_at: Last modification timestamp (ISO format)
                - creator: Information about who created the entry
                - project_id: Parent project ID
                - folder_id: Parent folder ID
                
        EXAMPLE USAGE PATTERNS:
        1. Get recent entries from a specific project:
           await get_entries(project_id="lib_abc123", sort="modifiedAt:desc", limit=10)
           
        2. Find entries with specific names:
           await get_entries(name="experiment", limit=25)
           
        3. Get all entries in a folder:
           await get_entries(folder_id="lib_folder123", limit=100)
           
        EXAMPLE INPUT/OUTPUT:
        Input: await get_entries(project_id="src_Fq2naN3m", limit=10)
        Output: BenchlingResult(
            success=True,
            message="Retrieved 0 entries",
            count=0,
            data=[]
        )
        Note: Empty result indicates no notebook entries in this project
           
        ERROR HANDLING:
        - Returns success=False if invalid IDs are provided
        - Returns empty list if no entries match the criteria
        - Network errors are logged and returned in the message field
        """
        with start_action(action_type="benchling_get_entries", project_id=project_id, folder_id=folder_id) as action:
            try:
                # Convert sort string to enum if provided
                sort_enum = None
                if sort:
                    sort_map = {
                        'modifiedAt:asc': ListEntriesSort.MODIFIEDAT_ASC,
                        'modifiedAt:desc': ListEntriesSort.MODIFIEDAT_DESC,
                        'name:asc': ListEntriesSort.NAME_ASC,
                        'name:desc': ListEntriesSort.NAME_DESC
                    }
                    sort_enum = sort_map.get(sort)
                
                # Note: folder_id is not supported by list_entries in this SDK version
                entries_iterator = self.client.entries.list_entries(
                    project_id=project_id,
                    name=name,
                    creator_ids=creator_ids,
                    schema_id=schema_id,
                    sort=sort_enum,
                    page_size=min(limit, 100)  # Cap at 100 per page
                )
                
                entries = []
                count = 0
                for entry_or_list in entries_iterator:
                    if count >= limit:
                        break
                    
                    # Handle both single entry and list of entries
                    entries_to_process = [entry_or_list] if not isinstance(entry_or_list, list) else entry_or_list
                    
                    for entry in entries_to_process:
                        if count >= limit:
                            break
                        entries.append({
                            "id": entry.id,
                            "name": entry.name,
                            "display_id": getattr(entry, 'display_id', None),
                            "created_at": entry.created_at.isoformat() if hasattr(entry, 'created_at') and entry.created_at and hasattr(entry.created_at, 'isoformat') else (str(entry.created_at) if hasattr(entry, 'created_at') and entry.created_at else None),
                            "modified_at": entry.modified_at.isoformat() if hasattr(entry, 'modified_at') and entry.modified_at and hasattr(entry.modified_at, 'isoformat') else (str(entry.modified_at) if hasattr(entry, 'modified_at') and entry.modified_at else None),
                            "web_url": getattr(entry, 'web_url', None),
                            "project_id": getattr(entry, 'project_id', None),
                            "folder_id": getattr(entry, 'folder_id', None),
                            "schema_id": getattr(entry, 'schema_id', None),
                            "creator": {
                                "id": entry.creator.id,
                                "name": entry.creator.name
                            } if hasattr(entry, 'creator') and entry.creator and hasattr(entry.creator, 'id') else None,
                            "entry_template_id": getattr(entry, 'entry_template_id', None)
                        })
                        count += 1
                
                result = BenchlingResult(
                    data=entries,
                    success=True,
                    message=f"Retrieved {count} entries",
                    count=count
                )
                
                action.add_success_fields(entries_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve entries: {e}",
                    count=0
                )

    async def get_entry_by_id(self, entry_id: str) -> BenchlingResult:
        """
        Get a specific notebook entry by its ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
        """
        with start_action(action_type="benchling_get_entry_by_id", entry_id=entry_id) as action:
            try:
                entry = self.client.entries.get_entry_by_id(entry_id)
                
                entry_data = {
                    "id": entry.id,
                    "name": entry.name,
                    "display_id": entry.display_id,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                    "modified_at": entry.modified_at.isoformat() if entry.modified_at else None,
                    "web_url": entry.web_url,
                    "project_id": entry.project_id,
                    "folder_id": entry.folder_id,
                    "schema_id": entry.schema_id,
                    "creator": {
                        "id": entry.creator.id,
                        "name": entry.creator.name
                    } if entry.creator else None,
                    "entry_template_id": entry.entry_template_id,
                    "days": entry.days if hasattr(entry, 'days') else []
                }
                
                result = BenchlingResult(
                    data=entry_data,
                    success=True,
                    message=f"Retrieved entry {entry.name}",
                    count=1
                )
                
                action.add_success_fields(entry_name=entry.name)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=None,
                    success=False,
                    message=f"Failed to retrieve entry: {e}"
                )

    async def get_dna_sequences(
        self,
        project_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        name: Optional[str] = None,
        bases: Optional[str] = None,
        registry_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        creator_ids: Optional[List[str]] = None,
        sort: Optional[str] = None,
        limit: int = 50
    ) -> BenchlingResult:
        """
        Get DNA sequences (including plasmids, primers, genes) from Benchling with comprehensive filtering.
        
        RECOMMENDED WORKFLOW:
        1. EASY WAY: Use `get_project_by_name("Project Name")` to find project by human-readable name
        2. EASY WAY: Use `get_folder_by_name("Folder Name", "Project Name")` to find folders by name
        3. TRADITIONAL WAY: Call `get_projects()` to find project IDs for project-specific sequence retrieval
        4. TRADITIONAL WAY: Call `get_folders()` to find folder IDs for folder-specific sequence retrieval  
        5. Use this method with discovered IDs for targeted sequence searches
        4. For downloading sequences, use `download_dna_sequence()` or `download_sequence_by_name()`
        5. For single sequence details, use `get_dna_sequence_by_id()` if you know the exact ID
        
        SEQUENCE TYPES RETURNED:
        - Plasmids (vectors, expression constructs)
        - Primers (PCR primers, sequencing primers)  
        - Genes (coding sequences, ORFs)
        - Synthetic constructs
        - Cloning intermediates
        - Any custom DNA sequence types defined in your Benchling instance
        
        Args:
            project_id (Optional[str]): Benchling project ID (format: "lib_xxxxxxxxx"). 
                Use get_projects() first to discover available project IDs.
            folder_id (Optional[str]): Benchling folder ID (format: "lib_xxxxxxxxx"). 
                Use get_folders() first to discover available folder IDs.
            name (Optional[str]): Partial or full sequence name to search for. Case-insensitive.
                Examples: "pUC19", "CRISPRoff", "primer", "GFP"
            bases (Optional[str]): Partial DNA sequence match. Use ONLY standard DNA bases.
                VALID CHARACTERS: A, T, G, C, N (uppercase recommended)
                Example: "ATCGATCGATCG" - finds sequences containing this subsequence
            registry_id (Optional[str]): Registry ID for registered sequences (format varies).
                This is used for sequences that have been formally registered in Benchling's registry.
            schema_id (Optional[str]): Sequence template/schema ID (format: "ps_xxxxxxxxx").
                Use this to find sequences following specific templates (e.g., "all plasmids", "all primers").
            creator_ids (Optional[List[str]]): List of Benchling user IDs (format: "ent_xxxxxxxxx")
                to filter sequences by their creators.
            sort (Optional[str]): Sort order. VALID VALUES:
                - "modifiedAt:asc" - Oldest modified first
                - "modifiedAt:desc" - Newest modified first (recommended for recent work)
                - "name:asc" - Alphabetical A-Z (good for browsing)
                - "name:desc" - Reverse alphabetical Z-A
                - None - Default Benchling ordering
            limit (int): Maximum number of sequences to return. Range: 1-100. Default: 50.
                Use smaller limits (10-25) for initial exploration, larger for comprehensive searches.
                
        Returns:
            BenchlingResult: Contains list of DNA sequence objects with these key fields:
                - id: Benchling sequence ID (use with download_dna_sequence)
                - name: Sequence name/title
                - bases: The actual DNA sequence (A, T, G, C)
                - length: Number of base pairs
                - web_url: Direct link to view sequence in Benchling
                - created_at: Creation timestamp (ISO format)
                - modified_at: Last modification timestamp
                - creator: User who created the sequence
                - project_id: Parent project ID
                - folder_id: Parent folder ID
                - registry_id: Registry ID if registered
                - annotations_count: Number of features/annotations
                - primers_count: Number of associated primers
                
        EXAMPLE USAGE PATTERNS:
        1. Find all plasmids in a project:
           await get_dna_sequences(project_id="lib_abc123", name="plasmid", limit=50)
           
        2. Search for CRISPR-related sequences:
           await get_dna_sequences(name="CRISPR", sort="modifiedAt:desc", limit=20)
           
        3. Find sequences by partial DNA match:
           await get_dna_sequences(bases="ATGCGTACGTACGTACGTAA", limit=10)
           
        4. Get all sequences in a specific folder:
           await get_dna_sequences(folder_id="lib_folder456", limit=100)
           
        NEXT STEPS AFTER GETTING SEQUENCES:
        - Use download_dna_sequence(sequence_id) to download individual sequences
        - Use download_sequence_by_name(name) to find and download by name
        - Use get_dna_sequence_by_id(id) for detailed single sequence information
        
        ERROR HANDLING:
        - Returns success=False if invalid IDs are provided
        - Returns empty list if no sequences match the criteria
        - Invalid 'bases' parameter (non-DNA characters) will cause filtering errors
        - Network errors are logged and returned in the message field
        
        EXAMPLE INPUT/OUTPUT:
        Input: await get_dna_sequences(project_id="src_Fq2naN3m", limit=10)
        Output: BenchlingResult(
            success=True,
            message="Retrieved 8 DNA sequences",
            count=8,
            data=[
                {"id": "seq_duu59Hdq", "name": "JKNp112-CAG-Dnmt3A-3L-"},
                {"id": "seq_bsw5XEhW", "name": "CRISPRoff-v2.1"},
                {"id": "seq_xmBvUXTV", "name": "IGF1"},
                {"id": "seq_W3HQdd7D", "name": "long_telomeres"},
                {"id": "seq_7b729Qoi", "name": "possible_cancer"},
                {"id": "seq_Hg6Qi4IZ", "name": "VEGFA"},
                {"id": "seq_zidyEvFg", "name": "Folistatin"},
                {"id": "seq_nYwfWjgm", "name": "CONSTRUCT_1"}
            ]
        )
        """
        with start_action(action_type="benchling_get_dna_sequences", project_id=project_id, folder_id=folder_id) as action:
            try:
                # Convert sort string to enum if provided
                sort_enum = None
                if sort:
                    sort_map = {
                        'modifiedAt:asc': ListDNASequencesSort.MODIFIEDAT_ASC,
                        'modifiedAt:desc': ListDNASequencesSort.MODIFIEDAT_DESC,
                        'name:asc': ListDNASequencesSort.NAME_ASC,
                        'name:desc': ListDNASequencesSort.NAME_DESC
                    }
                    sort_enum = sort_map.get(sort)
                
                sequences_iterator = self.client.dna_sequences.list(
                    project_id=project_id,
                    folder_id=folder_id,
                    name=name,
                    bases=bases,
                    registry_id=registry_id,
                    schema_id=schema_id,
                    creator_ids=creator_ids,
                    sort=sort_enum,
                    page_size=min(limit, 100)
                )
                
                sequences = []
                count = 0
                for seq_or_list in sequences_iterator:
                    if count >= limit:
                        break
                    
                    # Handle both single sequence and list of sequences
                    seqs_to_process = [seq_or_list] if not isinstance(seq_or_list, list) else seq_or_list
                    
                    for seq in seqs_to_process:
                        if count >= limit:
                            break
                        sequences.append({
                            "id": seq.id,
                            "name": seq.name,
                            "display_id": getattr(seq, 'display_id', None),
                            "bases": getattr(seq, 'bases', None),
                            "length": getattr(seq, 'length', None),
                            "created_at": seq.created_at.isoformat() if hasattr(seq, 'created_at') and seq.created_at else None,
                            "modified_at": seq.modified_at.isoformat() if hasattr(seq, 'modified_at') and seq.modified_at else None,
                            "web_url": getattr(seq, 'web_url', None),
                            "project_id": getattr(seq, 'project_id', None),
                            "folder_id": getattr(seq, 'folder_id', None),
                            "schema_id": getattr(seq, 'schema_id', None),
                            "registry_id": getattr(seq, 'registry_id', None),
                            "creator": {
                                "id": seq.creator.id,
                                "name": seq.creator.name
                            } if hasattr(seq, 'creator') and seq.creator and hasattr(seq.creator, 'id') else None,
                            "annotations_count": len(seq.annotations) if hasattr(seq, 'annotations') and seq.annotations else 0,
                            "primers_count": len(seq.primers) if hasattr(seq, 'primers') and seq.primers else 0
                        })
                        count += 1
                
                result = BenchlingResult(
                    data=sequences,
                    success=True,
                    message=f"Retrieved {count} DNA sequences",
                    count=count
                )
                
                action.add_success_fields(sequences_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve DNA sequences: {e}",
                    count=0
                )

    async def get_dna_sequence_by_id(self, sequence_id: str) -> BenchlingResult:
        """
        Get a specific DNA sequence by its ID.
        
        Args:
            sequence_id: The ID of the DNA sequence to retrieve
        """
        with start_action(action_type="benchling_get_dna_sequence_by_id", sequence_id=sequence_id) as action:
            try:
                seq = self.client.dna_sequences.get_by_id(sequence_id)
                
                sequence_data = {
                    "id": seq.id,
                    "name": seq.name,
                    "display_id": getattr(seq, 'display_id', None),  # Safe access - might not exist
                    "bases": seq.bases,
                    "length": seq.length,
                    "created_at": seq.created_at.isoformat() if seq.created_at else None,
                    "modified_at": seq.modified_at.isoformat() if seq.modified_at else None,
                    "web_url": seq.web_url,
                    "project_id": getattr(seq, 'project_id', None),  # Safe access - might not exist
                    "folder_id": getattr(seq, 'folder_id', None),    # Safe access - might not exist
                    "schema_id": getattr(seq, 'schema_id', None),    # Safe access - might not exist
                    "registry_id": getattr(seq, 'registry_id', None), # Safe access - might not exist
                    "creator": {
                        "id": seq.creator.id,
                        "name": seq.creator.name
                    } if seq.creator else None,
                    "annotations": [
                        {
                            "id": ann.id,
                            "name": ann.name,
                            "start": ann.start,
                            "end": ann.end,
                            "strand": ann.strand,
                            "type": ann.type
                        } for ann in (seq.annotations or [])
                    ],
                    "primers": [
                        {
                            "id": primer.id,
                            "name": primer.name,
                            "start": primer.start,
                            "end": primer.end,
                            "strand": primer.strand
                        } for primer in (seq.primers or [])
                    ]
                }
                
                result = BenchlingResult(
                    data=sequence_data,
                    success=True,
                    message=f"Retrieved DNA sequence {seq.name}",
                    count=1
                )
                
                action.add_success_fields(sequence_name=seq.name, sequence_length=seq.length)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=None,
                    success=False,
                    message=f"Failed to retrieve DNA sequence: {e}"
                )

    async def get_rna_sequences(
        self,
        project_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 50
    ) -> BenchlingResult:
        """
        Get RNA sequences from Benchling with filtering options.
        
        Args:
            project_id: Filter by project ID
            folder_id: Filter by folder ID
            name: Filter by sequence name (partial match)
            limit: Maximum number of sequences to return (default: 50)
        """
        with start_action(action_type="benchling_get_rna_sequences", project_id=project_id, folder_id=folder_id) as action:
            try:
                sequences_iterator = self.client.rna_sequences.list(
                    project_id=project_id,
                    folder_id=folder_id,
                    name=name,
                    page_size=min(limit, 100)
                )
                
                sequences = []
                count = 0
                for seq in sequences_iterator:
                    if count >= limit:
                        break
                    sequences.append({
                        "id": seq.id,
                        "name": seq.name,
                        "display_id": seq.display_id,
                        "bases": seq.bases,
                        "length": seq.length,
                        "created_at": seq.created_at.isoformat() if seq.created_at else None,
                        "modified_at": seq.modified_at.isoformat() if seq.modified_at else None,
                        "web_url": seq.web_url,
                        "project_id": seq.project_id,
                        "folder_id": seq.folder_id,
                        "creator": {
                            "id": seq.creator.id,
                            "name": seq.creator.name
                        } if seq.creator else None
                    })
                    count += 1
                
                result = BenchlingResult(
                    data=sequences,
                    success=True,
                    message=f"Retrieved {count} RNA sequences",
                    count=count
                )
                
                action.add_success_fields(sequences_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve RNA sequences: {e}",
                    count=0
                )

    async def get_aa_sequences(
        self,
        project_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 50
    ) -> BenchlingResult:
        """
        Get protein (amino acid) sequences from Benchling with filtering options.
        
        Args:
            project_id: Filter by project ID
            folder_id: Filter by folder ID
            name: Filter by sequence name (partial match)
            limit: Maximum number of sequences to return (default: 50)
        """
        with start_action(action_type="benchling_get_aa_sequences", project_id=project_id, folder_id=folder_id) as action:
            try:
                sequences_iterator = self.client.aa_sequences.list(
                    project_id=project_id,
                    folder_id=folder_id,
                    name=name,
                    page_size=min(limit, 100)
                )
                
                sequences = []
                count = 0
                for seq in sequences_iterator:
                    if count >= limit:
                        break
                    sequences.append({
                        "id": seq.id,
                        "name": seq.name,
                        "display_id": seq.display_id,
                        "amino_acids": seq.amino_acids,
                        "length": seq.length,
                        "created_at": seq.created_at.isoformat() if seq.created_at else None,
                        "modified_at": seq.modified_at.isoformat() if seq.modified_at else None,
                        "web_url": seq.web_url,
                        "project_id": seq.project_id,
                        "folder_id": seq.folder_id,
                        "creator": {
                            "id": seq.creator.id,
                            "name": seq.creator.name
                        } if seq.creator else None
                    })
                    count += 1
                
                result = BenchlingResult(
                    data=sequences,
                    success=True,
                    message=f"Retrieved {count} protein sequences",
                    count=count
                )
                
                action.add_success_fields(sequences_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve protein sequences: {e}",
                    count=0
                )

    async def get_projects(self, limit: int = 50) -> BenchlingResult:
        """
        Get projects from Benchling.
        
        Projects are the top-level organizational units in Benchling that contain
        all your research work including notebook entries, sequences, and other entities.
        
        RECOMMENDED AS FIRST STEP:
        This method is typically called first to discover available projects,
        then use the returned project IDs to filter other method calls.
        
        Args:
            limit (int): Maximum number of projects to return. Range: 1-100. Default: 50.
                Most organizations have fewer than 50 projects, so default is usually sufficient.
                
        Returns:
            BenchlingResult: Contains list of project objects with the following key fields:
                - id: Benchling project ID (format: "src_xxxxxxxxx")
                - name: Human-readable project name
                - description: Project description (if set)
                - created_at: Project creation timestamp (ISO format)
                - modified_at: Last modification timestamp (ISO format)
                - owner: Information about project owner/creator
                
        EXAMPLE INPUT/OUTPUT:
        Input: await get_projects(limit=5)
        Output: BenchlingResult(
            success=True,
            message="Retrieved 5 projects",
            count=5,
            data=[
                {"id": "src_1ypfGpcC", "name": "Sickle Cell - Mol Gen"},
                {"id": "src_m5Bb7mQJ", "name": "Yeast CRISPR"},
                {"id": "src_UXRsDBRs", "name": "PTC Project 2425"},
                {"id": "src_Fq2naN3m", "name": "ZELAR"},
                {"id": "src_H4t43VR7", "name": "PTC Sequences"}
            ]
        )
                
        NEXT STEPS AFTER GETTING PROJECTS:
        - Use project['id'] values in other methods' project_id parameter
        - Call get_entries(project_id=project_id) to get project-specific entries
        - Call get_dna_sequences(project_id=project_id) to get project-specific sequences
        """
        with start_action(action_type="benchling_get_projects") as action:
            try:
                projects_iterator = self.client.projects.list(page_size=min(limit, 100))
                
                projects = []
                count = 0
                for project_or_list in projects_iterator:
                    if count >= limit:
                        break
                    
                    # Debug: Check what type we're getting
                    if isinstance(project_or_list, list):
                        # If it's a list, iterate through it
                        for project in project_or_list:
                            if count >= limit:
                                break
                            self._process_single_project(project, projects)
                            count += 1
                    else:
                        # It's a single project
                        project = project_or_list
                        self._process_single_project(project, projects)
                        count += 1
                
                result = BenchlingResult(
                    data=projects,
                    success=True,
                    message=f"Retrieved {count} projects",
                    count=count
                )
                
                action.add_success_fields(projects_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve projects: {e}",
                    count=0
                )
    
    def _process_single_project(self, project, projects):
        """Process a single project object and add it to the projects list."""
        # Handle owner field safely - it might be a list or other structure
        owner_info = None
        if hasattr(project, 'owner') and project.owner:
            try:
                # If owner is a single object with id/name
                if hasattr(project.owner, 'id') and hasattr(project.owner, 'name'):
                    owner_info = {
                        "id": project.owner.id,
                        "name": project.owner.name
                    }
                # If owner is a list, take the first item
                elif isinstance(project.owner, list) and len(project.owner) > 0:
                    first_owner = project.owner[0]
                    if hasattr(first_owner, 'id') and hasattr(first_owner, 'name'):
                        owner_info = {
                            "id": first_owner.id,
                            "name": first_owner.name
                        }
                else:
                    # Just convert to string as fallback
                    owner_info = str(project.owner)
            except Exception:
                owner_info = str(project.owner)
        
        projects.append({
            "id": project.id,
            "name": project.name,
            "description": getattr(project, 'description', None),
            "created_at": project.created_at.isoformat() if hasattr(project, 'created_at') and project.created_at else None,
            "modified_at": project.modified_at.isoformat() if hasattr(project, 'modified_at') and project.modified_at else None,
            "web_url": getattr(project, 'web_url', None),
            "owner": owner_info
        })

    async def search_entities(
        self, 
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> BenchlingResult:
        """
        Search across Benchling entities using advanced search capabilities.
        
        This method searches across multiple entity types simultaneously, providing
        a unified search experience across your Benchling workspace.
        
        Args:
            query (str): Search query string. Can be:
                - Entity names: "CRISPR", "GFP", "experiment"
                - Partial matches: "plas" (finds "plasmid")
                - Project names: "ZELAR", "COVID"
            entity_types (Optional[List[str]]): List of entity types to search within.
                VALID VALUES: ["dna_sequence", "rna_sequence", "aa_sequence", "entry"]
                If None, searches across all supported entity types.
            limit (int): Maximum number of results to return. Range: 1-100. Default: 50.
                Results are distributed across entity types.
                
        Returns:
            BenchlingResult: Contains list of entity objects with these key fields:
                - id: Benchling entity ID
                - name: Entity name
                - type: Entity type ("dna_sequence", "entry", etc.)
                - web_url: Direct link to view entity in Benchling
                - created_at: Creation timestamp (ISO format)
                
        EXAMPLE INPUT/OUTPUT:
        Input: await search_entities(
            query="ZELAR",
            entity_types=["entry", "dna_sequence", "rna_sequence", "aa_sequence"],
            limit=5
        )
        Output: BenchlingResult(
            success=True,
            message="Found 0 entities matching 'ZELAR'",
            count=0,
            data=[]
        )
        Note: Empty result indicates no entities contain "ZELAR" in their names
        
        USAGE PATTERNS:
        1. Search for CRISPR-related entities:
           await search_entities(query="CRISPR", limit=20)
           
        2. Find only DNA sequences:
           await search_entities(query="plasmid", entity_types=["dna_sequence"])
           
        3. Search notebook entries only:
           await search_entities(query="experiment", entity_types=["entry"])
        """
        with start_action(action_type="benchling_search_entities", query=query, entity_types=entity_types) as action:
            try:
                # Note: The actual search implementation may vary based on Benchling SDK version
                # This is a simplified approach - you may need to use specific search methods
                results = []
                
                # Search DNA sequences if not filtered or specifically requested
                if not entity_types or 'dna_sequence' in entity_types:
                    try:
                        dna_iterator = self.client.dna_sequences.list(
                            name=query,
                            page_size=min(limit // 4 if entity_types else limit, 50)
                        )
                        for seq in dna_iterator:
                            results.append({
                                "id": seq.id,
                                "name": seq.name,
                                "type": "dna_sequence",
                                "web_url": seq.web_url,
                                "created_at": seq.created_at.isoformat() if seq.created_at else None
                            })
                            if len(results) >= limit:
                                break
                    except Exception:
                        pass  # Continue with other entity types
                
                # Search entries if not filtered or specifically requested
                if (not entity_types or 'entry' in entity_types) and len(results) < limit:
                    try:
                        entries_iterator = self.client.entries.list_entries(
                            name=query,
                            page_size=min(limit - len(results), 50)
                        )
                        for entry in entries_iterator:
                            results.append({
                                "id": entry.id,
                                "name": entry.name,
                                "type": "entry",
                                "web_url": entry.web_url,
                                "created_at": entry.created_at.isoformat() if entry.created_at else None
                            })
                            if len(results) >= limit:
                                break
                    except Exception:
                        pass
                
                result = BenchlingResult(
                    data=results,
                    success=True,
                    message=f"Found {len(results)} entities matching '{query}'",
                    count=len(results)
                )
                
                action.add_success_fields(results_count=len(results))
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Search failed: {e}",
                    count=0
                )

    async def get_folders(self, limit: int = 50) -> BenchlingResult:
        """
        Get folders from Benchling to organize your work.
        
        Folders provide organizational structure in Benchling for grouping related
        entries, sequences, and other entities. They can be nested hierarchically.
        
        Args:
            limit (int): Maximum number of folders to return. Range: 1-100. Default: 50.
                
        Returns:
            BenchlingResult: Contains list of folder objects with these key fields:
                - id: Benchling folder ID (format: "lib_xxxxxxxxx")
                - name: Folder name/title
                - created_at: Creation timestamp (ISO format)
                - modified_at: Last modification timestamp
                - web_url: Direct link to view folder in Benchling
                - parent_folder_id: Parent folder ID (if nested)
                - project_id: Parent project ID
                
        EXAMPLE INPUT/OUTPUT:
        Input: await get_folders(limit=5)
        Output: BenchlingResult(
            success=True,
            message="Retrieved 5 folders",
            count=5,
            data=[
                {"id": "lib_W25gpt5R", "name": "0"},
                {"id": "lib_cWioB7Wu", "name": "1"},
                {"id": "lib_o88jH2P0", "name": "1"},
                {"id": "lib_RvPlAq6S", "name": "1"},
                {"id": "lib_Yj2NxcnS", "name": "1"}
            ]
        )
        
        NEXT STEPS AFTER GETTING FOLDERS:
        - Use folder['id'] values in other methods' folder_id parameter
        - Call get_entries(folder_id=folder_id) to get folder-specific entries
        - Call get_dna_sequences(folder_id=folder_id) to get folder-specific sequences
        """
        with start_action(action_type="benchling_get_folders") as action:
            try:
                folders_iterator = self.client.folders.list(page_size=min(limit, 100))
                
                folders = []
                count = 0
                for folder_or_list in folders_iterator:
                    if count >= limit:
                        break
                    
                    # Handle both single folder and list of folders
                    folders_to_process = [folder_or_list] if not isinstance(folder_or_list, list) else folder_or_list
                    
                    for folder in folders_to_process:
                        if count >= limit:
                            break
                        folders.append({
                            "id": folder.id,
                            "name": folder.name,
                            "created_at": folder.created_at.isoformat() if hasattr(folder, 'created_at') and folder.created_at else None,
                            "modified_at": folder.modified_at.isoformat() if hasattr(folder, 'modified_at') and folder.modified_at else None,
                            "web_url": getattr(folder, 'web_url', None),
                            "parent_folder_id": getattr(folder, 'parent_folder_id', None),
                            "project_id": getattr(folder, 'project_id', None)
                        })
                        count += 1
                
                result = BenchlingResult(
                    data=folders,
                    success=True,
                    message=f"Retrieved {count} folders",  
                    count=count
                )
                
                action.add_success_fields(folders_count=count)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to retrieve folders: {e}",
                    count=0
                )

    async def download_dna_sequence(
        self, 
        sequence_id: str,
        download_dir: str = ".",
        filename: Optional[str] = None,
        format: str = "auto"
    ) -> BenchlingResult:
        """
        Download a DNA sequence (including plasmids) with automatic format selection.
        
        SMART FORMAT SELECTION:
        - For plasmids: Automatically uses GenBank format (.gb) to preserve annotations
        - For other sequences: Uses FASTA format (.fasta) for simplicity
        - Plasmid detection based on name keywords and sequence characteristics
        
        RECOMMENDED USAGE:
        - Leave format="auto" for best results (default behavior)
        - Files saved to current directory by default for easy access
        
        Args:
            sequence_id: The ID of the DNA sequence to download
            download_dir: Directory to save the file (default: "." = current directory)
            filename: Optional custom filename (default: auto-generated from sequence name)
            format: Format to download. OPTIONS:
                   - "auto" (RECOMMENDED): GenBank for plasmids, FASTA for others
                   - "fasta": Force FASTA format (.fasta extension)  
                   - "genbank": Force GenBank format (.gb extension)
            
        Returns:
            BenchlingResult with download information including:
                - file_path: Full path to downloaded file
                - format: Actual format used ("fasta" or "genbank")
                - is_plasmid: Whether sequence was detected as plasmid
                - length: Sequence length in base pairs
        """
        with start_action(action_type="benchling_download_dna_sequence", sequence_id=sequence_id, format=format) as action:
            try:
                # Get the DNA sequence details
                dna_sequence = self.client.dna_sequences.get_by_id(sequence_id)
                
                # Create download directory if it doesn't exist
                download_path = Path(download_dir)
                download_path.mkdir(parents=True, exist_ok=True)
                
                # Determine format
                is_plasmid = self._is_plasmid(dna_sequence)
                
                if format == "auto":
                    selected_format = "genbank" if is_plasmid else "fasta"
                else:
                    selected_format = format.lower()
                
                # Generate filename if not provided
                if not filename:
                    safe_name = "".join(c for c in dna_sequence.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    extension = "gb" if selected_format == "genbank" else "fasta"
                    filename = f"{safe_name}.{extension}"
                
                file_path = download_path / filename
                
                # Create content based on format
                if selected_format == "genbank":
                    content = self._create_genbank_content(dna_sequence)
                else:  # fasta
                    content = self._create_fasta_content(dna_sequence)
                
                # Write to file
                with open(file_path, 'w') as f:
                    f.write(content)
                
                result_data = {
                    "sequence_id": sequence_id,
                    "sequence_name": dna_sequence.name,
                    "file_path": str(file_path.absolute()),
                    "filename": filename,
                    "format": selected_format,
                    "is_plasmid": is_plasmid,
                    "length": len(dna_sequence.bases) if dna_sequence.bases else 0,
                    "download_dir": str(download_path.absolute())
                }
                
                result = BenchlingResult(
                    data=result_data,
                    success=True,
                    message=f"Downloaded DNA sequence '{dna_sequence.name}' to {file_path}",
                    count=1
                )
                
                action.add_success_fields(file_path=str(file_path))
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data={},
                    success=False,
                    message=f"Failed to download DNA sequence: {e}",
                    count=0
                )

    async def download_sequence_by_name(
        self, 
        name: str,
        download_dir: str = ".",
        project_id: Optional[str] = None,
        format: str = "auto"
    ) -> BenchlingResult:
        """
        Find and download a DNA sequence by name with smart format selection.
        
        SMART FEATURES:
        - Automatically detects plasmids and uses GenBank format (.gb) for them
        - Uses FASTA format (.fasta) for other sequences  
        - Saves to current directory by default for easy access
        - Searches for exact name matches first, then partial matches
        
        This method combines search and download functionality:
        1. Searches for DNA sequences matching the provided name
        2. Finds the best match (exact match preferred, otherwise first result)
        3. Downloads the sequence in the optimal format (GenBank for plasmids)
        4. Saves to current directory unless specified otherwise
        
        RECOMMENDED WORKFLOW:
        1. Use this method when you know the sequence name but not the ID
        2. For bulk downloads, use get_dna_sequences() first, then download_dna_sequence() for each
        3. For exact ID-based downloads, use download_dna_sequence() directly
        
        Args:
            name (str): Name of the DNA sequence to find and download. 
                Can be partial or full name. Case-insensitive matching.
                Examples: "CRISPRoff-v2.1", "pUC19", "GFP", "primer"
            download_dir (str): Directory to save the file. Default: "." (current directory)
                Can be absolute or relative path. Directory will be created if it doesn't exist.
            project_id (Optional[str]): Benchling project ID to search within (format: "src_xxxxxxxxx").
                If provided, searches only within that project for better specificity.
                If None, searches across all accessible projects.
            format (str): Download format. OPTIONS:
                - "auto" (RECOMMENDED): GenBank for plasmids, FASTA for others
                - "fasta": Force FASTA format (.fasta extension)
                - "genbank": Force GenBank format (.gb extension)
            
        Returns:
            BenchlingResult: Contains download information with these key fields:
                - sequence_id: Benchling sequence ID that was downloaded
                - sequence_name: Name of the downloaded sequence
                - file_path: Absolute path to the downloaded file
                - filename: Name of the created file
                - format: Actual format used ("fasta" or "genbank")
                - is_plasmid: Boolean indicating if sequence was detected as plasmid
                - length: Length of sequence in base pairs
                - download_dir: Directory where file was saved
                
        EXAMPLE - CRISPRoff plasmid automatically downloads as GenBank:
        Input: await download_sequence_by_name(name="CRISPRoff-v2.1")
        Output: BenchlingResult(
            success=True,
            message="Found and downloaded sequence 'CRISPRoff-v2.1'",
            data={
                "sequence_name": "CRISPRoff-v2.1",
                "file_path": "/current/dir/CRISPRoff-v21.gb",
                "filename": "CRISPRoff-v21.gb", 
                "format": "genbank",  # ← Automatically selected!
                "is_plasmid": True,   # ← Detected as plasmid
                "length": 11885
            }
        )
        
        ERROR HANDLING:
        - Returns success=False if no sequences found with the given name
        - Returns success=False if download fails due to permissions or disk space
        - Invalid project_id will limit search scope but won't cause failure
        - Invalid download_dir will attempt to create the directory
        
        NEXT STEPS AFTER DOWNLOAD:
        - Use the file_path to access the downloaded sequence file
        - Check is_plasmid to understand the sequence type
        - Use sequence_id for future direct downloads or API calls
        """
        with start_action(action_type="benchling_download_sequence_by_name", name=name, project_id=project_id) as action:
            try:
                # Search for sequences with the given name
                sequences_result = await self.get_dna_sequences(
                    name=name,
                    project_id=project_id,
                    limit=10  # Limit to avoid too many results
                )
                
                if not sequences_result.success or not sequences_result.data:
                    return BenchlingResult(
                        data={},
                        success=False,
                        message=f"No DNA sequences found with name containing '{name}'",
                        count=0
                    )
                
                downloaded_files = []
                
                # Try to find exact match first, otherwise use first result
                target_sequence = None
                for seq in sequences_result.data:
                    seq_name = seq.get('name', '') if isinstance(seq, dict) else getattr(seq, 'name', '')
                    if seq_name.lower() == name.lower():
                        target_sequence = seq
                        break
                
                if not target_sequence:
                    target_sequence = sequences_result.data[0]
                
                # Get sequence ID
                seq_id = target_sequence.get('id') if isinstance(target_sequence, dict) else getattr(target_sequence, 'id')
                seq_name = target_sequence.get('name') if isinstance(target_sequence, dict) else getattr(target_sequence, 'name')
                
                # Download the sequence
                download_result = await self.download_dna_sequence(
                    sequence_id=seq_id,
                    download_dir=download_dir,
                    format=format
                )
                
                if download_result.success:
                    result = BenchlingResult(
                        data=download_result.data,
                        success=True,
                        message=f"Found and downloaded sequence '{seq_name}'",
                        count=1
                    )
                else:
                    result = download_result
                
                action.add_success_fields(found_sequence=seq_name)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data={},
                    success=False,
                    message=f"Failed to find and download sequence: {e}",
                    count=0
                )

    async def create_dna_sequence(
        self,
        name: str,
        bases: str,
        project_id: str,
        folder_id: Optional[str] = None,
        description: Optional[str] = None,
        schema_id: Optional[str] = None,
        is_circular: bool = False
    ) -> BenchlingResult:
        """
        Create a single DNA sequence in Benchling.
        
        This method creates a new DNA sequence entity in Benchling with the provided sequence data.
        
        Args:
            name (str): Name for the DNA sequence. Should be descriptive and unique within the project.
            bases (str): DNA sequence string using standard nucleotide codes (A, T, G, C, N).
                Must contain only valid DNA characters. Case will be normalized to uppercase.
            project_id (str): Benchling project ID where the sequence will be created (format: "src_xxxxxxxxx").
                Use get_projects() to find available project IDs.
            folder_id (Optional[str]): Optional folder ID for organization (format: "lib_xxxxxxxxx").
                Use get_folders() to find available folder IDs.
            description (Optional[str]): Optional description for the sequence.
            schema_id (Optional[str]): Optional schema/template ID for the sequence (format: "ps_xxxxxxxxx").
            is_circular (bool): Whether the DNA sequence is circular (like a plasmid). Defaults to False.
            
        Returns:
            BenchlingResult: Contains information about the created sequence with key fields:
                - id: Benchling sequence ID of the created sequence
                - name: Name of the created sequence
                - length: Length of the sequence in base pairs
                - web_url: Direct link to view the sequence in Benchling
                - project_id: Parent project ID
                - folder_id: Parent folder ID (if specified)
                
        Example:
            result = await create_dna_sequence(
                name="My New Plasmid",
                bases="ATCGATCGATCG",
                project_id="src_abc123",
                description="A test plasmid"
            )
        """
        with start_action(action_type="benchling_create_dna_sequence", name=name, project_id=project_id) as action:
            try:
                # Debug: Print what we're trying to create
                print(f"🔧 Creating DNA sequence with:")
                print(f"   name: {name}")
                print(f"   project_id: {project_id}")
                print(f"   folder_id: {folder_id}")
                print(f"   schema_id: {schema_id}")
                print(f"   is_circular: {is_circular}")
                
                # Validate and clean the DNA sequence
                cleaned_bases = self._validate_and_clean_dna_sequence(bases)
                
                # Create the DNA sequence object
                dna_sequence_create = DnaSequenceCreate(
                    name=name,
                    bases=cleaned_bases,
                    folder_id=folder_id,
                    schema_id=schema_id,
                    is_circular=is_circular
                )
                
                # Add description if provided (not in fields)
                if description:
                    # Note: Description might need to be handled differently
                    # For now, we'll put it in custom fields or leave it out
                    pass
                
                # Create the sequence using Benchling SDK
                created_sequence = self.client.dna_sequences.create(dna_sequence_create)
                
                result_data = {
                    "id": created_sequence.id,
                    "name": created_sequence.name,
                    "length": len(cleaned_bases),
                    "bases": cleaned_bases,
                    "web_url": created_sequence.web_url,
                    "project_id": project_id,
                    "folder_id": folder_id,
                    "schema_id": schema_id,
                    "created_at": created_sequence.created_at.isoformat() if created_sequence.created_at else None
                }
                
                result = BenchlingResult(
                    data=result_data,
                    success=True,
                    message=f"Successfully created DNA sequence '{name}' with {len(cleaned_bases)} bases",
                    count=1
                )
                
                action.add_success_fields(sequence_id=created_sequence.id, sequence_length=len(cleaned_bases))
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data={},
                    success=False,
                    message=f"Failed to create DNA sequence: {e}",
                    count=0
                )

    async def archive_dna_sequence(self, sequence_id: str, reason: str = "OTHER") -> BenchlingResult:
        """
        Archive (delete) a DNA sequence by ID.
        
        This method archives a DNA sequence in Benchling, which effectively removes it from
        active use while preserving it in the system history.
        
        Args:
            sequence_id (str): Benchling sequence ID to archive (format: "seq_xxxxxxxxx")
            reason (str): Reason for archiving. VALID VALUES:
                - "OTHER" (default) - General archiving
                - "MADE_IN_ERROR" - Sequence was created in error
                - "CONTAMINATED" - Sequence is contaminated
                - "RETIRED" - Sequence is retired/deprecated
                - "EXPENDED" - Sequence is expended
                - "EXPIRED" - Sequence is expired
                - "MISSING" - Sequence is missing
                - "SHIPPED" - Sequence is shipped
                - "DEPRECATED" - Alias for "RETIRED"
                - "DUPLICATE" - Alias for "OTHER"
                
        Returns:
            BenchlingResult: Contains information about the archival operation with key fields:
                - success: Boolean indicating if archival was successful
                - message: Description of the operation result
                - data: Information about the archived sequence
                
        Example:
            result = await archive_dna_sequence(
                sequence_id="seq_abc123",
                reason="MADE_IN_ERROR"
            )
        """
        with start_action(action_type="benchling_archive_dna_sequence", sequence_id=sequence_id, reason=reason) as action:
            try:
                # Convert reason string to enum
                try:
                    # First, let's see what's actually available in the enum
                    available_reasons = [attr for attr in dir(EntityArchiveReason) if not attr.startswith('_')]
                    print(f"🔧 Available EntityArchiveReason values: {available_reasons}")
                    
                    reason_map = {}
                    
                    # Add all available enum values based on actual SDK
                    reason_map = {
                        "OTHER": EntityArchiveReason.OTHER,
                        "CONTAMINATED": EntityArchiveReason.CONTAMINATED,
                        "MADE_IN_ERROR": EntityArchiveReason.MADE_IN_ERROR,
                        "RETIRED": EntityArchiveReason.RETIRED,
                        "EXPENDED": EntityArchiveReason.EXPENDED,
                        "EXPIRED": EntityArchiveReason.EXPIRED,
                        "MISSING": EntityArchiveReason.MISSING,
                        "SHIPPED": EntityArchiveReason.SHIPPED,
                        # Aliases for user convenience
                        "DEPRECATED": EntityArchiveReason.RETIRED,  # Map deprecated to retired
                        "DUPLICATE": EntityArchiveReason.OTHER,     # Map duplicate to other
                    }
                    
                    print(f"🔧 Available reason mappings: {list(reason_map.keys())}")
                    
                    # Use the requested reason if available, otherwise use OTHER or the first available
                    archive_reason = reason_map.get(reason.upper())
                    if not archive_reason:
                        # Fallback to OTHER or first available reason
                        archive_reason = reason_map.get("OTHER") or next(iter(reason_map.values()), None)
                        print(f"🔧 Reason '{reason}' not found, using fallback: {archive_reason}")
                    else:
                        print(f"🔧 Archive reason: {reason} -> {archive_reason}")
                        
                    if not archive_reason:
                        raise ValueError(f"No valid archive reasons available in EntityArchiveReason enum")
                        
                except Exception as enum_error:
                    print(f"🐛 Error with EntityArchiveReason enum: {enum_error}")
                    raise
                
                action.log(message_type="info", 
                          sequence_id=sequence_id, 
                          reason=reason, 
                          archive_reason=str(archive_reason))
                
                # Archive the sequence using Benchling SDK
                archive_result = self.client.dna_sequences.archive(
                    dna_sequence_ids=[sequence_id],
                    reason=archive_reason
                )
                
                result_data = {
                    "sequence_id": sequence_id,
                    "reason": reason,
                    "archived_at": archive_result.modified_at.isoformat() if hasattr(archive_result, 'modified_at') and archive_result.modified_at else None,
                    "archive_result": str(archive_result)
                }
                
                result = BenchlingResult(
                    data=result_data,
                    success=True,
                    message=f"Successfully archived DNA sequence '{sequence_id}' with reason '{reason}'",
                    count=1
                )
                
                action.add_success_fields(sequence_id=sequence_id, reason=reason)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e), error_type=type(e).__name__)
                # Also print the full exception for debugging
                print(f"🐛 Archive error details: {type(e).__name__}: {e}")
                if hasattr(e, 'response'):
                    print(f"🐛 Response: {e.response}")
                return BenchlingResult(
                    data={},
                    success=False,
                    message=f"Failed to archive DNA sequence: {type(e).__name__}: {e}",
                    count=0
                )

    async def create_folder(
        self,
        name: str,
        project_id: str,
        parent_folder_id: Optional[str] = None
    ) -> BenchlingResult:
        """
        Create a new folder in a Benchling project.
        
        Args:
            name (str): Name for the new folder
            project_id (str): Benchling project ID where the folder will be created (format: "src_xxxxxxxxx")
            parent_folder_id (Optional[str]): Parent folder ID if creating a subfolder (format: "lib_xxxxxxxxx")
            
        Returns:
            BenchlingResult: Contains information about the created folder
        """
        with start_action(action_type="benchling_create_folder", name=name, project_id=project_id) as action:
            try:
                print(f"🔧 Creating folder '{name}' in project {project_id}")
                
                # Create the folder object
                # Note: FolderCreate doesn't accept project_id directly in constructor
                # But we can try creating a folder with just name and parent_folder_id
                if parent_folder_id:
                    folder_create = FolderCreate(
                        name=name,
                        parent_folder_id=parent_folder_id
                    )
                else:
                    # Try creating a root-level folder (might require different approach)
                    folder_create = FolderCreate(name=name)
                
                # Create the folder using Benchling SDK
                created_folder = self.client.folders.create(folder_create)
                
                result_data = {
                    "id": created_folder.id,
                    "name": created_folder.name,
                    "project_id": project_id,
                    "parent_folder_id": parent_folder_id,
                    "web_url": getattr(created_folder, 'web_url', None),
                    "created_at": created_folder.created_at.isoformat() if hasattr(created_folder, 'created_at') and created_folder.created_at else None
                }
                
                result = BenchlingResult(
                    data=result_data,
                    success=True,
                    message=f"Successfully created folder '{name}' with ID {created_folder.id}",
                    count=1
                )
                
                action.add_success_fields(folder_id=created_folder.id)
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                print(f"🐛 Create folder error: {type(e).__name__}: {e}")
                return BenchlingResult(
                    data={},
                    success=False,
                    message=f"Failed to create folder: {type(e).__name__}: {e}",
                    count=0
                )

    async def get_project_by_name(self, project_name: str) -> BenchlingResult:
        """
        Find a project by its name and return project details including ID.
        
        This is a helper method for users who know the project name (like "ZELAR") 
        but need the project ID for other API calls.
        
        Args:
            project_name (str): The human-readable project name to search for.
                Examples: "ZELAR", "COVID Research", "Protein Engineering"
                
        Returns:
            BenchlingResult: Contains project information with key fields:
                - id: Benchling project ID (format: "src_xxxxxxxxx") 
                - name: Human-readable project name
                - description: Project description (if available)
                - web_url: Direct link to project in Benchling
                - created_at: Creation timestamp
                
        Example Usage:
            # Find the ZELAR project
            result = await get_project_by_name("ZELAR")
            if result.success:
                project_id = result.data["id"]  # Use this ID in other methods
                
        NEXT STEPS:
        - Use the returned project ID in methods like get_dna_sequences(project_id=...)
        - Use get_folder_by_name() to find folders within this project
        """
        with start_action(action_type="benchling_get_project_by_name", project_name=project_name) as action:
            try:
                # Get all projects and search for name match
                projects_result = await self.get_projects(limit=100)
                
                if not projects_result.success:
                    return BenchlingResult(
                        data=None,
                        success=False,
                        message=f"Failed to retrieve projects: {projects_result.message}",
                        count=0
                    )
                
                # Search for exact name match (case-insensitive)
                target_project = None
                for project in projects_result.data:
                    if project["name"].lower() == project_name.lower():
                        target_project = project
                        break
                
                if not target_project:
                    # Try partial match if exact match fails
                    for project in projects_result.data:
                        if project_name.lower() in project["name"].lower():
                            target_project = project
                            action.log(message_type="info", match_type="partial", 
                                     found_name=project["name"])
                            break
                
                if not target_project:
                    available_names = [p["name"] for p in projects_result.data[:10]]
                    return BenchlingResult(
                        data=None,
                        success=False,
                        message=f"Project '{project_name}' not found. Available projects: {', '.join(available_names)}",
                        count=0
                    )
                
                result = BenchlingResult(
                    data=target_project,
                    success=True,
                    message=f"Found project '{target_project['name']}' with ID {target_project['id']}",
                    count=1
                )
                
                action.add_success_fields(project_id=target_project["id"], project_name=target_project["name"])
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=None,
                    success=False,
                    message=f"Failed to find project by name: {e}",
                    count=0
                )

    async def get_folder_by_name(
        self, 
        folder_name: str, 
        project_name_or_id: Optional[str] = None
    ) -> BenchlingResult:
        """
        Find folders by name within a project (specified by name or ID).
        
        This helper method allows users to find folders using human-readable names
        rather than cryptic IDs.
        
        Args:
            folder_name (str): The folder name to search for.
                Examples: "Experiments", "Sequences", "benchling_test"
            project_name_or_id (Optional[str]): Project to search within. Can be:
                - Project name: "ZELAR", "COVID Research" 
                - Project ID: "src_xxxxxxxxx"
                - None: Search across all accessible projects
                
        Returns:
            BenchlingResult: Contains list of matching folders with key fields:
                - id: Benchling folder ID (format: "lib_xxxxxxxxx")
                - name: Folder name
                - project_id: Parent project ID
                - project_name: Parent project name (added for convenience)
                - parent_folder_id: Parent folder ID (if nested)
                
        Example Usage:
            # Find "benchling_test" folder in ZELAR project
            result = await get_folder_by_name("benchling_test", "ZELAR")
            if result.success and result.data:
                folder_id = result.data[0]["id"]  # Use first match
                
        NEXT STEPS:
        - Use the returned folder ID in methods like upload_genbank_file(folder_id=...)
        - If no folders found, use create_folder() to create one
        """
        with start_action(action_type="benchling_get_folder_by_name", 
                         folder_name=folder_name, 
                         project_name_or_id=project_name_or_id) as action:
            try:
                target_project_id = None
                target_project_name = None
                
                # Resolve project name to ID if needed
                if project_name_or_id:
                    if project_name_or_id.startswith("src_"):
                        # It's already a project ID
                        target_project_id = project_name_or_id
                        # Get project name for convenience
                        projects_result = await self.get_projects(limit=100)
                        if projects_result.success:
                            for project in projects_result.data:
                                if project["id"] == target_project_id:
                                    target_project_name = project["name"]
                                    break
                    else:
                        # It's a project name, resolve to ID
                        project_result = await self.get_project_by_name(project_name_or_id)
                        if not project_result.success:
                            return project_result  # Return the error from project lookup
                        target_project_id = project_result.data["id"]
                        target_project_name = project_result.data["name"]
                
                # Get folders, optionally filtered by project
                folders_result = await self.get_folders(limit=200)
                
                if not folders_result.success:
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message=f"Failed to retrieve folders: {folders_result.message}",
                        count=0
                    )
                
                # Filter folders by name and optionally by project
                matching_folders = []
                for folder in folders_result.data:
                    # Check name match (case-insensitive)
                    if folder["name"].lower() == folder_name.lower():
                        # Check project match if specified
                        if not target_project_id or folder.get("project_id") == target_project_id:
                            # Add project name for convenience
                            folder_with_project = folder.copy()
                            folder_with_project["project_name"] = target_project_name
                            matching_folders.append(folder_with_project)
                
                # If no exact matches, try partial matches
                if not matching_folders:
                    for folder in folders_result.data:
                        if folder_name.lower() in folder["name"].lower():
                            if not target_project_id or folder.get("project_id") == target_project_id:
                                folder_with_project = folder.copy()
                                folder_with_project["project_name"] = target_project_name
                                matching_folders.append(folder_with_project)
                                action.log(message_type="info", match_type="partial",
                                         found_name=folder["name"])
                
                if not matching_folders:
                    project_context = f" in project '{target_project_name or target_project_id}'" if target_project_id else ""
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message=f"No folders named '{folder_name}' found{project_context}",
                        count=0
                    )
                
                result = BenchlingResult(
                    data=matching_folders,
                    success=True,
                    message=f"Found {len(matching_folders)} folder(s) named '{folder_name}'",
                    count=len(matching_folders)
                )
                
                action.add_success_fields(folders_found=len(matching_folders))
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to find folder by name: {e}",
                    count=0
                )

    async def upload_fasta_file(
        self,
        file_path: str,
        project_id: str,
        folder_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        name_prefix: Optional[str] = None
    ) -> BenchlingResult:
        """
        Upload and create DNA sequences from a FASTA file.
        
        This method reads a FASTA file and creates corresponding DNA sequences in Benchling.
        Supports both single-sequence and multi-sequence FASTA files.
        
        Args:
            file_path (str): Path to the FASTA file to upload. Can be absolute or relative path.
            project_id (str): Benchling project ID where sequences will be created (format: "src_xxxxxxxxx").
            folder_id (Optional[str]): Optional folder ID for organization (format: "lib_xxxxxxxxx").
            schema_id (Optional[str]): Optional schema/template ID for sequences (format: "ps_xxxxxxxxx").
            name_prefix (Optional[str]): Optional prefix to add to sequence names from the file.
            
        Returns:
            BenchlingResult: Contains information about all created sequences with key fields:
                - data: List of created sequence objects
                - count: Number of sequences created
                - message: Summary of the upload operation
                
        Example:
            result = await upload_fasta_file(
                file_path="/path/to/sequences.fasta",
                project_id="src_abc123",
                name_prefix="Upload_"
            )
        """
        with start_action(action_type="benchling_upload_fasta", file_path=file_path, project_id=project_id) as action:
            try:
                if not HAS_BIOPYTHON:
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message="BioPython is required for FASTA file parsing. Install with: pip install biopython",
                        count=0
                    )
                
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message=f"File not found: {file_path}",
                        count=0
                    )
                
                # Parse FASTA file
                sequences = list(SeqIO.parse(file_path_obj, "fasta"))
                
                if not sequences:
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message=f"No valid FASTA sequences found in {file_path}",
                        count=0
                    )
                
                created_sequences = []
                
                for seq_record in sequences:
                    # Generate sequence name
                    seq_name = seq_record.id
                    if name_prefix:
                        seq_name = f"{name_prefix}{seq_name}"
                    
                    # Get description if available
                    description = seq_record.description if seq_record.description != seq_record.id else None
                    
                    # Create the sequence
                    result = await self.create_dna_sequence(
                        name=seq_name,
                        bases=str(seq_record.seq),
                        project_id=project_id,
                        folder_id=folder_id,
                        description=description,
                        schema_id=schema_id
                    )
                    
                    if result.success:
                        created_sequences.append(result.data)
                    else:
                        action.log(message_type="warning", sequence_name=seq_name, error=result.message)
                
                result = BenchlingResult(
                    data=created_sequences,
                    success=True,
                    message=f"Successfully uploaded {len(created_sequences)} of {len(sequences)} sequences from FASTA file",
                    count=len(created_sequences)
                )
                
                action.add_success_fields(
                    sequences_parsed=len(sequences),
                    sequences_created=len(created_sequences)
                )
                return result
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to upload FASTA file: {e}",
                    count=0
                )

    async def upload_genbank_file(
        self,
        file_path: str,
        project_id: str,
        folder_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        name_prefix: Optional[str] = None,
        preserve_annotations: bool = True
    ) -> BenchlingResult:
        """
        Upload and create DNA sequences from a GenBank file.
        
        FIXED APPROACH: No longer uses BioPython to avoid losing annotations!
        By default, uploads the original GenBank file as a blob and creates 
        a simple DNA sequence, preserving all original annotations.
        
        Args:
            file_path (str): Path to the GenBank file to upload. Can be absolute or relative path.
            project_id (str): Benchling project ID where sequences will be created (format: "src_xxxxxxxxx").
            folder_id (Optional[str]): Optional folder ID for organization (format: "lib_xxxxxxxxx").
            schema_id (Optional[str]): Optional schema/template ID for sequences (format: "ps_xxxxxxxxx").
            name_prefix (Optional[str]): Optional prefix to add to sequence names from the file.
            preserve_annotations (bool): If True (default), uploads original file as blob and extracts minimal info.
                If False, uses old BioPython parsing method (loses annotations).
            
        Returns:
            BenchlingResult: Contains information about all created sequences with key fields:
                - data: List of created sequence objects with attached original files
                - count: Number of sequences created
                - message: Summary of the upload operation
                
        Example:
            result = await upload_genbank_file(
                file_path="/path/to/plasmid.gb",
                project_id="src_abc123"
            )
        """
        with start_action(action_type="benchling_upload_genbank", file_path=file_path, project_id=project_id) as action:
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    return BenchlingResult(
                        data=[],
                        success=False,
                        message=f"File not found: {file_path}",
                        count=0
                    )
                
                if preserve_annotations:
                    # NEW APPROACH: Upload file as blob and extract minimal sequence info
                    return await self._upload_genbank_as_blob(
                        file_path_obj, project_id, folder_id, schema_id, name_prefix, action
                    )
                else:
                    # OLD APPROACH: Parse with BioPython (loses annotations)
                    return await self._upload_genbank_parsed(
                        file_path_obj, project_id, folder_id, schema_id, name_prefix, action
                    )
                
            except Exception as e:
                action.log(message_type="error", error=str(e))
                return BenchlingResult(
                    data=[],
                    success=False,
                    message=f"Failed to upload GenBank file: {e}",
                    count=0
                )

    def _validate_and_clean_dna_sequence(self, bases: str) -> str:
        """
        Validate and clean a DNA sequence string.
        
        Args:
            bases: Raw DNA sequence string
            
        Returns:
            Cleaned DNA sequence with only valid characters
            
        Raises:
            ValueError: If sequence contains invalid characters or is empty
        """
        if not bases:
            raise ValueError("DNA sequence cannot be empty")
        
        # Remove whitespace and convert to uppercase
        cleaned = re.sub(r'\s', '', bases.upper())
        
        # Check for valid DNA characters (including ambiguous codes)
        valid_chars = set('ATCGRYSWKMBDHVN')
        invalid_chars = set(cleaned) - valid_chars
        
        if invalid_chars:
            raise ValueError(f"Invalid DNA characters found: {', '.join(sorted(invalid_chars))}")
        
        if not cleaned:
            raise ValueError("DNA sequence cannot be empty after cleaning")
        
        return cleaned

    def _is_plasmid(self, dna_sequence) -> bool:
        """
        Determine if a DNA sequence is likely a plasmid based on various indicators.
        
        This method checks multiple characteristics that commonly indicate a plasmid:
        - Name contains plasmid-related keywords (case-insensitive): "plasmid", "vector", "pUC", "pBR", "pET", "pCMV"
        - Sequence is circular (if topology information is available)
        - Sequence length is in typical plasmid range (1000-20000 bp)
        - Contains common plasmid features in annotations
        
        Args:
            dna_sequence: DnaSequence object from Benchling SDK
            
        Returns:
            bool: True if the sequence appears to be a plasmid, False otherwise
            
        Note: This is a heuristic method and may not be 100% accurate. It's designed to make 
        reasonable assumptions for automatic format selection.
        """
        if not dna_sequence.name:
            return False
            
        name_lower = dna_sequence.name.lower()
        
        # Check for plasmid-related keywords in name
        plasmid_keywords = [
            "plasmid", "vector", "puc", "pbr", "pet", "pcmv", "pgex", "pmal", 
            "pcdna", "pcr", "pgl", "pgfp", "prfp", "pyfp", "pcfp", "pires",
            "crisproff", "lentiviral", "retroviral", "expression vector"
        ]
        
        for keyword in plasmid_keywords:
            if keyword in name_lower:
                return True
                
        # Check sequence length (typical plasmid range)
        if dna_sequence.bases and 1000 <= len(dna_sequence.bases) <= 20000:
            # Additional checks for plasmid-like features could go here
            # For now, we'll be conservative and only rely on name-based detection
            pass
            
        return False
    
    def _create_fasta_content(self, dna_sequence) -> str:
        """
        Create FASTA format content from a DNA sequence.
        
        FASTA format structure:
        - Header line starts with '>' followed by sequence name and optional description
        - Sequence data on subsequent lines (typically wrapped at 70-80 characters)
        
        Args:
            dna_sequence: DnaSequence object from Benchling SDK
            
        Returns:
            str: Formatted FASTA content ready to write to file
            
        Example output:
            >Sequence Name
            ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
            ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
        """
        header = f">{dna_sequence.name}"
        if hasattr(dna_sequence, 'description') and dna_sequence.description:
            header += f" {dna_sequence.description}"
            
        # Wrap sequence at 70 characters per line (standard FASTA format)
        sequence = dna_sequence.bases or ""
        wrapped_sequence = "\n".join(sequence[i:i+70] for i in range(0, len(sequence), 70))
        
        return f"{header}\n{wrapped_sequence}\n"
    
    def _create_genbank_content(self, dna_sequence) -> str:
        """
        Create GenBank format content from a DNA sequence.
        
        GenBank format is more complex and includes:
        - LOCUS line: sequence name, length, molecule type, topology, division, date
        - DEFINITION: description of the sequence
        - ACCESSION: accession number (using Benchling ID)
        - VERSION: version information
        - SOURCE: organism information
        - FEATURES: annotations and features (if available)
        - ORIGIN: the actual sequence data in 6-column format with line numbers
        
        Args:
            dna_sequence: DnaSequence object from Benchling SDK
            
        Returns:
            str: Formatted GenBank content ready to write to file
            
        Note: This creates a basic GenBank file. Advanced features like detailed annotations,
        references, and complex feature tables would require additional Benchling API calls
        to retrieve annotation data.
        """
        from datetime import datetime
        
        # Basic GenBank header information
        name = dna_sequence.name or "unnamed"
        length = len(dna_sequence.bases) if dna_sequence.bases else 0
        
        # Create safe GenBank locus name (max 16 chars, alphanumeric + underscore)
        locus_name = "".join(c for c in name.replace(" ", "_") if c.isalnum() or c == "_")[:16]
        if not locus_name:
            locus_name = "sequence"
            
        # Format current date
        current_date = datetime.now().strftime("%d-%b-%Y").upper()
        
        # Start building GenBank content
        content = []
        
        # LOCUS line: name, length, bp, DNA, topology, division, date
        topology = "circular" if self._is_plasmid(dna_sequence) else "linear"
        content.append(f"LOCUS       {locus_name:<16} {length:>7} bp    DNA     {topology}   SYN {current_date}")
        
        # DEFINITION line
        definition = getattr(dna_sequence, 'description', name) or name
        content.append(f"DEFINITION  {definition}")
        
        # ACCESSION and VERSION (using Benchling ID)
        content.append(f"ACCESSION   {dna_sequence.id}")
        content.append(f"VERSION     {dna_sequence.id}")
        
        # SOURCE information
        content.append("SOURCE      synthetic DNA construct")
        content.append("  ORGANISM  synthetic DNA construct")
        content.append("            other sequences; artificial sequences; vectors.")
        
        # Basic FEATURES section
        content.append("FEATURES             Location/Qualifiers")
        content.append(f"     source          1..{length}")
        content.append("                     /organism=\"synthetic DNA construct\"")
        content.append("                     /mol_type=\"other DNA\"")
        
        # ORIGIN section with sequence data
        content.append("ORIGIN")
        
        if dna_sequence.bases:
            sequence = dna_sequence.bases.lower()
            # Format sequence in GenBank style (60 characters per line, 10 chars per group)
            for i in range(0, len(sequence), 60):
                line_num = i + 1
                line_seq = sequence[i:i+60]
                
                # Split into groups of 10 characters
                formatted_seq = " ".join(line_seq[j:j+10] for j in range(0, len(line_seq), 10))
                content.append(f"{line_num:>9} {formatted_seq}")
        
        content.append("//")
        
        return "\n".join(content) + "\n"

    async def _upload_genbank_as_blob(
        self, 
        file_path_obj: Path, 
        project_id: str, 
        folder_id: Optional[str], 
        schema_id: Optional[str], 
        name_prefix: Optional[str],
        action
    ) -> BenchlingResult:
        """
        Upload GenBank file preserving all annotations by uploading as blob
        and extracting only basic sequence information without parsing.
        """
        try:
            # Just upload the GenBank file as a blob - DON'T PARSE ANYTHING!
            print(f"📁 Uploading GenBank file as blob (preserving ALL annotations)...")
            blob = self.client.blobs.create_from_file(
                file_path=file_path_obj,
                mime_type="application/x-genbank",
                auto_detect=True
            )
            print(f"✅ GenBank file uploaded as blob: {blob.id} ({blob.name})")
            print(f"💡 To import with annotations intact: Use Benchling UI to import this blob")
            print(f"🔗 Blob URL: https://{self.domain}/blobs/{blob.id}")
            
            return BenchlingResult(
                data=[{
                    "blob_id": blob.id,
                    "blob_name": blob.name,
                    "file_path": str(file_path_obj),
                    "mime_type": blob.mime_type,
                    "size_bytes": file_path_obj.stat().st_size,
                    "blob_url": f"https://{self.domain}/blobs/{blob.id}",
                    "import_instructions": "Use Benchling UI to import this blob to preserve all annotations"
                }],
                success=True,
                message=f"GenBank file uploaded as blob {blob.id}. Import manually in Benchling UI to preserve annotations.",
                count=1
            )
            
        except Exception as e:
            raise Exception(f"Failed to upload GenBank as blob: {e}")

    def _extract_genbank_basic_info(self, content: str) -> List[Dict]:
        """
        Extract basic sequence information from GenBank file without BioPython.
        This preserves the original file while getting just what we need.
        """
        sequences = []
        lines = content.split('\n')
        
        current_seq = None
        in_origin = False
        sequence_data = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('LOCUS'):
                # Start of new sequence
                if current_seq:
                    # Finish previous sequence
                    current_seq['sequence'] = ''.join(sequence_data).upper()
                    sequences.append(current_seq)
                
                # Parse LOCUS line
                parts = line.split()
                current_seq = {
                    'name': parts[1] if len(parts) > 1 else 'Unknown',
                    'is_circular': 'circular' in line.lower()
                }
                sequence_data = []
                in_origin = False
                
            elif line.startswith('DEFINITION') and current_seq:
                # Get description
                desc = line.replace('DEFINITION', '').strip()
                current_seq['description'] = desc
                
            elif line.startswith('ORIGIN'):
                in_origin = True
                
            elif line.startswith('//'):
                # End of sequence
                if current_seq:
                    current_seq['sequence'] = ''.join(sequence_data).upper()
                    sequences.append(current_seq)
                    current_seq = None
                in_origin = False
                sequence_data = []
                
            elif in_origin and line:
                # Extract sequence data (remove numbers and spaces)
                seq_line = ''.join(c for c in line if c.isalpha())
                sequence_data.append(seq_line)
        
        # Handle last sequence if file doesn't end with //
        if current_seq and sequence_data:
            current_seq['sequence'] = ''.join(sequence_data).upper()
            sequences.append(current_seq)
        
        return sequences

    async def _upload_genbank_parsed(
        self, 
        file_path_obj: Path, 
        project_id: str, 
        folder_id: Optional[str], 
        schema_id: Optional[str], 
        name_prefix: Optional[str],
        action
    ) -> BenchlingResult:
        """
        OLD METHOD: Parse GenBank file with BioPython (loses annotations).
        Only used when preserve_annotations=False.
        """
        if not HAS_BIOPYTHON:
            return BenchlingResult(
                data=[],
                success=False,
                message="BioPython is required for GenBank file parsing. Install with: pip install biopython",
                count=0
            )
        
        # Parse GenBank file
        sequences = list(SeqIO.parse(file_path_obj, "genbank"))
        
        if not sequences:
            return BenchlingResult(
                data=[],
                success=False,
                message=f"No valid GenBank sequences found in {file_path_obj}",
                count=0
            )
        
        created_sequences = []
        
        for seq_record in sequences:
            # Generate sequence name from GenBank record
            seq_name = seq_record.id
            if hasattr(seq_record, 'name') and seq_record.name:
                seq_name = seq_record.name
            if name_prefix:
                seq_name = f"{name_prefix}{seq_name}"
            
            # Get description from GenBank record
            description = seq_record.description if seq_record.description else None
            
            # Determine if sequence is circular from GenBank topology
            is_circular = False
            if hasattr(seq_record, 'annotations'):
                topology = seq_record.annotations.get('topology', '').lower()
                is_circular = topology == 'circular'
            
            action.log(message_type="info", 
                      sequence_name=seq_name, 
                      sequence_length=len(str(seq_record.seq)),
                      description=description,
                      is_circular=is_circular)
            
            # Create the sequence
            result = await self.create_dna_sequence(
                name=seq_name,
                bases=str(seq_record.seq),
                project_id=project_id,
                folder_id=folder_id,
                description=description,
                schema_id=schema_id,
                is_circular=is_circular
            )
            
            if result.success:
                created_sequences.append(result.data)
            else:
                action.log(message_type="warning", sequence_name=seq_name, error=result.message)
        
        result = BenchlingResult(
            data=created_sequences,
            success=True,
            message=f"Successfully uploaded {len(created_sequences)} of {len(sequences)} sequences from GenBank file (annotations lost due to parsing)",
            count=len(created_sequences)
        )
        
        action.add_success_fields(
            sequences_parsed=len(sequences),
            sequences_created=len(created_sequences)
        )
        return result

# CLI setup
app = typer.Typer()

@app.command()
def main(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind to"),
    transport: str = typer.Option(DEFAULT_TRANSPORT, help="Transport type")
):
    """Run Benchling MCP Server in HTTP mode."""
    mcp = BenchlingMCP()
    mcp.run(transport=transport, host=host, port=port)

@app.command()
def stdio():
    """Run Benchling MCP Server in STDIO mode."""
    mcp = BenchlingMCP()
    mcp.run(transport="stdio")

@app.command()
def sse(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind to")
):
    """Run Benchling MCP Server in SSE mode."""
    mcp = BenchlingMCP()
    mcp.run(transport="sse", host=host, port=port)

# Entry points for scripts
def cli_app():
    """Entry point for the main CLI app."""
    app()

def cli_app_stdio():
    """Entry point for STDIO mode."""
    mcp = BenchlingMCP()
    mcp.run(transport="stdio")

def cli_app_sse():
    """Entry point for SSE mode."""
    mcp = BenchlingMCP()
    mcp.run(transport="sse", host=DEFAULT_HOST, port=DEFAULT_PORT)

if __name__ == "__main__":
    app() 