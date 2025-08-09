import json
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from moto import mock_aws
import boto3

# Import the lambda function
import sys
import os
import importlib.util

from src.endpoint_autoscaling_lambda import handler, setup_auto_scaling

@mock_aws
def test_handler_success():
    """Test successful autoscaling configuration"""
    # Arrange
    event = {
        "endpoint_name": "test-navigation-endpoint",
        "min_capacity": 1,
        "max_capacity": 2,
        "target_value": 10.0
    }
    context = Mock()
    
    # Act
    result = handler(event, context)
    
    # Assert
    assert result["statusCode"] == 200
    assert result["success"] is True
    assert result["endpoint_name"] == "test-navigation-endpoint"
    assert "Successfully configured autoscaling" in result["message"]
    assert result["autoscaling_config"]["min_capacity"] == 1
    assert result["autoscaling_config"]["max_capacity"] == 2
    assert result["autoscaling_config"]["target_value"] == 10.0


@mock_aws
def test_handler_with_default_values():
    """Test handler with default autoscaling values"""
    # Arrange
    event = {
        "endpoint_name": "test-navigation-endpoint"
    }
    context = Mock()
    
    # Act
    result = handler(event, context)
    
    # Assert
    assert result["statusCode"] == 200
    assert result["success"] is True
    assert result["autoscaling_config"]["min_capacity"] == 1
    assert result["autoscaling_config"]["max_capacity"] == 2
    assert result["autoscaling_config"]["target_value"] == 10.0


def test_handler_missing_endpoint_name():
    """Test handler with missing endpoint name"""
    # Arrange
    event = {}
    context = Mock()
    
    # Act
    result = handler(event, context)
    
    # Assert
    assert result["statusCode"] == 400
    assert result["success"] is False
    assert "Missing 'endpoint_name'" in result["error"]


def test_handler_already_configured():
    """Test handler when autoscaling is already configured"""
    # Arrange
    event = {
        "endpoint_name": "test-navigation-endpoint"
    }
    context = Mock()
    
    # Mock the setup_auto_scaling function to raise ValidationException
    original_setup = lambda_module.setup_auto_scaling
    
    def mock_setup(*args, **kwargs):
        raise ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Already exists'}},
            operation_name='RegisterScalableTarget'
        )
    
    lambda_module.setup_auto_scaling = mock_setup
    
    try:
        # Act
        result = handler(event, context)
        
        # Assert
        assert result["statusCode"] == 200
        assert result["success"] is True
        assert result["already_configured"] is True
        assert "already configured" in result["message"]
    finally:
        # Restore original function
        lambda_module.setup_auto_scaling = original_setup


def test_handler_client_error():
    """Test handler with AWS ClientError - using mock for error simulation"""
    # Arrange
    event = {
        "endpoint_name": "test-navigation-endpoint"
    }
    context = Mock()
    
    # Mock the setup_auto_scaling function to raise ClientError
    original_setup = lambda_module.setup_auto_scaling
    
    def mock_setup(*args, **kwargs):
        raise ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='RegisterScalableTarget'
        )
    
    lambda_module.setup_auto_scaling = mock_setup
    
    try:
        # Act
        result = handler(event, context)
        
        # Assert
        assert result["statusCode"] == 500
        assert result["success"] is False
        assert "AWS ClientError" in result["error"]
    finally:
        # Restore original function
        lambda_module.setup_auto_scaling = original_setup


def test_handler_unexpected_error():
    """Test handler with unexpected error"""
    # Arrange
    event = {
        "endpoint_name": "test-navigation-endpoint"
    }
    context = Mock()
    
    # Mock the setup_auto_scaling function to raise unexpected error
    original_setup = lambda_module.setup_auto_scaling
    
    def mock_setup(*args, **kwargs):
        raise Exception("Unexpected error")
    
    lambda_module.setup_auto_scaling = mock_setup
    
    try:
        # Act
        result = handler(event, context)
        
        # Assert
        assert result["statusCode"] == 500
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
    finally:
        # Restore original function
        lambda_module.setup_auto_scaling = original_setup


