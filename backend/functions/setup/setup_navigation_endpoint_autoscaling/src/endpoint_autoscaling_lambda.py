import json
import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    """
    Lambda function to configure autoscaling for navigation endpoints within SageMaker pipeline context.
    
    This function is designed to be called as a pipeline step, not from EventBridge triggers.
    It receives the endpoint name as a parameter and configures autoscaling with:
    - Min capacity: 1 instance
    - Max capacity: 2 instances  
    - Target tracking on invocations per instance
    
    Args:
        event: Pipeline step event containing endpoint_name
        context: Lambda context
        
    Returns:
        dict: Structured response for pipeline continuation
    """
    print(f"Received event: {json.dumps(event, indent=2)}")
    
    # Extract endpoint name from pipeline step parameters
    try:
        endpoint_name = event.get("endpoint_name")
        if not endpoint_name:
            raise ValueError("Missing 'endpoint_name' in event parameters")
            
        min_capacity = event.get("min_capacity", 1)
        max_capacity = event.get("max_capacity", 2)
        target_value = event.get("target_value", 10.0)
        
        print(f"Configuring autoscaling for endpoint: {endpoint_name}")
        print(f"Min capacity: {min_capacity}, Max capacity: {max_capacity}")
        print(f"Target invocations per instance: {target_value}")
        
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
        setup_auto_scaling(endpoint_name, min_capacity, max_capacity, target_value)
        
        success_msg = f"Successfully configured autoscaling for endpoint {endpoint_name}"
        print(success_msg)
        
        return {
            "statusCode": 200,
            "success": True,
            "message": success_msg,
            "endpoint_name": endpoint_name,
            "autoscaling_config": {
                "min_capacity": min_capacity,
                "max_capacity": max_capacity,
                "target_value": target_value
            }
        }
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            warning_msg = f"Autoscaling already configured for endpoint {endpoint_name}"
            print(warning_msg)
            return {
                "statusCode": 200,
                "success": True,
                "message": warning_msg,
                "endpoint_name": endpoint_name,
                "already_configured": True
            }
        else:
            error_msg = f"AWS ClientError configuring autoscaling: {str(e)}"
            print(error_msg)
            return {
                "statusCode": 500,
                "success": False,
                "error": error_msg,
                "endpoint_name": endpoint_name
            }
            
    except Exception as e:
        error_msg = f"Unexpected error configuring autoscaling: {str(e)}"
        print(error_msg)
        return {
            "statusCode": 500,
            "success": False,
            "error": error_msg,
            "endpoint_name": endpoint_name
        }


def setup_auto_scaling(endpoint_name, min_capacity=1, max_capacity=2, target_value=10.0):
    """
    Configure autoscaling for a SageMaker endpoint.
    
    Args:
        endpoint_name (str): Name of the SageMaker endpoint
        min_capacity (int): Minimum number of instances (default: 1)
        max_capacity (int): Maximum number of instances (default: 2)
        target_value (float): Target invocations per instance (default: 10.0)
    """
    application_autoscaling_client = boto3.client("application-autoscaling")
    resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
    
    print(f"Registering scalable target for resource: {resource_id}")
    
    # Register the scalable target
    application_autoscaling_client.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=min_capacity,
        MaxCapacity=max_capacity,
    )
    
    print(f"Creating scaling policy for resource: {resource_id}")
    
    # Create the scaling policy
    application_autoscaling_client.put_scaling_policy(
        PolicyName=f"NavigationEndpointScalingPolicy-{endpoint_name}",
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": target_value,
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
            },
            "ScaleInCooldown": 300,  # 5 minutes
            "ScaleOutCooldown": 300,  # 5 minutes
        },
    )
    
    print(f"Autoscaling configuration completed for endpoint: {endpoint_name}")