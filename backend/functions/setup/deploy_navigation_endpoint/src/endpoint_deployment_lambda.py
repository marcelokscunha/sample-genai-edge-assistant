import json
import time

import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    """
    Lambda function to deploy endpoint from existing SageMaker model.
    """
    print(f"Received event: {json.dumps(event, indent=2)}")
    
    model_package_arn = event.get("model_package_arn")
    endpoint_name = event.get("endpoint_name")
    instance_type = event.get("instance_type", "ml.g5.xlarge")
    initial_instance_count = event.get("initial_instance_count", 1)
    
    if not model_package_arn:
        raise ValueError("Missing 'model_package_arn' in event parameters")
    if not endpoint_name:
        raise ValueError("Missing 'endpoint_name' in event parameters")
    
    model_name = get_model_name_from_package(model_package_arn)

    print(f"Deploying endpoint: {endpoint_name}")
    print(f"Using existing model from model package: {model_name} (package: {model_package_arn})")
    print(f"Instance type: {instance_type}, count: {initial_instance_count}")
    
    try:
        deploy_endpoint_from_existing_model(
            model_name=model_name,
            endpoint_name=endpoint_name,
            instance_type=instance_type,
            initial_instance_count=initial_instance_count
        )
        print(f"Successfully deployed endpoint {endpoint_name}")
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException" and "already exists" in str(e):
            print(f"Endpoint {endpoint_name} already exists, checking status")
            check_existing_endpoint(endpoint_name)
        else:
            raise


def check_existing_endpoint(endpoint_name):
    """Check if existing endpoint is usable, raise exception if not."""
    sagemaker_client = boto3.client("sagemaker")
    response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    status = response["EndpointStatus"]
    
    print(f"Existing endpoint {endpoint_name} status: {status}")
    
    if status in ["InService", "Creating", "Updating"]:
        print(f"Endpoint {endpoint_name} is in acceptable state: {status}")
    else:
        raise RuntimeError(f"Endpoint {endpoint_name} is in unusable state: {status}")

def get_model_name_from_package(model_package_arn):
    """
    Get model name from model package ARN.
    There must be a CustomerMetadataProperties in the format: { "model_name": "<CREATED-MODEL-NAME>"}
    """
    sagemaker_client = boto3.client("sagemaker")
    response = sagemaker_client.describe_model_package(ModelPackageName=model_package_arn)
    return response["CustomerMetadataProperties"]["model_name"]

def deploy_endpoint_from_existing_model(
    model_name,
    endpoint_name,
    instance_type="ml.g5.xlarge",
    initial_instance_count=1
):
    """
    Deploy a SageMaker endpoint from an existing SageMaker model.
    
    Args:
        model_name (str): Name of the existing SageMaker model
        endpoint_name (str): Name for the endpoint
        instance_type (str): EC2 instance type for the endpoint
        initial_instance_count (int): Initial number of instances
    """
    sagemaker_client = boto3.client("sagemaker")
    
    # Generate unique endpoint config name
    timestamp = str(int(time.time()))
    endpoint_config_name = f"{endpoint_name}-config-{timestamp}"
    
    print(f"Creating endpoint config: {endpoint_config_name}")
    
    # Step 1: Create endpoint configuration
    sagemaker_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "InitialInstanceCount": initial_instance_count,
                "InstanceType": instance_type,
                "InitialVariantWeight": 1.0,
            }
        ],
    )
    
    print(f"Created endpoint config: {endpoint_config_name}")
    
    # Step 2: Create endpoint
    create_endpoint_response = sagemaker_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name,
    )
    
    endpoint_arn = create_endpoint_response["EndpointArn"]
    print(f"Created endpoint: {endpoint_arn}")
    
    # Wait for endpoint to be in service (with timeout)
    print(f"Waiting for endpoint {endpoint_name} to be InService...")
    waiter = sagemaker_client.get_waiter("endpoint_in_service")
    
    try:
        waiter.wait(
            EndpointName=endpoint_name,
            WaiterConfig={
                "Delay": 30,  # Check every 30 seconds
                "MaxAttempts": 20  # Wait up to 10 minutes
            }
        )
        print(f"Endpoint {endpoint_name} is now InService")
    except Exception as e:
        print(f"Warning: Endpoint deployment may still be in progress: {str(e)}")
        # Don't fail - endpoint may still deploy successfully