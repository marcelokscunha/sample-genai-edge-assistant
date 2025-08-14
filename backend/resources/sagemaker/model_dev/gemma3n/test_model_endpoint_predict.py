
import os
import pathlib
from pprint import pprint

import boto3
import sagemaker
from sagemaker.predictor import Predictor

from test_utils import get_base64_from_image

# Requirements:
# - You have a SageMaker endpoint running (already ran 'python test_model_endpoint_deploy.py')

if __name__ == "__main__":
    HERE = pathlib.Path(__file__).parent

    default_ep_name = "gemma3n-test-endpoint"
    endpoint_name = input(f"Name of SageMaker endpoint to invoke: (press enter to default '{default_ep_name}'): ") 
    if endpoint_name=="":
        endpoint_name = default_ep_name
    print(f"Invoking endpoint '{endpoint_name}'")
    predictor = Predictor(endpoint_name)
    
    # Example inference
    sample_input = {
        "image": get_base64_from_image(HERE.parent / "data" / "samples" / "sidewalk.jpg"),
        "nav_goal": "sidewalk"
    }
    
    # Make prediction
    predictor.serializer = sagemaker.serializers.JSONSerializer()
    predictor.deserializer = sagemaker.deserializers.JSONDeserializer()
    result = predictor.predict(sample_input)
    print(f"Prediction result:")
    pprint(result)
    # OUTPUT:
    # Prediction result:
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

    delete_ep = input("Should we delete the endpoint? [y/N]: ") == "y"
    if delete_ep:
        print("Cleaning up (deleting endpoint)")
        predictor.delete_endpoint()
        print("Deleted successfully!")
