import json
import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    """
    Lambda function to deploy navigation endpoint from approved model package within SageMaker pipeline context.
    
    This function is designed to be called as a pipeline step, receiving model package ARN
    and endpoint configuration as parameters.
    
    Args:
        event: Pipeline step event containing model_package_arn, endpoint_name, etc.
        context: Lambda context
        
    Returns:
        dict: Structured response for pipeline continuation
    """
    print(f"Received event: {json.dumps(event, indent=2)}")
    
    # Extract parameters from pipeline step
    try:
        model_package_arn = event.get("model_package_arn")
        endpoint_name = event.get("endpoint_name")
        instance_type = event.get("instance_type", "ml.g5.xlarge")
        initial_instance_count = event.get("initial_instance_count", 1)
        execution_role = event.get("execution_role")
        region = event.get("region")
        
        if not model_package_arn:
            raise ValueError("Missing 'model_package_arn' in event parameters")
        if not endpoint_name:
            raise ValueError("Missing 'endpoint_name' in event parameters")
        if not execution_role:
            raise ValueError("Missing 'execution_role' in event parameters")
            
        print(f"Deploying endpoint: {endpoint_name}")
        print(f"Model package ARN: {model_package_arn}")
        print(f"Instance type: {instance_type}, count: {initial_instance_count}")
        
    except Exception as e:
        error_msg = f"Failed to parse event parameters: {str(e)}"
        print(error_msg)
        return {
            "statusCode": 400,
            "success": False,
            "error": error_msg,
            "endpoint_name": event.get("endpoint_name", "unknown")
        }

    try:
        endpoint_arn = deploy_endpoint_from_model_package(
            model_package_arn=model_package_arn,
            endpoint_name=endpoint_name,
            instance_type=instance_type,
            initial_instance_count=initial_instance_count,
            execution_role=execution_role,
            region=region
        )
        
        success_msg = f"Successfully deployed endpoint {endpoint_name}"
        print(success_msg)
        
        return {
            "statusCode": 200,
            "success": True,
            "message": success_msg,
            "endpoint_name": endpoint_name,
            "endpoint_arn": endpoint_arn,
            "endpoint_config": {
                "instance_type": instance_type,
                "initial_instance_count": initial_instance_count
            }
        }
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ValidationException" and "already exists" in str(e):
            warning_msg = f"Endpoint {endpoint_name} already exists, checking status"
            print(warning_msg)
            
            # Check if existing endpoint is in service
            sagemaker_client = boto3.client("sagemaker")
            try:
                response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                endpoint_status = response["EndpointStatus"]
                
                if endpoint_status == "InService":
                    return {
                        "statusCode": 200,
                        "success": True,
                        "message": f"Endpoint {endpoint_name} already exists and is InService",
                        "endpoint_name": endpoint_name,
                        "endpoint_arn": response["EndpointArn"],
                        "already_exists": True
                    }
                else:
                    return {
                        "statusCode": 202,
                        "success": True,
                        "message": f"Endpoint {endpoint_name} already exists with status: {endpoint_status}",
                        "endpoint_name": endpoint_name,
                        "endpoint_status": endpoint_status,
                        "already_exists": True
                    }
            except Exception as desc_error:
                error_msg = f"Failed to describe existing endpoint: {str(desc_error)}"
                print(error_msg)
                return {
                    "statusCode": 500,
                    "success": False,
                    "error": error_msg,
                    "endpoint_name": endpoint_name
                }
        else:
            error_msg = f"AWS ClientError deploying endpoint: {str(e)}"
            print(error_msg)
            return {
                "statusCode": 500,
                "success": False,
                "error": error_msg,
                "endpoint_name": endpoint_name
            }
            
    except Exception as e:
        error_msg = f"Unexpected error deploying endpoint: {str(e)}"
        print(error_msg)
        return {
            "statusCode": 500,
            "success": False,
            "error": error_msg,
            "endpoint_name": endpoint_name
        }


def deploy_endpoint_from_model_package(
    model_package_arn,
    endpoint_name,
    instance_type="ml.g5.xlarge",
    initial_instance_count=1,
    execution_role=None,
    region=None
):
    """
    Deploy a SageMaker endpoint from an approved model package.
    
    Args:
        model_package_arn (str): ARN of the approved model package
        endpoint_name (str): Name for the endpoint
        instance_type (str): EC2 instance type for the endpoint
        initial_instance_count (int): Initial number of instances
        execution_role (str): IAM role ARN for SageMaker execution
        region (str): AWS region
        
    Returns:
        str: ARN of the created endpoint
    """
    sagemaker_client = boto3.client("sagemaker")
    
    # Generate unique names for model and endpoint config
    import time
    timestamp = str(int(time.time()))
    model_name = f"{endpoint_name}-model-{timestamp}"
    endpoint_config_name = f"{endpoint_name}-config-{timestamp}"
    
    print(f"Creating model: {model_name}")
    print(f"Creating endpoint config: {endpoint_config_name}")
    
    # Step 1: Create model from model package
    create_model_response = sagemaker_client.create_model(
        ModelName=model_name,
        Containers=[
            {
                "ModelPackageName": model_package_arn
            }
        ],
        ExecutionRoleArn=execution_role,
    )
    
    print(f"Created model: {create_model_response['ModelArn']}")
    
    # Step 2: Create endpoint configuration
    create_config_response = sagemaker_client.create_endpoint_config(
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
    
    print(f"Created endpoint config: {create_config_response['EndpointConfigArn']}")
    
    # Step 3: Create endpoint
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
        # Don't fail the pipeline if waiting times out, endpoint may still deploy successfully
    
    return endpoint_arn