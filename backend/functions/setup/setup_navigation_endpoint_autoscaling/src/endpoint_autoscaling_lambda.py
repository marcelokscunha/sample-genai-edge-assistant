import json
import boto3
from botocore.exceptions import ClientError


def handler(event, context):
    """
    Lambda function to configure autoscaling for navigation endpoints within SageMaker pipeline context.
    """
    print(f"Received event: {json.dumps(event, indent=2)}")
    
    endpoint_name = event.get("endpoint_name")
    if not endpoint_name:
        return {"statusCode": 400, "success": False, "error": "Missing 'endpoint_name' in event parameters"}
    
    min_capacity = event.get("min_capacity", 1)
    max_capacity = event.get("max_capacity", 2)
    target_value = event.get("target_value", 10.0)
    
    print(f"Configuring autoscaling for endpoint: {endpoint_name}")
    
    # Validate endpoint exists and is in valid state
    validate_endpoint_exists(endpoint_name)

    # Setup auto scaling for the endpoint
    setup_auto_scaling(endpoint_name, min_capacity, max_capacity, target_value)
        

def validate_endpoint_exists(endpoint_name):
    """Validate that the SageMaker endpoint exists and is not in a failed state."""

    sagemaker_client = boto3.client("sagemaker")
    response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    status = response["EndpointStatus"]
        
    print(f"Endpoint {endpoint_name} status: {status}")

    valid_statuses = ["Creating", "InService", "Updating"]
    if not status in valid_statuses:
        raise RuntimeError(f"Endpoint {endpoint_name} is in an invalid state: {status}")


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