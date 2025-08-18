import base64
import json
import os
import pathlib
import tarfile
import tempfile
from pathlib import Path
from pprint import pprint

from inference import model_fn, predict_fn, input_fn, output_fn

HERE = pathlib.Path(__file__).parent.absolute()

def get_base64_from_image(image_path: str) -> str:
    """Convert image file to base64 data URI format."""
    with open(image_path, 'rb') as img_file:
        b64_bytes = base64.b64encode(img_file.read())
        b64_str = b64_bytes.decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_str}"
    return data_uri

def untar_model_artifacts():
    """
    Extract model artifacts from tar.gz file.
    Returns the path to the extracted model directory.
    """
    
    # Check if running in SageMaker processing job environment
    input_dir = Path(os.environ.get("SM_PROCESSING_INPUT_DIR", "/opt/ml/processing/input"))
    model_input_dir = input_dir / "model"
    
    if model_input_dir.exists():
        # SageMaker processing job - extract model.tar.gz
        print("Running in SageMaker processing job environment")
        model_tar_path = model_input_dir / "model.tar.gz"
        if not model_tar_path.exists():
            # Look for any .tar.gz file
            tar_files = list(model_input_dir.glob("*.tar.gz"))
            if tar_files:
                model_tar_path = tar_files[0]
            else:
                raise RuntimeError(f"No model.tar.gz file found in {model_input_dir}")
        
        # Extract to temporary directory
        extract_dir = Path(tempfile.mkdtemp()) / "extracted_model"
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Extracting model from {model_tar_path} to {extract_dir}")
        with tarfile.open(model_tar_path, 'r:gz') as tar:
            tar.extractall(path=extract_dir)
        
        return extract_dir
    else:
        # Local testing
        print("Running in local environment")
        artifacts_dir = HERE / "ARTIFACTS" / "model"
        if not artifacts_dir.exists():
            raise RuntimeError("ARTIFACTS directory does not exist. Please run the prepare_model_files.py script first.")
        return artifacts_dir

def validate_output_format(result):
    """Validate that the output matches the expected format for navigation."""
    # Expected format: {'response': 'string with navigation guidance'}
    if not isinstance(result, dict):
        raise ValueError(f"Expected dict output, got {type(result)}")
    
    if 'response' not in result:
        raise ValueError("Output dict must contain 'response' key")
    
    response = result['response']
    if not isinstance(response, str):
        raise ValueError(f"Response must be string, got {type(response)}")
    
    if len(response.strip()) == 0:
        raise ValueError("Response cannot be empty")
    
    # Check for navigation guidance keywords
    response_lower = response.lower()
    navigation_keywords = ['right', 'left', 'forward', 'no_action']
    found_keywords = [kw for kw in navigation_keywords if kw in response_lower]
    
    if not found_keywords:
        print("Warning: Response may not contain expected navigation guidance (no keywords detected)")
    else:
        print(f"✓ Found navigation keywords: {found_keywords}")
    
    print("✓ Navigation output format validation passed")
    return True


def validate_chat_output_format(result):
    """Validate that the output matches the expected format for chat."""
    # Expected format: {'response': 'string with chat response'}
    if not isinstance(result, dict):
        raise ValueError(f"Expected dict output, got {type(result)}")
    
    if 'response' not in result:
        raise ValueError("Output dict must contain 'response' key")
    
    response = result['response']
    if not isinstance(response, str):
        raise ValueError(f"Response must be string, got {type(response)}")
    
    if len(response.strip()) == 0:
        raise ValueError("Response cannot be empty")
    
    # Check for descriptive content (chat responses should be descriptive)
    response_lower = response.lower()
    descriptive_keywords = ['see', 'image', 'shows', 'appears', 'visible', 'contains', 'depicts']
    found_keywords = [kw for kw in descriptive_keywords if kw in response_lower]
    
    if not found_keywords:
        print("Warning: Response may not contain expected descriptive content (no keywords detected)")
    else:
        print(f"✓ Found descriptive keywords: {found_keywords}")
    
    print("✓ Chat output format validation passed")
    return True

