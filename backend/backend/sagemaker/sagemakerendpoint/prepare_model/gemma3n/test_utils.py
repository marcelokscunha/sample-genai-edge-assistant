import base64
import os
import tarfile
from pathlib import Path


def get_base64_from_image(image_path: str) -> str:
    with open(image_path, 'rb') as img_file:
        b64_bytes = base64.b64encode(img_file.read())
        b64_str = b64_bytes.decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_str}"
    return data_uri


def create_model_archive(source_dir: str | Path, output_file_path: str | Path):
    """
    Create a tar.gz archive from the source directory.
    
    Args:
        source_dir (str): Path to the source directory (ARTIFACTS)
        output_file_path (str): Path to the final tar.gz file (e.g. output_file_path="ARTIFACTS/model.tar.gz")
    """
    # Convert to absolute paths
    source_dir = Path(source_dir).absolute()
    output_file_path = Path(output_file_path).absolute()

    if not source_dir.is_dir():
        raise ValueError(f"Source directory {source_dir} does not exist or is not a directory")
    
    # Create the tar.gz file
    with tarfile.open(output_file_path, "w:gz") as tar:
        # Walk through all files and directories
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                # Get the full path of the file
                file_path = Path(root) / file
                # Get the relative path for the archive
                arc_name = file_path.relative_to(source_dir)
                # Add the file to the archive
                tar.add(file_path, arcname=arc_name)
                print(f"Added {arc_name} to archive")
