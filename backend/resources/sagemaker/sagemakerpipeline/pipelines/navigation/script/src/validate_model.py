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
    """Validate that the output matches the expected format from the commented example."""
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
    
    print("✓ Output format validation passed")
    return True

# Requirements:
# - You have the local artifacts for the model (have ran 'python prepare_model_files.py')
# - Make sure you've installed the dependencies in requirements.txt with 'pip install -r core/requirements.txt'

if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent.absolute()
    
    # Always untar model artifacts first
    ARTIFACTS_DIR = untar_model_artifacts()
    
    print("Testing full inference pipeline...")
    
    # Step 1: Load model
    print("1. Loading model...")
    pipeline = model_fn(str(ARTIFACTS_DIR))
    print("✓ Model loaded successfully")
    
    # Step 2: Prepare input data as JSON string (as it would come from SageMaker endpoint)
    print("2. Preparing input data...")
    input_data = {
        "image": get_base64_from_image(HERE / "data" / "samples" / "sidewalk.jpg"),
        "nav_goal": "sidewalk"
    }
    json_input = json.dumps(input_data)
    print("✓ Input data prepared")
    
    # Step 3: Test input_fn
    print("3. Testing input_fn...")
    parsed_input = input_fn(json_input, "application/json")
    assert isinstance(parsed_input, dict)
    print("✓ input_fn processed successfully")
    
    # Step 4: Test predict_fn
    print("4. Testing predict_fn...")
    prediction = predict_fn(parsed_input, pipeline)
    assert isinstance(prediction, str)
    print("✓ predict_fn completed successfully")
    
    # Step 5: Test output_fn
    print("5. Testing output_fn...")
    final_output = output_fn(prediction, "application/json")
    assert isinstance(final_output, str)
    print("✓ output_fn completed successfully")
    
    # Step 6: Parse and validate final output
    print("6. Validating output format...")
    result_dict = json.loads(final_output)
    validate_output_format(result_dict)
    
    print("\n" + "="*50)
    print("FULL PIPELINE TEST RESULTS:")
    print("="*50)
    pprint(result_dict)
    print("="*50)
    print("✓ All tests passed! Full inference pipeline working correctly.")
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