def create_sample_payload(navigation_input_data, chat_input_data):
    """
    Create a single sample payload archive for SageMaker Inference Recommender.
    This payload will contain both navigation and chat examples and be used during 
    model registration to enable inference recommendations.
    """
    # Get output directory (SageMaker processing job or local)
    output_dir = Path(os.environ.get("SM_PROCESSING_OUTPUT_DIR", "/opt/ml/processing/output"))
    
    # Get sample payload filename from environment variable (set by SageMaker pipeline)
    sample_payload_filename = os.environ.get("SAMPLE_PAYLOAD_FILENAME", "gemma3n_sample_payload.tar.gz")
    
    # Create sample payload directory
    payload_dir = output_dir / "sample-payload"
    payload_dir.mkdir(parents=True, exist_ok=True)
    
    # Create navigation sample input file
    navigation_input_file = payload_dir / "sample_input_navigation.json"
    with open(navigation_input_file, 'w') as f:
        json.dump(navigation_input_data, f, indent=2)
    
    # Create chat sample input file
    chat_input_file = payload_dir / "sample_input_chat.json"
    with open(chat_input_file, 'w') as f:
        json.dump(chat_input_data, f, indent=2)
    
    # Create the payload archive with both samples
    payload_archive_path = output_dir / sample_payload_filename
    
    with tarfile.open(payload_archive_path, 'w:gz') as tar:
        tar.add(navigation_input_file, arcname="sample_input_navigation.json")
        tar.add(chat_input_file, arcname="sample_input_chat.json")
    
    print(f"Sample payload archive created at: {payload_archive_path}")
    print("  - Contains: sample_input_navigation.json")
    print("  - Contains: sample_input_chat.json")
    
    # Create comprehensive metadata file with both pipeline types
    payload_metadata = {
        "payload_archive": sample_payload_filename,
        "content_type": "application/json",
        "model_type": "gemma3n_foundation_model",
        "supported_pipelines": ["navigation", "chat"],
        "sample_description": "Gemma3n foundation model sample inputs for both navigation and chat use cases",
        "samples": {
            "navigation": {
                "file": "sample_input_navigation.json",
                "description": "Navigation model sample input with base64 image and navigation goal",
                "input_format": {
                    "pipeline_type": "navigation",
                    "image": "base64 encoded image data URI",
                    "nav_goal": "string describing navigation target (e.g., 'sidewalk')"
                }
            },
            "chat": {
                "file": "sample_input_chat.json", 
                "description": "Chat model sample input with multimodal messages",
                "input_format": {
                    "pipeline_type": "chat",
                    "messages": "array of message objects with role and content (text, image, audio)"
                }
            }
        }
    }
    
    metadata_file = output_dir / "payload_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(payload_metadata, f, indent=2)
    
    print(f"Payload metadata saved at: {metadata_file}")
    return str(payload_archive_path)


