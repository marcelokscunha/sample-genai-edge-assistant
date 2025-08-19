#!/usr/bin/env python3
"""
Script to package the Janus model files into a ZIP for the web interface.
This creates a ZIP file that can be served by the model URL API.
"""

import os
import zipfile
from pathlib import Path

def package_janus_model():
    """Package the Janus model files into a ZIP file."""
    
    # Paths
    artifacts_dir = Path(__file__).parent / "ARTIFACTS_MINIMAL"
    output_zip = Path(__file__).parent / "ARTIFACTS_OUT" / "janus-pro-1b.zip"
    
    if not artifacts_dir.exists():
        print(f"Error: ARTIFACTS_MINIMAL directory not found at {artifacts_dir}")
        return False
    
    print(f"Packaging model from: {artifacts_dir}")
    print(f"Output ZIP: {output_zip}")
    
    # Create ZIP file
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from ARTIFACTS_MINIMAL directory
        for root, dirs, files in os.walk(artifacts_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate relative path from ARTIFACTS_MINIMAL directory
                relative_path = file_path.relative_to(artifacts_dir)
                
                print(f"Adding: {relative_path}")
                zipf.write(file_path, str(relative_path))
    
    print(f"Model packaged successfully: {output_zip}")
    print(f"ZIP file size: {output_zip.stat().st_size / (1024*1024):.1f} MB")
    
    return True

if __name__ == "__main__":
    success = package_janus_model()
    if not success:
        exit(1)