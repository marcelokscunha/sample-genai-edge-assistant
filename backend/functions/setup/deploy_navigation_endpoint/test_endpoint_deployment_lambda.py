import pytest
from unittest.mock import Mock, patch
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from endpoint_deployment_lambda import handler, deploy_endpoint_from_model_package


def test_handler_missing_model_package_arn():
    """Test handler with missing model_package_arn parameter"""
    event = {
        "endpoint_name": "test-endpoint",
        "execution_role": "arn:aws:iam::123456789012:role/test-role"
    }
    context = Mock()
    
    result = handler(event, context)
    
    assert result["statusCode"] == 400
    assert result["success"] is False
    assert "model_package_arn" in result["error"]


def test_handler_missing_endpoint_name():
    """Test handler with missing endpoint_name parameter"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "execution_role": "arn:aws:iam::123456789012:role/test-role"
    }
    context = Mock()
    
    result = handler(event, context)
    
    assert result["statusCode"] == 400
    assert result["success"] is False
    assert "endpoint_name" in result["error"]


def test_handler_missing_execution_role():
    """Test handler with missing execution_role parameter"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint"
    }
    context = Mock()
    
    result = handler(event, context)
    
    assert result["statusCode"] == 400
    assert result["success"] is False
    assert "execution_role" in result["error"]


def test_handler_successful_deployment():
    """Test successful endpoint deployment"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint",
        "instance_type": "ml.g5.xlarge",
        "initial_instance_count": 1,
        "execution_role": "arn:aws:iam::123456789012:role/test-role",
        "region": "us-east-1"
    }
    context = Mock()
    
    with patch('endpoint_deployment_lambda.deploy_endpoint_from_model_package') as mock_deploy:
        mock_deploy.return_value = "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"
        
        result = handler(event, context)
        
        assert result["statusCode"] == 200
        assert result["success"] is True
        assert result["endpoint_name"] == "test-endpoint"
        assert "endpoint_arn" in result
        mock_deploy.assert_called_once()


def test_handler_endpoint_already_exists():
    """Test handler when endpoint already exists and is InService"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint",
        "execution_role": "arn:aws:iam::123456789012:role/test-role",
        "region": "us-east-1"
    }
    context = Mock()
    
    with patch('endpoint_deployment_lambda.deploy_endpoint_from_model_package') as mock_deploy, \
         patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        
        # Mock the deploy function to raise ValidationException
        mock_deploy.side_effect = ClientError(
            error_response={"Error": {"Code": "ValidationException", "Message": "already exists"}},
            operation_name="CreateModel"
        )
        
        # Mock the SageMaker client for describe_endpoint call
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        mock_sagemaker.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"
        }
        
        result = handler(event, context)
        
        assert result["statusCode"] == 200
        assert result["success"] is True
        assert result["already_exists"] is True


def test_deploy_endpoint_from_model_package():
    """Test the deploy_endpoint_from_model_package function"""
    with patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        
        # Mock responses
        mock_sagemaker.create_model.return_value = {
            "ModelArn": "arn:aws:sagemaker:us-east-1:123456789012:model/test-model"
        }
        mock_sagemaker.create_endpoint_config.return_value = {
            "EndpointConfigArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/test-config"
        }
        mock_sagemaker.create_endpoint.return_value = {
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"
        }
        
        # Mock waiter
        mock_waiter = Mock()
        mock_sagemaker.get_waiter.return_value = mock_waiter
        mock_waiter.wait.return_value = None
        
        result = deploy_endpoint_from_model_package(
            model_package_arn="arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
            endpoint_name="test-endpoint",
            instance_type="ml.g5.xlarge",
            initial_instance_count=1,
            execution_role="arn:aws:iam::123456789012:role/test-role",
            region="us-east-1"
        )
        
        assert result == "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"


def test_deploy_endpoint_with_defaults():
    """Test deploy_endpoint_from_model_package with default parameters"""
    with patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        
        # Mock responses
        mock_sagemaker.create_model.return_value = {
            "ModelArn": "arn:aws:sagemaker:us-east-1:123456789012:model/test-model"
        }
        mock_sagemaker.create_endpoint_config.return_value = {
            "EndpointConfigArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/test-config"
        }
        mock_sagemaker.create_endpoint.return_value = {
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"
        }
        
        # Mock waiter
        mock_waiter = Mock()
        mock_sagemaker.get_waiter.return_value = mock_waiter
        mock_waiter.wait.return_value = None
        
        result = deploy_endpoint_from_model_package(
            model_package_arn="arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
            endpoint_name="test-endpoint",
            execution_role="arn:aws:iam::123456789012:role/test-role"
        )
        
        assert result == "arn:aws:sagemaker:us-east-1:123456789012:endpoint/test-endpoint"
        
        # Verify default parameters were used
        create_config_call = mock_sagemaker.create_endpoint_config.call_args
        production_variants = create_config_call[1]["ProductionVariants"]
        assert production_variants[0]["InstanceType"] == "ml.g5.xlarge"
        assert production_variants[0]["InitialInstanceCount"] == 1