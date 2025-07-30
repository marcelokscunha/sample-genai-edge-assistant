
import os
import pathlib

import boto3
import sagemaker
from sagemaker.pytorch.model import PyTorchModel

from test_utils import get_base64_from_image

def deploy_model(
    role: str,
    artifacts_file: str,
    code_dir: str,
    entry_point="inference.py",
    endpoint_name: str = "gemma3n-test-endpoint",
    pytorch_version: str ="2.6.0",
    py_version: str ="py312",
    local: bool = True
):
    """
    Deploy a HuggingFace model locally using SageMaker local mode
    
    Args:
        model_data_path (str): Path to model artifacts (absolute local path or S3 URI)
        role (str): AWS IAM role ARN
        framework_version (str): HuggingFace Transformers version
        pytorch_version (str): PyTorch version
        py_version (str): Python version
        instance_type (str): Instance type (use 'local' for local mode)
    
    Returns:
        predictor: HuggingFace predictor object
    """
    if local:
        print("Configured local deployment...")
        model_data = f"file://{artifacts_file}"
        instance_type = "local_gpu"

        # Initialize SageMaker session
        sagemaker_session = sagemaker.LocalSession()
        sagemaker_session.config = {'local': {'local_code': True}}
        
    else:
        print("Configured cloud deployment...")
        instance_type = "ml.g6.xlarge"

        # Initialize SageMaker session
        sagemaker_session = sagemaker.Session()
        print("Uploading model artifact...")
        model_data = sagemaker_session.upload_data(path=artifacts_file)
        print(f"Uploaded artifact to: {model_data}")

    print("Preparing model...")
    model = PyTorchModel(
        source_dir=code_dir,
        entry_point=entry_point,
        model_data=model_data,
        role=role,
        framework_version=pytorch_version,
        py_version=py_version,
    )

    try:
        print("Deploying...")
        predictor = model.deploy(
            endpoint_name=endpoint_name,
            initial_instance_count=1,
            instance_type=instance_type,
            wait=True
        )
    
        return predictor
    
    except Exception as e:
        if local:
            print(f"Error deploying model locally (make sure Docker is enabled if in SageMaker Domain): {str(e)}")
        raise e


if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent

    # Get IAM role
    role = sagemaker.get_execution_role() if sagemaker.get_execution_role() else "arn:aws:iam::111111111111:role/service-role/AmazonSageMaker-ExecutionRole-20200101T000001"
    artifacts_file = (pathlib.Path(__file__).parent / "ARTIFACTS" / "package" / "model.tar.gz").absolute()
    code_dir = (HERE / "src").absolute()

    try:
        # Deploy the model locally
        deploy_model(
            artifacts_file=str(artifacts_file),
            code_dir=str(code_dir),
            role=role,
            local=False
        )
        
    except Exception as e:
        print(f"Error in deployment: {str(e)}")
