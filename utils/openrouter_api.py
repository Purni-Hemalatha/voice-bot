import requests
import json
from config import Config

class OpenRouterAPI:
    """Handles API communication with OpenRouter for AI text generation."""
    
    def __init__(self):
        self.config = Config()
        self.base_url = self.config.OPENROUTER_BASE_URL
        self.api_key = self.config.OPENROUTER_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Voice Chatbot"
        }
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
    
    def get_available_models(self):
        """Get list of available models from OpenRouter."""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models: {e}")
            return None
    
    def generate_response(self, user_input, model=None, conversation_history=None):
        """Generate AI response using OpenRouter API."""
        if not model:
            model = self.config.DEFAULT_MODEL
        
        # Prepare conversation messages
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            "stream": False
        }
        
        try:
            print(f"Sending request to OpenRouter API with model: {model}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                ai_response = response_data['choices'][0]['message']['content']
                print(f"AI Response received: {ai_response[:100]}...")
                return ai_response
            else:
                print("No response choices found in API response")
                return "I'm sorry, I couldn't generate a response."
                
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenRouter API: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response content: {e.response.text}")
            return "I'm sorry, I'm having trouble connecting to the AI service."
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return "I'm sorry, I received an invalid response from the AI service."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "I'm sorry, an unexpected error occurred."
    
    def generate_streaming_response(self, user_input, model=None, conversation_history=None):
        """Generate streaming AI response using OpenRouter API."""
        if not model:
            model = self.config.DEFAULT_MODEL
        
        # Prepare conversation messages
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Prepare request payload for streaming
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            "stream": True
        }
        
        try:
            print(f"Sending streaming request to OpenRouter API with model: {model}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30,
                stream=True
            )
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        line = line[6:]  # Remove 'data: ' prefix
                        if line.strip() == '[DONE]':
                            break
                        try:
                            chunk_data = json.loads(line)
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                delta = chunk_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    yield content
                        except json.JSONDecodeError:
                            continue
            
            return full_response
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling OpenRouter API: {e}")
            yield "I'm sorry, I'm having trouble connecting to the AI service."
        except Exception as e:
            print(f"Unexpected error: {e}")
            yield "I'm sorry, an unexpected error occurred."
    
    def test_connection(self):
        """Test the connection to OpenRouter API."""
        try:
            models = self.get_available_models()
            if models:
                print("✓ Successfully connected to OpenRouter API")
                print(f"✓ Found {len(models.get('data', []))} available models")
                return True
            else:
                print("✗ Failed to connect to OpenRouter API")
                return False
        except Exception as e:
            print(f"✗ Connection test failed: {e}")
            return False
    
    def get_model_info(self, model_name):
        """Get information about a specific model."""
        models = self.get_available_models()
        if models and 'data' in models:
            for model in models['data']:
                if model['id'] == model_name:
                    return model
        return None