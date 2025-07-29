import pathlib
from pprint import pprint

from code.inference import model_fn, predict_fn
from test_utils import get_base64_from_image

if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent.absolute()
    ARTIFACTS_DIR = HERE / "ARTIFACTS"

    if not ARTIFACTS_DIR.exists():
        raise RuntimeError("ARTIFACTS directory does not exist. Please run the prepare_model_files.py script first.")

    print(f"Predicting with test data...")
    pipeline = model_fn(str(ARTIFACTS_DIR))
    payload = {
        "image": get_base64_from_image(HERE.parent / "data" / "samples" / "sidewalk.jpg"),
        "nav_goal": "sidewalk"
    }

    pprint(predict_fn(payload, pipeline))