@mock_aws
def test_setup_auto_scaling_default_parameters():
    """Test setup_auto_scaling with default parameters using moto"""
    # Arrange
    endpoint_name = "test-navigation-endpoint"
    
    # Mock the boto3 client calls to verify they're made with correct parameters
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name)
        
        # Assert - verify the correct AWS calls were made
        expected_resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
        
        mock_client.register_scalable_target.assert_called_once_with(
            ServiceNamespace="sagemaker",
            ResourceId=expected_resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            MinCapacity=1,
            MaxCapacity=2,
        )
        
        mock_client.put_scaling_policy.assert_called_once_with(
            PolicyName=f"NavigationEndpointScalingPolicy-{endpoint_name}",
            ServiceNamespace="sagemaker",
            ResourceId=expected_resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            PolicyType="TargetTrackingScaling",
            TargetTrackingScalingPolicyConfiguration={
                "TargetValue": 10.0,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
                },
                "ScaleInCooldown": 300,
                "ScaleOutCooldown": 300,
            },
        )


@mock_aws
def test_setup_auto_scaling_custom_parameters():
    """Test setup_auto_scaling with custom parameters"""
    # Arrange
    endpoint_name = "test-navigation-endpoint"
    min_capacity = 2
    max_capacity = 5
    target_value = 15.0
    
    # Mock the boto3 client calls to verify they're made with correct parameters
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name, min_capacity, max_capacity, target_value)
        
        # Assert - verify the correct AWS calls were made with custom parameters
        expected_resource_id = f"endpoint/{endpoint_name}/variant/AllTraffic"
        
        mock_client.register_scalable_target.assert_called_once_with(
            ServiceNamespace="sagemaker",
            ResourceId=expected_resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            MinCapacity=min_capacity,
            MaxCapacity=max_capacity,
        )
        
        scaling_policy_call = mock_client.put_scaling_policy.call_args
        assert scaling_policy_call[1]["TargetTrackingScalingPolicyConfiguration"]["TargetValue"] == target_value


@mock_aws
def test_setup_auto_scaling_resource_id_format():
    """Test that resource ID is formatted correctly"""
    # Arrange
    endpoint_name = "my-test-endpoint-123"
    
    # Mock the boto3 client calls to verify resource ID format
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name)
        
        # Assert
        expected_resource_id = "endpoint/my-test-endpoint-123/variant/AllTraffic"
        
        register_call = mock_client.register_scalable_target.call_args
        assert register_call[1]["ResourceId"] == expected_resource_id
        
        policy_call = mock_client.put_scaling_policy.call_args
        assert policy_call[1]["ResourceId"] == expected_resource_id


@mock_aws
def test_setup_auto_scaling_policy_name_format():
    """Test that scaling policy name is formatted correctly"""
    # Arrange
    endpoint_name = "navigation-endpoint-v1"
    
    # Mock the boto3 client calls to verify policy name format
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name)
        
        # Assert
        expected_policy_name = "NavigationEndpointScalingPolicy-navigation-endpoint-v1"
        
        policy_call = mock_client.put_scaling_policy.call_args
        assert policy_call[1]["PolicyName"] == expected_policy_name


@mock_aws
def test_setup_auto_scaling_cooldown_periods():
    """Test that cooldown periods are set correctly"""
    # Arrange
    endpoint_name = "test-endpoint"
    
    # Mock the boto3 client calls to verify cooldown periods
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name)
        
        # Assert
        policy_call = mock_client.put_scaling_policy.call_args
        config = policy_call[1]["TargetTrackingScalingPolicyConfiguration"]
        
        assert config["ScaleInCooldown"] == 300
        assert config["ScaleOutCooldown"] == 300


@mock_aws
def test_setup_auto_scaling_predefined_metric():
    """Test that predefined metric specification is correct"""
    # Arrange
    endpoint_name = "test-endpoint"
    
    # Mock the boto3 client calls to verify metric specification
    with patch('boto3.client') as mock_client_factory:
        mock_client = Mock()
        mock_client_factory.return_value = mock_client
        
        # Act
        setup_auto_scaling(endpoint_name)
        
        # Assert
        policy_call = mock_client.put_scaling_policy.call_args
        config = policy_call[1]["TargetTrackingScalingPolicyConfiguration"]
        metric_spec = config["PredefinedMetricSpecification"]
        
        assert metric_spec["PredefinedMetricType"] == "SageMakerVariantInvocationsPerInstance"