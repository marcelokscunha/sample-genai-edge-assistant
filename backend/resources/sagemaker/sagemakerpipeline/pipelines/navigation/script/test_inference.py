import base64
import os
import tarfile
import pathlib
import pytest
from unittest.mock import patch, MagicMock
from pprint import pprint

from src.inference import model_fn, predict_fn, input_fn, output_fn, InferenceInput, InferenceResponse


def test_input_fn_valid_json():
    """Test input function with valid JSON."""
    test_data = {
        "image": "data:image/jpeg;base64,test_data",
        "nav_goal": "sidewalk"
    }
    json_data = InferenceInput(**test_data).model_dump_json()
    
    result = input_fn(json_data, "application/json")
    
    assert result == test_data


def test_input_fn_invalid_content_type():
    """Test input function with invalid content type."""
    test_data = '{"image": "test", "nav_goal": "sidewalk"}'
    
    with pytest.raises(ValueError) as exc_info:
        input_fn(test_data, "text/plain")
    
    assert "Content type must be application/json" in str(exc_info.value)


def test_input_fn_invalid_json():
    """Test input function with invalid JSON structure."""
    invalid_json = '{"invalid": "data"}'
    
    with pytest.raises(Exception):  # Pydantic validation error
        input_fn(invalid_json, "application/json")


def test_output_fn_valid():
    """Test output function with valid prediction."""
    prediction = "Go right to reach the sidewalk"
    
    result = output_fn(prediction, "application/json")
    
    expected = InferenceResponse(response=prediction).model_dump_json()
    assert result == expected


def test_output_fn_invalid_accept():
    """Test output function with invalid accept type."""
    prediction = "Go right to reach the sidewalk"
    
    with pytest.raises(ValueError) as exc_info:
        output_fn(prediction, "text/plain")
    
    assert "Accept type must be application/json" in str(exc_info.value)


@patch('src.inference.NavigationPipeline')
def test_model_fn(mock_pipeline_class):
    """Test model_fn creates NavigationPipeline correctly."""
    mock_pipeline = MagicMock()
    mock_pipeline_class.return_value = mock_pipeline
    
    result = model_fn("/path/to/model")
    
    mock_pipeline_class.assert_called_once_with("/path/to/model")
    assert result == mock_pipeline


@patch('src.inference.NavigationPipeline')
def test_predict_fn(mock_pipeline_class):
    """Test predict_fn calls pipeline predict method."""
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = "Go right to reach the sidewalk"
    
    payload = {
        "image": "data:image/jpeg;base64,test_data",
        "nav_goal": "sidewalk"
    }
    
    result = predict_fn(payload, mock_pipeline)
    
    mock_pipeline.predict.assert_called_once_with(**payload)
    assert result == "Go right to reach the sidewalk"


def test_inference_input_validation():
    """Test InferenceInput validation."""
    # Valid input
    valid_data = {
        "image": "data:image/jpeg;base64,test_data",
        "nav_goal": "sidewalk"
    }
    input_obj = InferenceInput(**valid_data)
    assert input_obj.image == valid_data["image"]
    assert input_obj.nav_goal == valid_data["nav_goal"]
    
    # Invalid input - missing fields
    with pytest.raises(Exception):  # Pydantic validation error
        InferenceInput(image="test")


def test_inference_response_validation():
    """Test InferenceResponse validation."""
    response_obj = InferenceResponse(response="Go right")
    assert response_obj.response == "Go right"
    
    # Test JSON serialization
    json_str = response_obj.model_dump_json()
    assert '"response":"Go right"' in json_str