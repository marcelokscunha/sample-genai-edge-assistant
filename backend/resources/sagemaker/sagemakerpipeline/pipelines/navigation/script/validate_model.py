import base64
import os
import pathlib
from pprint import pprint

from src.inference import model_fn, predict_fn

def get_base64_from_image(image_path: str) -> str:
    """Convert image file to base64 data URI format."""
    with open(image_path, 'rb') as img_file:
        b64_bytes = base64.b64encode(img_file.read())
        b64_str = b64_bytes.decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_str}"
    return data_uri


# Requirements:
# - You have the local artifacts for the model (have ran 'python prepare_model_files.py')
# - Make sure you've installed the dependencies in requirements.txt with 'pip install -r core/requirements.txt'

if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent.absolute()
    ARTIFACTS_DIR = HERE / "ARTIFACTS" / "model"

    if not ARTIFACTS_DIR.exists():
        raise RuntimeError("ARTIFACTS directory does not exist. Please run the prepare_model_files.py script first.")

    print(f"Predicting with test data...")
    pipeline = model_fn(str(ARTIFACTS_DIR))
    payload = {
        "image": get_base64_from_image(HERE.parent / "data" / "samples" / "sidewalk.jpg"),
        "nav_goal": "sidewalk"
    }

    pprint(predict_fn(payload, pipeline))
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