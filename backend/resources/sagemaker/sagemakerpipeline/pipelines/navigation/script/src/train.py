import os 
import pathlib
import shutil
import tarfile
import boto3
import logging
from pathlib import Path

from huggingface_hub import login

from inference import NavigationPipeline

# Configure logging for SageMaker training job
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        logger.info(f"Retrieving Hugging Face token from Secrets Manager: {secret_name}")
        secrets_client = boto3.client('secretsmanager')
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        token = response['SecretString']
        
        if not token or not token.strip() or not token.startswith('hf_'):
            raise ValueError("Invalid Hugging Face token format")
            
        logger.info("Successfully retrieved Hugging Face token")
        return token
        
    except Exception as e:
        logger.error(f"Failed to retrieve Hugging Face token: {str(e)}")
        raise RuntimeError("Failed to retrieve Hugging Face token from Secrets Manager")

def create_model_archive(source_dir: str | Path, output_file_path: str | Path):
    """
    Create a tar.gz archive from the source directory.
    
    Args:
        source_dir (str): Path to the source directory
        output_file_path (str): Path to the final tar.gz file
    """
    # Convert to absolute paths
    source_dir = Path(source_dir).absolute()
    output_file_path = Path(output_file_path).absolute()
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    if not source_dir.is_dir():
        raise ValueError(f"Source directory {source_dir} does not exist or is not a directory")
    
    logger.info(f"Creating model archive from {source_dir} to {output_file_path}")
    
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
                logger.debug(f"Added {arc_name} to archive")

if __name__ == "__main__":
    try:
        logger.info("Starting navigation model preparation training job")
        
        # Get Hugging Face token from Secrets Manager
        secret_name = os.environ.get("HF_TOKEN_SECRET_NAME", "huggingface-token")
        hf_token = get_hf_token_from_secrets(secret_name)
        login(hf_token)

        # Set up paths for SageMaker training job environment
        # In SageMaker training jobs, the model output should go to /opt/ml/model
        HERE = pathlib.Path(__file__).parent.absolute()
        src_dir = HERE.absolute()
        
        # Use SageMaker training job output directory
        output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        dst_content_dir = output_dir / "model"
        dst_content_dir.mkdir(parents=True, exist_ok=True)

        model_id = "google/gemma-3n-e2b-it"

        logger.info(f"Downloading and saving model {model_id}...")
        pipeline = NavigationPipeline(model_id)
        pipeline.processor.save_pretrained(dst_content_dir)
        pipeline.model.save_pretrained(dst_content_dir)
        
        # Copy inference code to model directory
        if src_dir.exists():
            shutil.copytree(src_dir, dst_content_dir / "code", dirs_exist_ok=True)
            logger.info("Copied inference code to model directory")

        logger.info(f"Creating model archive at {output_dir}/model.tar.gz")
        create_model_archive(dst_content_dir, output_file_path=output_dir/"model.tar.gz")
        
        # Verify the size of the created archive
        archive_path = output_dir / "model.tar.gz"
        if archive_path.exists():
            archive_size = archive_path.stat().st_size / (1024 * 1024)  # Size in MB
            logger.info(f"Archive created successfully! Size: {archive_size:.2f} MB")
        
        logger.info("Navigation model preparation training job completed successfully")
        
    except Exception as e:
        logger.error(f"Training job failed: {str(e)}")
        raise