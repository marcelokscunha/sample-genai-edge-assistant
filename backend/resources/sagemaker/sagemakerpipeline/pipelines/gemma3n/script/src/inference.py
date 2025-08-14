import base64
import json
import logging
import os
import pathlib
import time
from typing import Any, Dict, List, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel
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
    
    def get_prompt(self, image: str, nav_goal: str) -> List[Dict]:
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
    
    def predict(self, model_manager: GemmaModelManager, image: str, nav_goal: str) -> str:
        """
        image: str
            Base64 image
        nav_goal: str
            The goal of the navigation. E.g. to reach the object "chair" we put nav_goal="chair"
        """
        prompt = self.get_prompt(image, nav_goal)
        
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
    """Strategy for chat-specific prompts and predictions with multimodal support"""
    
    def get_prompt(self, messages: List[Dict]) -> List[Dict]:
        """
        messages: List of message dicts with flexible content
        Each message can contain:
        - role: str ("user", "assistant", "system")
        - content: List[Dict] with flexible multimodal content
          - {"type": "text", "text": str}
          - {"type": "image", "image": str} (base64)
          - {"type": "audio", "audio": str} (base64 or processed)
        """
        formatted_messages = []
        
        # Add system message if not present
        has_system = any(msg.get("role") == "system" for msg in messages)
        if not has_system:
            formatted_messages.append({
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful visual assistant for visually impaired people."}]
            })
        
        for msg in messages:
            content = []
            
            # Handle different content formats
            if isinstance(msg.get("content"), str):
                # Simple text message
                content.append({"type": "text", "text": msg["content"]})
            elif isinstance(msg.get("content"), list):
                # Already formatted multimodal content
                for item in msg["content"]:
                    if item.get("type") == "audio":
                        # For now, represent audio as text placeholder
                        # TODO: Implement audio transcription if needed
                        content.append({"type": "text", "text": "[Audio message received]"})
                    else:
                        content.append(item)
            else:
                # Handle legacy format with separate fields
                if msg.get("text"):
                    content.append({"type": "text", "text": msg["text"]})
                
                for image in msg.get("images", []):
                    content.append({"type": "image", "image": image})
                
                for audio in msg.get("audio", []):
                    # For now, represent audio as text placeholder
                    content.append({"type": "text", "text": "[Audio message received]"})
            
            if content:
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })
        
        return formatted_messages
    
    def predict(self, model_manager: GemmaModelManager, messages: List[Dict]) -> str:
        """
        messages: List of message dicts with flexible multimodal content
        """
        prompt = self.get_prompt(messages)
        
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


class NavigationInput(BaseModel):
    image: str  # Base64 encoded image
    nav_goal: str


class ChatInput(BaseModel):
    messages: List[Dict]  # List of message dicts with multimodal content


class InferenceInput(BaseModel):
    pipeline_type: str  # "navigation" or "chat"
    # Navigation fields (optional)
    image: Union[str, None] = None
    nav_goal: Union[str, None] = None
    # Chat fields (optional)
    messages: Union[List[Dict], None] = None


def input_fn(input_data: Any, content_type: str) -> Dict:
    """
    Deserialize and validate input data for model inference
    
    Args:
        input_data: Raw input data (byte buffer)
        content_type: Content type of the input (must be 'application/json')
    
    Returns:
        dict: Validated input data
        
    Raises:
        ValueError: If content type is not 'application/json' or if data validation fails
    """
    if content_type == "application/json":
        validated_input = InferenceInput.model_validate_json(input_data)
        payload = validated_input.model_dump()
        
        # Validate pipeline-specific requirements
        pipeline_type = payload["pipeline_type"]
        
        if pipeline_type == "navigation":
            if not payload.get("image") or not payload.get("nav_goal"):
                raise ValueError("Navigation pipeline requires 'image' and 'nav_goal' fields")
        elif pipeline_type == "chat":
            if not payload.get("messages"):
                raise ValueError("Chat pipeline requires 'messages' field")
        else:
            raise ValueError(f"Unknown pipeline_type: {pipeline_type}. Must be 'navigation' or 'chat'")
        
        return payload
    else:
        raise ValueError("Content type must be application/json")


def predict_fn(payload: Dict, pipeline: UnifiedPipeline) -> str:
    pipeline_type = payload.pop("pipeline_type")
    return pipeline.predict(pipeline_type, **payload)


class InferenceResponse(BaseModel):
    response: str


def output_fn(prediction: str, accept: str) -> str:
    if accept == "application/json":
        return InferenceResponse(response=prediction).model_dump_json()
    else:
        raise ValueError("Accept type must be application/json")