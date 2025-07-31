import os
import pathlib
import base64
import time

from transformers import AutoProcessor, Gemma3nForConditionalGeneration
import torch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NavigationPipeline:
        def __init__(self, model_dir_or_id):
            
            start = time.time()
            self.model = Gemma3nForConditionalGeneration.from_pretrained(model_dir_or_id, device_map="auto", torch_dtype=torch.bfloat16,).eval()
            logger.debug(f"Loaded model in {time.time()-start: .2f}s")
            
            start = time.time()
            self.processor = AutoProcessor.from_pretrained(model_dir_or_id)
            logger.debug(f"Loaded processor in {time.time()-start: .2f}s")

        def _get_prompt(self, image: str, nav_goal: str):
            return [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "You are a helpful visual assistant for visually impaired people."}]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image", 
                            "image": image
                        },
                        {
                            "type": "text", 
                            "text": f"# First describe this image in detail and obstacles.\n# Finally answer the question\nTo reach the {nav_goal} what should I do: go right, left, forward?"
                        }
                    ]
                }
            ]

        
        def predict(self, image: str, nav_goal: str) -> str:
            """
            image: str
                Base64 image
            nav_goal: str
                The goal of the navigation. E.g. to reach the object "chair" we put nav_goal="chair"
            """
            
            inputs = self.processor.apply_chat_template(
                self._get_prompt(image, nav_goal),
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self.model.device, dtype=torch.bfloat16)

            input_len = inputs["input_ids"].shape[-1]

            with torch.inference_mode():
                generation = self.model.generate(**inputs, max_new_tokens=500, do_sample=False)
                generation = generation[0][input_len:]

            return self.processor.decode(generation, skip_special_tokens=True)

def model_fn(model_dir):
    return NavigationPipeline(model_dir)

def predict_fn(payload, pipeline):
    return {"response": pipeline.predict(**payload)}

