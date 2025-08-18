import base64
import json
import logging
import os
import pathlib
import time
from typing import Any, Dict, List, Literal
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from transformers import AutoProcessor, Gemma3nForConditionalGeneration
import torch


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GemmaModelManager:
    """Manages the shared Gemma model and processor instances"""
    
    def __init__(self, model_dir_or_id):
        start = time.time()
        self.model = Gemma3nForConditionalGeneration.from_pretrained(
            model_dir_or_id, 
            device_map="auto", 
            torch_dtype=torch.bfloat16
        ).eval()
        logger.debug(f"Loaded model in {time.time()-start: .2f}s")
        
        start = time.time()
        self.processor = AutoProcessor.from_pretrained(model_dir_or_id)
        logger.debug(f"Loaded processor in {time.time()-start: .2f}s")


class PipelineStrategy(ABC):
    """Abstract base class for pipeline strategies"""
    
    @abstractmethod
    def get_prompt(self, **kwargs) -> List[Dict]:
        """Generate the prompt for this pipeline type"""
        pass
    
    @abstractmethod
    def predict(self, model_manager: GemmaModelManager, **kwargs) -> str:
        """Execute prediction using the model manager"""
        pass


class NavigationStrategy(PipelineStrategy):
    """Strategy for navigation-specific prompts and predictions"""
    
    def get_prompt(self, image: str, goal: str) -> List[Dict]:
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
                        "text": f"# First describe this image in detail and obstacles.\n# Finally answer the question\nTo reach the {goal} what should I do: go right, left, forward?"
                    }
                ]
            }
        ]
    
    def predict(self, model_manager: GemmaModelManager, image: str, goal: str) -> str:
        """
        image: str
            Base64 image
        goal: str
            The goal of the navigation. E.g. to reach the object "chair" we put goal="chair"
        """
        prompt = self.get_prompt(image, goal)
        
        inputs = model_manager.processor.apply_chat_template(
            prompt,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model_manager.model.device, dtype=torch.bfloat16)

        input_len = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            generation = model_manager.model.generate(**inputs, max_new_tokens=500, do_sample=False)
            generation = generation[0][input_len:]

        return model_manager.processor.decode(generation, skip_special_tokens=True)


class ChatStrategy(PipelineStrategy):
    """Chat strategy supporting multiple content types"""
    
    def get_prompt(self, content_items: List[Dict]) -> List[Dict]:
        """Build prompt from content items"""
        user_content = []
        
        for item in content_items:
            content_type = item["type"]
            content_value = item["value"]
            user_content.append({"type": content_type, content_type: content_value})
        
        return [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful visual assistant for visually impaired people. You don't have access to any external tool, so if you are unable to help the user explain that."}]
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    
    def predict(self, model_manager: GemmaModelManager, content_items: List[Dict]) -> str:
        """Chat prediction with multiple content types"""
        prompt = self.get_prompt(content_items)
        
        inputs = model_manager.processor.apply_chat_template(
            prompt,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model_manager.model.device, dtype=torch.bfloat16)

        input_len = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            generation = model_manager.model.generate(**inputs, max_new_tokens=500, do_sample=False)
            generation = generation[0][input_len:]

        return model_manager.processor.decode(generation, skip_special_tokens=True)


class UnifiedPipeline:
    """Unified pipeline that uses strategy pattern for different use cases"""
    
    def __init__(self, model_dir_or_id):
        self.model_manager = GemmaModelManager(model_dir_or_id)
        self.strategies = {
            "navigation": NavigationStrategy(),
            "chat": ChatStrategy()
        }
    
    def predict(self, pipeline_type: str, **kwargs) -> str:
        """
        Execute prediction based on pipeline type
        
        Args:
            pipeline_type: "navigation" or "chat"
            **kwargs: Arguments specific to the pipeline type
        
        Returns:
            str: Model prediction
        """
        if pipeline_type not in self.strategies:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}. Available: {list(self.strategies.keys())}")
        
        strategy = self.strategies[pipeline_type]
        return strategy.predict(self.model_manager, **kwargs)


def model_fn(model_dir: str):
    return UnifiedPipeline(model_dir)


class MessageContent(BaseModel):
    """Content item for chat messages"""
    type: Literal["image", "text", "audio"]
    value: str = Field(..., description="Content value (text string, base64 image, or base64 audio)")


class NavigationPayload(BaseModel):
    """Payload for navigation task"""
    image: str = Field(..., description="Base64 encoded image")
    goal: str = Field(..., description="Navigation goal/target")


class ChatPayload(BaseModel):
    """Payload for chat task"""
    content: List[MessageContent] = Field(..., min_items=1, description="List of message content items")


class TaskInput(BaseModel):
    """Main input structure for all tasks"""
    task: Literal["chat", "navigation"]
    payload: NavigationPayload | ChatPayload = Field(..., description="Task-specific payload")


def input_fn(input_data: Any, content_type: str) -> Dict:
    """Validate input and enforce security controls."""
    if content_type != "application/json":
        raise ValueError("Content type must be application/json")
    
    try:
        data = json.loads(input_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Validate the complete input structure
    validated = TaskInput.model_validate(data)
    
    return validated.model_dump()


def predict_fn(payload: Dict, pipeline: UnifiedPipeline) -> str:
    """Execute prediction. All validation is already done in input_fn."""
    task = payload["task"]
    task_payload = payload["payload"]
    
    if task == "navigation":
        return pipeline.predict("navigation", **task_payload)
    else:  # task == "chat"
        return pipeline.predict("chat", content_items=task_payload["content"])


class InferenceResponse(BaseModel):
    response: str


def output_fn(prediction: str, accept: str) -> str:
    if accept == "application/json":
        return InferenceResponse(response=prediction).model_dump_json()
    else:
        raise ValueError("Accept type must be application/json")