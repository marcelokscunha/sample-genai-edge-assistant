
import os
import pathlib

import boto3
import sagemaker
# from sagemaker.huggingface import HuggingFaceModel
from sagemaker.pytorch.model import PyTorchModel

from test_utils import get_base64_from_image

def deploy_model_locally(
    role: str,
    artifacts_file: str,
    code_dir: str,
    # framework_version: str ="4.49.0",
    pytorch_version: str ="2.6.0",
    py_version: str ="py312",
    instance_type: str ="local_gpu"
):
    """
    Deploy a HuggingFace model locally using SageMaker local mode
    
    Args:
        model_data_path (str): Path to model artifacts (local path or S3 URI)
        role (str): AWS IAM role ARN
        framework_version (str): HuggingFace Transformers version
        pytorch_version (str): PyTorch version
        py_version (str): Python version
        instance_type (str): Instance type (use 'local' for local mode)
    
    Returns:
        predictor: HuggingFace predictor object
    """
    try:
        # Initialize SageMaker session
        sagemaker_session = sagemaker.LocalSession()
        sagemaker_session.config = {'local': {'local_code': True}}
        
        # Create HuggingFace Model
        # model = HuggingFaceModel(
        #     model_data=f"file://{artifacts_file}",
        #     role=role,
        #     transformers_version=framework_version,
        #     pytorch_version=pytorch_version,
        #     py_version=py_version,
        #     sagemaker_session=sagemaker_session,
        #     env={"HF_TASK": "image-text-to-text"}
        # )
        print("Preparing model...")
        model = PyTorchModel(
            model_data=f"file://{artifacts_file}",
            role=role,
            framework_version=pytorch_version,
            source_dir=code_dir,
            py_version=py_version,
            entry_point="inference.py"
        )

        # Deploy the model locally
        print("Deploying model locally...")
        predictor = model.deploy(
            initial_instance_count=1,
            instance_type=instance_type
        )
        
        return predictor
    
    except Exception as e:
        print(f"Error deploying model locally (make sure Docker is enabled if in SageMaker Domain): {str(e)}")
        raise e

# Example usage
if __name__ == "__main__":
    # Get IAM role from environment variable
    role = os.environ.get(sagemaker.get_execution_role(), "arn:aws:iam::111111111111:role/service-role/AmazonSageMaker-ExecutionRole-20200101T000001")
    artifacts_file = (pathlib.Path(__file__).parent / "ARTIFACTS" / "package" / "model.tar.gz").absolute()
    code_dir = (pathlib.Path(__file__).parent / "code").absolute()

    try:
        # Deploy the model locally
        predictor = deploy_model_locally(
            artifacts_file=str(artifacts_file),
            code_dir=str(code_dir),
            role=role
        )
        
        # Example inference
        sample_input = {
            "image": get_base64_from_image(HERE.parent / "test_data" / "sidewalk.jpg"),
            "nav_goal": "sidewalk"
        }
        
        # Make prediction
        result = predictor.predict(sample_input)
        print(f"Prediction result: {result}")
        
        # Clean up (delete endpoint)
        predictor.delete_endpoint()
        
    except Exception as e:
        print(f"Error in deployment or inference: {str(e)}")
