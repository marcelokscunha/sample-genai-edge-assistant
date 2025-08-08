import os 
import pathlib
import shutil
import tarfile
import boto3
from pathlib import Path

from huggingface_hub import login

from code.inference import NavigationPipeline

def get_hf_token_from_secrets(secret_name: str = "huggingface-token") -> str:
    """
    Retrieve Hugging Face token from AWS Secrets Manager.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        
    Returns:
        str: The Hugging Face token
        
    Raises:
        RuntimeError: If token retrieval fails
    """
    try:
        secrets_client = boto3.client('secretsmanager')
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        token = response['SecretString']
        
        if not token or not token.strip() or not token.startswith('hf_'):
            raise ValueError("Invalid Hugging Face token format")
            
        return token
        
    except Exception as e:
        raise RuntimeError("Failed to retrieve Hugging Face token from Secrets Manager")

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
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

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

# Requirements:
# - Make sure you've installed the dependencies in requirements.txt with 'pip install -r core/requirements.txt'
# - Hugging Face token will be retrieved from AWS Secrets Manager

if __name__ == "__main__":

    # Get Hugging Face token from Secrets Manager instead of .env file
    secret_name = os.environ.get("HF_TOKEN_SECRET_NAME", "huggingface-token")
    hf_token = get_hf_token_from_secrets(secret_name)
    login(hf_token)

    HERE = pathlib.Path(__file__).parent.absolute()
    code_dir = (HERE / "code").absolute()
    dst_dir = (HERE / "ARTIFACTS").absolute()
    dst_content_dir = (HERE / "ARTIFACTS" / "model").absolute()
    dst_content_code_dir = (dst_content_dir / "code").absolute()

    model_id = "google/gemma-3n-e2b-it"

    print("Downloading and saving model...")
    pipeline = NavigationPipeline(model_id)
    pipeline.processor.save_pretrained(dst_content_dir)
    pipeline.model.save_pretrained(dst_content_dir)

    print(f"Creating final '{dst_content_dir}/model.tar.gz' artifact with model and inference code...")
    create_model_archive(dst_content_dir, output_file_path = dst_dir/"package"/"model.tar.gz")
    print(f"\nArchive created successfully!")
    
    # Verify the size of the created archive
    archive_size = pathlib.Path(dst_dir/"package"/"model.tar.gz").stat().st_size / (1024 * 1024)  # Size in MB
    print(f"Archive size: {archive_size:.2f} MB")

    print("OK, now you can run some test inferences locally if wanted with 'python test_model.py'")