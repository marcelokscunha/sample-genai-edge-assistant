import pytest
from unittest.mock import Mock, patch
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from endpoint_deployment_lambda import handler, deploy_endpoint_from_existing_model


def test_handler_missing_model_package_arn():
    """Test handler with missing model_package_arn parameter"""
    event = {
        "endpoint_name": "test-endpoint"
    }
    context = Mock()
    
    with pytest.raises(ValueError, match="Missing 'model_package_arn'"):
        handler(event, context)


def test_handler_missing_endpoint_name():
    """Test handler with missing endpoint_name parameter"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package"
    }
    context = Mock()
    
    with pytest.raises(ValueError, match="Missing 'endpoint_name'"):
        handler(event, context)


@patch('endpoint_deployment_lambda.get_model_name_from_package')
@patch('endpoint_deployment_lambda.deploy_endpoint_from_existing_model')
def test_handler_successful_deployment(mock_deploy, mock_get_model_name):
    """Test successful endpoint deployment"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint",
        "instance_type": "ml.g5.xlarge",
        "initial_instance_count": 1
    }
    context = Mock()
    
    mock_get_model_name.return_value = "test-model"
    mock_deploy.return_value = None
    
    result = handler(event, context)
    
    assert result is None  # Handler returns None on success
    mock_get_model_name.assert_called_once_with("arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package")
    mock_deploy.assert_called_once_with(
        model_name="test-model",
        endpoint_name="test-endpoint", 
        instance_type="ml.g5.xlarge",
        initial_instance_count=1
    )


@patch('endpoint_deployment_lambda.get_model_name_from_package')
@patch('endpoint_deployment_lambda.deploy_endpoint_from_existing_model')
@patch('endpoint_deployment_lambda.check_existing_endpoint')
def test_handler_endpoint_already_exists(mock_check, mock_deploy, mock_get_model_name):
    """Test handler when endpoint already exists"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint"
    }
    context = Mock()
    
    mock_get_model_name.return_value = "test-model"
    # Mock the deploy function to raise ValidationException
    mock_deploy.side_effect = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "already exists"}},
        operation_name="CreateEndpoint"
    )
    mock_check.return_value = None  # Endpoint is in acceptable state
    
    result = handler(event, context)
    
    assert result is None  # Handler returns None on success
    mock_check.assert_called_once_with("test-endpoint")


@patch('endpoint_deployment_lambda.get_model_name_from_package')
@patch('endpoint_deployment_lambda.deploy_endpoint_from_existing_model')
def test_handler_with_defaults(mock_deploy, mock_get_model_name):
    """Test handler with default parameter values"""
    event = {
        "model_package_arn": "arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package",
        "endpoint_name": "test-endpoint"
    }
    context = Mock()
    
    mock_get_model_name.return_value = "test-model"
    mock_deploy.return_value = None
    
    result = handler(event, context)
    
    assert result is None
    mock_deploy.assert_called_once_with(
        model_name="test-model",
        endpoint_name="test-endpoint",
        instance_type="ml.g5.xlarge",  # Default value
        initial_instance_count=1       # Default value
    )


def test_deploy_endpoint_from_existing_model():
    """Test the deploy_endpoint_from_existing_model function"""
    with patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        
        # Mock responses - no create_model call since model already exists
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
        
        result = deploy_endpoint_from_existing_model(
            model_name="existing-test-model",
            endpoint_name="test-endpoint",
            instance_type="ml.g5.xlarge",
            initial_instance_count=1
        )
        
        # Function doesn't return anything, just verify calls were made
        assert result is None
        mock_sagemaker.create_endpoint_config.assert_called_once()
        mock_sagemaker.create_endpoint.assert_called_once()
        # Verify NO create_model call was made
        mock_sagemaker.create_model.assert_not_called()


def test_deploy_endpoint_with_defaults():
    """Test deploy_endpoint_from_existing_model with default parameters"""
    with patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        
        # Mock responses
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
        
        result = deploy_endpoint_from_existing_model(
            model_name="existing-test-model",
            endpoint_name="test-endpoint"
        )
        
        assert result is None
        
        # Verify default parameters were used
        create_config_call = mock_sagemaker.create_endpoint_config.call_args
        production_variants = create_config_call[1]["ProductionVariants"]
        assert production_variants[0]["InstanceType"] == "ml.g5.xlarge"
        assert production_variants[0]["InitialInstanceCount"] == 1
        assert production_variants[0]["ModelName"] == "existing-test-model"


def test_get_model_name_from_package():
    """Test get_model_name_from_package function"""
    with patch('endpoint_deployment_lambda.boto3.client') as mock_boto_client:
        mock_sagemaker = Mock()
        mock_boto_client.return_value = mock_sagemaker
        
        # Mock the describe_model_package response
        mock_sagemaker.describe_model_package.return_value = {
            "CustomerMetadataProperties": {
                "model_name": "navigation-model-12345"
            }
        }
        
        from endpoint_deployment_lambda import get_model_name_from_package
        
        result = get_model_name_from_package("arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package")
        
        assert result == "navigation-model-12345"
        mock_sagemaker.describe_model_package.assert_called_once_with(
            ModelPackageName="arn:aws:sagemaker:us-east-1:123456789012:model-package/test-package"
        )