def run_full_pipeline_test(artifacts_dir: str, create_payload: bool = True):
    """
    Run the full pipeline test for both navigation and chat modes.
    
    Args:
        artifacts_dir: Path to the model artifacts directory
        create_payload: Whether to create sample payload (default True for SageMaker, False for local testing)
    
    Returns:
        tuple: (navigation_result_dict, chat_result_dict)
    """
    print("Testing full inference pipeline...")
    
    # Step 1: Load model
    print("1. Loading model...")
    pipeline = model_fn(artifacts_dir)
    print("✓ Model loaded successfully")
    
    # Step 2: Prepare navigation input data as JSON string (as it would come from SageMaker endpoint)
    print("2. Preparing navigation input data...")
    navigation_input_data = {
        "task": "navigation",
        "payload": {
            "image": get_base64_from_image(HERE / "data" / "samples" / "sidewalk.jpg"),
            "goal": "sidewalk"
        }
    }
    navigation_json_input = json.dumps(navigation_input_data)
    print("✓ Navigation input data prepared")
    
    # Step 2b: Prepare chat input data as JSON string
    print("2b. Preparing chat input data...")
    chat_input_data = {
        "task": "chat",
        "payload": {
            "content": [
                {
                    "type": "image",
                    "value": get_base64_from_image(HERE / "data" / "samples" / "sidewalk.jpg")
                },
                {
                    "type": "text",
                    "value": "What do you see in this image? Describe it in detail."
                }
            ]
        }
    }
    chat_json_input = json.dumps(chat_input_data)
    print("✓ Chat input data prepared")
    
    # Step 3: Test navigation pipeline
    print("3. Testing navigation pipeline...")
    print("3a. Testing input_fn for navigation...")
    parsed_navigation_input = input_fn(navigation_json_input, "application/json")
    assert isinstance(parsed_navigation_input, dict)
    assert parsed_navigation_input["task"] == "navigation"
    print("✓ Navigation input_fn processed successfully")
    
    print("3b. Testing predict_fn for navigation...")
    navigation_prediction = predict_fn(parsed_navigation_input, pipeline)
    assert isinstance(navigation_prediction, str)
    print("✓ Navigation predict_fn completed successfully")
    
    print("3c. Testing output_fn for navigation...")
    navigation_final_output = output_fn(navigation_prediction, "application/json")
    assert isinstance(navigation_final_output, str)
    print("✓ Navigation output_fn completed successfully")
    
    print("3d. Validating navigation output format...")
    navigation_result_dict = json.loads(navigation_final_output)
    validate_output_format(navigation_result_dict)
    
    # Step 4: Test chat pipeline
    print("4. Testing chat pipeline...")
    print("4a. Testing input_fn for chat...")
    parsed_chat_input = input_fn(chat_json_input, "application/json")
    assert isinstance(parsed_chat_input, dict)
    assert parsed_chat_input["task"] == "chat"
    print("✓ Chat input_fn processed successfully")
    
    print("4b. Testing predict_fn for chat...")
    chat_prediction = predict_fn(parsed_chat_input, pipeline)
    assert isinstance(chat_prediction, str)
    print("✓ Chat predict_fn completed successfully")
    
    print("4c. Testing output_fn for chat...")
    chat_final_output = output_fn(chat_prediction, "application/json")
    assert isinstance(chat_final_output, str)
    print("✓ Chat output_fn completed successfully")
    
    print("4d. Validating chat output format...")
    chat_result_dict = json.loads(chat_final_output)
    validate_chat_output_format(chat_result_dict)
    
    print("\n" + "="*60)
    print("FULL PIPELINE TEST RESULTS:")
    print("="*60)
    print("\nNAVIGATION PIPELINE RESULT:")
    print("-" * 30)
    pprint(navigation_result_dict)
    # {'response': 'The image shows a street scene with a sidewalk running along the '
    #             "right side of the frame. On the left side, there's a set of "
    #             'outdoor stairs leading up to a building with a black iron '
    #             'railing and a stone facade. The stairs have a decorative black '
    #             'iron design on the risers. \n'
    #             '\n'
    #             'The sidewalk is made of concrete and is relatively wide. There '
    #             'are two parked cars along the right side of the sidewalk. One is '
    #             'a silver station wagon and the other is a darker silver sedan. A '
    #             'tree with a thick trunk is growing in the middle of the '
    #             "sidewalk, slightly to the right of the center. There's a small "
    #             'stone or brick area around the base of the tree. \n'
    #             '\n'
    #             'The railing on the left side of the stairs is made of black iron '
    #             'bars and has a decorative pattern. There are also black iron '
    #             'posts supporting the railing. \n'
    #             '\n'
    #             '**Obstacles:**\n'
    #             '\n'
    #             '* **Stairs:** There are outdoor stairs on the left side of the '
    #             'frame.\n'
    #             '* **Tree:** A tree is growing in the middle of the sidewalk.\n'
    #             '* **Parked Cars:** There are parked cars on the right side of '
    #             'the sidewalk.\n'
    #             '* **Railing:** The black iron railing on the left side of the '
    #             'stairs.\n'
    #             '\n'
    #             '\n'
    #             '\n'
    #             '**To reach the sidewalk:**\n'
    #             '\n'
    #             'Based on the image, to reach the sidewalk, you should **go '
    #             'right**. The sidewalk is on the right side of the frame, and the '
    #             'stairs are on the left. You would need to navigate around the '
    #             'tree and the parked cars to get to the sidewalk.\n'
    #             '\n'
    #             '\n'
    #             '\n'}
    
    print("\nCHAT PIPELINE RESULT:")
    print("-" * 20)
    pprint(chat_result_dict)
    # {'response': 'The image shows a street scene with a sidewalk running along the '
    #          "right side of the frame. On the left side, there's a set of "
    #          'outdoor stairs leading up to a building with a black iron '
    #          'railing and a stone facade. The stairs have a decorative black '
    #          'iron railing with geometric patterns. \n'
    #          '\n'
    #          'The sidewalk is made of concrete and is relatively wide. There '
    #          'are two parked cars along the right side of the sidewalk. One is '
    #          'a silver station wagon and the other is a gray sedan. A tree '
    #          'with a thick trunk is growing in the middle of the sidewalk, '
    #          "slightly to the right of the center. There's a small stone "
    #          'pathway around the base of the tree. \n'
    #          '\n'
    #          'The overall scene appears to be a typical urban environment. \n'
    #          '\n'
    #          'To reach the sidewalk, you should go **forward**. The stairs on '
    #          'the left lead to a higher level, so you need to proceed forward '
    #          'to access the sidewalk.'}

    print("="*60)
    print("✓ All tests passed! Both navigation and chat pipelines working correctly.")
    
    # Step 5: Create unified sample payload for inference recommendations (only if requested)
    if create_payload:
        print("5. Creating unified sample payload for inference recommendations...")
        create_sample_payload(navigation_input_data, chat_input_data)
        print("✓ Unified sample payload created successfully")
    
    return navigation_result_dict, chat_result_dict


# Requirements:
# - You have the local artifacts for the model (have ran 'python prepare_model_files.py')
# - Make sure you've installed the dependencies in requirements.txt with 'pip install -r src/requirements.txt'

if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent.absolute()
    
    # Always untar model artifacts first
    ARTIFACTS_DIR = untar_model_artifacts()
    
    # Run the full pipeline test with payload creation
    run_full_pipeline_test(str(ARTIFACTS_DIR), create_payload=True)
