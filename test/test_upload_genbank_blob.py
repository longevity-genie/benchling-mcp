#!/usr/bin/env python3
"""
Test GenBank file upload as blob (preserving annotations).

This test demonstrates the new approach where GenBank files are uploaded as blobs
without parsing, preserving all annotations and features intact.
"""

import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from benchling_mcp.server import BenchlingMCP

# Load environment variables
load_dotenv()

# Constants  
ZELAR_PROJECT_NAME = "ZELAR"  # The actual project name
TEST_GENBANK_FILE = "test_CRISPRoff-v21.gb"

class TestGenBankBlobUpload:
    """Test GenBank file upload as blob (preserving annotations)."""
    
    @pytest.fixture(scope="class")
    def benchling_mcp(self):
        """Create BenchlingMCP instance with API credentials."""
        api_key = os.getenv("BENCHLING_API_KEY")
        domain = os.getenv("BENCHLING_DOMAIN")
        
        if not api_key or not domain:
            pytest.skip("BENCHLING_API_KEY and BENCHLING_DOMAIN environment variables required")
        
        return BenchlingMCP(api_key=api_key, domain=domain)
    
    @pytest.fixture(scope="class")
    def genbank_file_path(self):
        """Get path to the test GenBank file."""
        test_dir = Path(__file__).parent
        genbank_path = test_dir / TEST_GENBANK_FILE
        
        if not genbank_path.exists():
            pytest.skip(f"Test GenBank file not found: {genbank_path}")
        
        return str(genbank_path)
    
    @pytest.mark.asyncio
    async def test_genbank_blob_upload(self, benchling_mcp, genbank_file_path):
        """
        Test uploading GenBank file as blob (preserving annotations).
        
        This test:
        1. Uploads GenBank file as blob without parsing
        2. Verifies blob was created successfully
        3. Provides instructions for manual import in Benchling UI
        """
        
        try:
            # Step 1: Upload GenBank file as blob
            print(f"\n🔄 Step 1: Uploading {TEST_GENBANK_FILE} as blob...")
            print(f"   💡 This preserves ALL annotations and features intact")
            print(f"   📁 File will be uploaded as blob for manual import")
            
            upload_result = await benchling_mcp.upload_genbank_file(
                file_path=genbank_file_path,
                project_id="dummy",  # Not used in blob-only mode
                preserve_annotations=True
            )
            
            # Verify upload was successful
            assert upload_result.success is True, f"Upload failed: {upload_result.message}"
            assert upload_result.count == 1, "Expected exactly 1 blob to be created"
            assert len(upload_result.data) == 1, "Expected blob data to be returned"
            
            # Get the uploaded blob info
            blob_info = upload_result.data[0]
            blob_id = blob_info["blob_id"]
            blob_name = blob_info["blob_name"]
            blob_url = blob_info.get("blob_url", "N/A")
            
            print(f"✅ Upload successful!")
            print(f"   📄 Blob Name: {blob_name}")
            print(f"   🆔 Blob ID: {blob_id}")
            print(f"   🔗 Blob URL: {blob_url}")
            print(f"   📏 File Size: {blob_info.get('size_bytes', 'Unknown')} bytes")
            
            # Step 2: Verify blob properties
            print(f"\n🔄 Step 2: Verifying blob properties...")
            
            assert blob_id is not None, "Blob ID should not be None"
            assert blob_name is not None, "Blob name should not be None"
            assert blob_info["mime_type"] == "application/x-genbank", "MIME type should be GenBank"
            assert blob_info["size_bytes"] > 0, "File size should be > 0"
            
            print(f"✅ Blob verification successful!")
            
            # Step 3: Provide import instructions
            print(f"\n🎯 Step 3: Import Instructions")
            print(f"   To import this GenBank file with ALL annotations preserved:")
            print(f"   1. Go to Benchling UI")
            print(f"   2. Navigate to your project")
            print(f"   3. Use 'Import' feature")
            print(f"   4. Select blob ID: {blob_id}")
            print(f"   5. Choose 'GenBank' format")
            print(f"   6. All annotations and features will be preserved!")
            
            print(f"\n🎉 GenBank blob upload test completed successfully!")
            print(f"   📄 Original file: {TEST_GENBANK_FILE}")
            print(f"   📦 Blob ID: {blob_id}")
            print(f"   ✨ Annotations: PRESERVED")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_genbank_file_not_found(self, benchling_mcp):
        """Test error handling when GenBank file doesn't exist."""
        
        upload_result = await benchling_mcp.upload_genbank_file(
            file_path="/nonexistent/file.gb",
            project_id="dummy",
            preserve_annotations=True
        )
        
        assert upload_result.success is False, "Upload should fail for non-existent file"
        assert "File not found" in upload_result.message, "Error message should mention file not found"
        assert upload_result.count == 0, "No blobs should be created"
        assert len(upload_result.data) == 0, "No data should be returned"
        
        print("✅ File not found error handling works correctly")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 