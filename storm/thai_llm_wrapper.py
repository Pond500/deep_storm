"""
Thai Language Wrapper for Co-STORM
Wraps LiteLLM model to add Thai language instructions
"""

from typing import Any, Optional
import dspy
import os
import litellm


class ThaiLitellmModel:
    """Wrapper around LitellmModel that adds Thai language instructions"""
    
    def __init__(self, model, **kwargs):
        from knowledge_storm.lm import LitellmModel
        
        # Always configure LiteLLM to use OpenRouter.
        # OPENAI_API_KEY and OPENAI_API_BASE are set globally in app.py,
        # but we also set litellm module-level vars as a belt-and-suspenders approach.
        api_key = kwargs.get('api_key') or os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
        if api_key:
            os.environ['OPENROUTER_API_KEY'] = api_key
            os.environ['OPENAI_API_KEY'] = api_key
            litellm.api_key = api_key
        
        litellm.api_base = os.environ.get('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
        
        self.base_model = LitellmModel(model=model, **kwargs)
        self.thai_instruction = (
            "\n\n**IMPORTANT: You MUST respond in Thai language (ภาษาไทย) for all outputs. "
            "Do not use English unless it's a technical term that has no Thai equivalent. "
            "Write naturally in Thai.**"
        )
    
    def __call__(self, prompt=None, **kwargs):
        """Intercept calls and add Thai instruction"""
        if prompt:
            prompt = prompt + self.thai_instruction
        elif 'messages' in kwargs:
            # Add Thai instruction to system message
            messages = kwargs['messages']
            if messages and messages[0].get('role') == 'system':
                messages[0]['content'] = messages[0]['content'] + self.thai_instruction
            else:
                messages.insert(0, {
                    'role': 'system',
                    'content': 'You are a helpful assistant.' + self.thai_instruction
                })
            kwargs['messages'] = messages
        
        return self.base_model(prompt=prompt, **kwargs)
    
    def __getattr__(self, name):
        """Proxy all other attributes to base model"""
        return getattr(self.base_model, name)
    
    def copy(self, **kwargs):
        """Support dspy's copy method"""
        return ThaiLitellmModel(
            model=self.base_model.model,  # .model not .model_name
            **{**self.base_model.kwargs, **kwargs}
        )
