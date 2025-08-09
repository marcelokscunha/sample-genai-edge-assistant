import json
import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients will be initialized when needed
sagemaker_client = None
s3_client = None

def get_sagemaker_client():
    """Get or create SageMaker client."""
    global sagemaker_client
    if sagemaker_client is None:
        sagemaker_client = boto3.client('sagemaker')
    return sagemaker_client

def get_s3_client():
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client


def handler(event, context):
    """
    Lambda function to create and manage SageMaker Inference Recommender jobs.
    
    This function is designed to be used as a Lambda step in SageMaker pipelines.
    It creates an inference recommendation job for a registered model package.
    
    Expected event structure:
    {
        "model_package_arn": "arn:aws:sagemaker:region:account:model-package/...",
        "job_name": "navigation-inference-recommendation-job",
        "results_s3_bucket": "bucket-name",
        "results_s3_prefix": "navigation/inference-recommendations"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract parameters from event
        model_package_arn = event.get('model_package_arn')
        job_name = event.get('job_name', f"navigation-inference-rec-{int(datetime.now().timestamp())}")
        results_s3_bucket = event.get('results_s3_bucket')
        results_s3_prefix = event.get('results_s3_prefix', 'navigation/inference-recommendations')
        
        # Validate required parameters
        if not model_package_arn:
            raise ValueError("model_package_arn is required")
        if not results_s3_bucket:
            raise ValueError("results_s3_bucket is required")
        
        # Create inference recommendation job
        recommendation_job_response = create_inference_recommendation_job(
            job_name=job_name,
            model_package_arn=model_package_arn,
            results_s3_bucket=results_s3_bucket,
            results_s3_prefix=results_s3_prefix
        )
        
        logger.info(f"Successfully created inference recommendation job: {job_name}")
        
        return {
            'statusCode': 200,
            'body': {
                'job_name': job_name,
                'job_arn': recommendation_job_response.get('JobArn'),
                'status': 'CREATED',
                'results_s3_uri': f"s3://{results_s3_bucket}/{results_s3_prefix}/{job_name}",
                'message': f'Inference recommendation job {job_name} created successfully'
            }
        }
        
    except Exception as e:
        logger.error(f"Error in inference recommendation Lambda: {str(e)}")
        
        # Return success with error details (non-blocking as per requirements)
        return {
            'statusCode': 200,
            'body': {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Inference recommendation job failed but pipeline will continue'
            }
        }


def create_inference_recommendation_job(job_name, model_package_arn, results_s3_bucket, results_s3_prefix):
    """
    Create a SageMaker Inference Recommender job.
    
    Args:
        job_name (str): Name for the inference recommendation job
        model_package_arn (str): ARN of the registered model package
        results_s3_bucket (str): S3 bucket for storing results
        results_s3_prefix (str): S3 prefix for storing results
    
    Returns:
        dict: Response from create_inference_recommendations_job API call
    """
    # Define the job configuration
    job_config = {
        'JobName': job_name,
        'JobType': 'Default',  # Use Default job type for automatic recommendations
        'RoleArn': get_execution_role(),
        'InputConfig': {
            'ModelPackageVersionArn': model_package_arn,
            'JobDurationInSeconds': 3600,  # 1 hour timeout
        },
        'OutputConfig': {
            'KmsKeyId': '',  # Use default encryption
            'CompiledOutputConfig': {
                'S3OutputLocation': f"s3://{results_s3_bucket}/{results_s3_prefix}/{job_name}"
            }
        }
    }
    
    # Create the inference recommendation job - let boto3 handle errors
    client = get_sagemaker_client()
    response = client.create_inference_recommendations_job(**job_config)
    
    logger.info(f"Created inference recommendation job with ARN: {response.get('JobArn')}")
    return response


def get_execution_role():
    """
    Get the execution role ARN from environment or construct it.
    
    Returns:
        str: IAM role ARN for SageMaker execution
    """
    import os
    
    # Try to get from environment variable first
    role_arn = os.environ.get('SAGEMAKER_EXECUTION_ROLE')
    
    if not role_arn:
        # Construct role ARN using account ID and region
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.Session().region_name
        role_name = 'SageMakerExecutionRole'  # Default role name
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    
    return role_arn


def get_job_status(job_name):
    """
    Get the status of an inference recommendation job.
    
    Args:
        job_name (str): Name of the inference recommendation job
    
    Returns:
        dict: Job status information
    """
    try:
        client = get_sagemaker_client()
        response = client.describe_inference_recommendations_job(JobName=job_name)
        
        return {
            'job_name': job_name,
            'status': response.get('Status'),
            'creation_time': response.get('CreationTime'),
            'last_modified_time': response.get('LastModifiedTime'),
            'completion_time': response.get('CompletionTime'),
            'failure_reason': response.get('FailureReason'),
            'output_config': response.get('OutputConfig', {})
        }
        
    except ClientError as e:
        logger.error(f"Error getting job status for {job_name}: {str(e)}")
        raise