import os
import json
import random
import requests
from typing import Dict, List, Optional, Tuple, Union, Any

class LLMClient:
    """
    A client for interacting with various LLM providers to extract entities from text.
    Supports both local Ollama and cloud-based LLMs like OpenAI and Anthropic.
    """
    
    # Default colors for entity types
    DEFAULT_COLORS = {
        "person": "#FF5733",     # Red-orange
        "project": "#33A1FF",    # Blue
        "company": "#33FF57",    # Green
        "topic": "#A133FF",      # Purple
        "location": "#FFD700",   # Gold
        "date": "#00CED1",       # Turquoise
        "other": "#808080"       # Gray
    }
    
    def __init__(self, provider: str = "ollama", config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM client.
        
        Args:
            provider: The LLM provider to use ('ollama', 'openai', or 'anthropic')
            config: Configuration for the LLM provider
        """
        self.provider = provider.lower()
        self.config = config or {}
        
        # Set default configurations if not provided
        if self.provider == "ollama":
            self.config.setdefault("base_url", "http://host.docker.internal:11434")
            self.config.setdefault("model", "gemma3:12b")
        elif self.provider == "openai":
            self.config.setdefault("api_key", os.environ.get("OPENAI_API_KEY", ""))
            self.config.setdefault("model", "gpt-4o")
        elif self.provider == "anthropic":
            self.config.setdefault("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
            self.config.setdefault("model", "claude-3-opus-20240229")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Check connectivity during initialization
        self.is_connected = self.check_connectivity()
        if not self.is_connected:
            print(f"Warning: Could not connect to {self.provider} LLM service. Entity extraction may not work.")
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extract entities from the given text using the configured LLM provider.
        
        Args:
            text: The text to extract entities from
            
        Returns:
            A list of entity dictionaries with 'type', 'label', and 'color' keys
        """
        if self.provider == "ollama":
            return self._extract_with_ollama(text)
        elif self.provider == "openai":
            return self._extract_with_openai(text)
        elif self.provider == "anthropic":
            return self._extract_with_anthropic(text)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _extract_with_ollama(self, text: str) -> List[Dict[str, str]]:
        """Extract entities using local Ollama."""
        try:
            prompt = self._create_extraction_prompt(text)
            
            response = requests.post(
                f"{self.config['base_url']}/api/generate",
                json={
                    "model": self.config["model"],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for more deterministic results
                    }
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse the response to extract entities
            return self._parse_llm_response(result["response"])
            
        except Exception as e:
            print(f"Error extracting entities with Ollama: {e}")
            return []
    
    def _extract_with_openai(self, text: str) -> List[Dict[str, str]]:
        """Extract entities using OpenAI API."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.config["api_key"])
            
            prompt = self._create_extraction_prompt(text)
            
            response = client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": "You are an expert at extracting named entities from text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
            )
            
            # Parse the response to extract entities
            return self._parse_llm_response(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error extracting entities with OpenAI: {e}")
            return []
    
    def _extract_with_anthropic(self, text: str) -> List[Dict[str, str]]:
        """Extract entities using Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.config["api_key"])
            
            prompt = self._create_extraction_prompt(text)
            
            response = client.messages.create(
                model=self.config["model"],
                max_tokens=1000,
                system="You are an expert at extracting named entities from text.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
            )
            
            # Parse the response to extract entities
            return self._parse_llm_response(response.content[0].text)
            
        except Exception as e:
            print(f"Error extracting entities with Anthropic: {e}")
            return []
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create a prompt for entity extraction."""
        return f"""
Extract the following entity types from this text:
- person: Names of people mentioned
- project: Project names or initiatives
- company: Company or organization names
- topic: Key topics or subjects discussed
- location: Places mentioned
- date: Dates or time periods mentioned

Text to analyze:
{text}

Return ONLY a JSON array of objects with 'type' and 'label' properties, like this:
[
  {{"type": "person", "label": "John Smith"}},
  {{"type": "company", "label": "Acme Corp"}},
  {{"type": "topic", "label": "AI Development"}}
]

Do not include any explanations or other text, just the JSON array.
"""
    
    def check_connectivity(self) -> bool:
        """
        Check if the LLM service is reachable.
        
        Returns:
            True if the service is reachable, False otherwise
        """
        try:
            if self.provider == "ollama":
                # Check if Ollama API is reachable
                response = requests.get(
                    f"{self.config['base_url']}/api/tags",
                    timeout=5
                )
                return response.status_code == 200
            
            elif self.provider == "openai":
                # Check if OpenAI API key is valid
                if not self.config.get("api_key"):
                    print("OpenAI API key is not configured")
                    return False
                
                import openai
                client = openai.OpenAI(api_key=self.config["api_key"])
                # Just list models to check connectivity
                client.models.list(limit=1)
                return True
            
            elif self.provider == "anthropic":
                # Check if Anthropic API key is valid
                if not self.config.get("api_key"):
                    print("Anthropic API key is not configured")
                    return False
                
                import anthropic
                client = anthropic.Anthropic(api_key=self.config["api_key"])
                # Simple request to check connectivity
                client.messages.create(
                    model=self.config["model"],
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                return True
            
            return False
        
        except Exception as e:
            print(f"Error checking connectivity to {self.provider}: {e}")
            return False
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extract entities from the given text using the configured LLM provider.
        
        Args:
            text: The text to extract entities from
            
        Returns:
            A list of entity dictionaries with 'type', 'label', and 'color' keys
        """
        # Check connectivity before attempting extraction
        if not self.is_connected and not self.check_connectivity():
            print(f"Cannot extract entities: {self.provider} LLM service is not reachable")
            return []
        
        if self.provider == "ollama":
            return self._extract_with_ollama(text)
        elif self.provider == "openai":
            return self._extract_with_openai(text)
        elif self.provider == "anthropic":
            return self._extract_with_anthropic(text)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _parse_llm_response(self, response_text: str) -> List[Dict[str, str]]:
        """
        Parse the LLM response to extract entities.
        
        Args:
            response_text: The raw text response from the LLM
            
        Returns:
            A list of entity dictionaries with 'type', 'label', and 'color' keys
        """
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                entities = json.loads(json_str)
                
                # Add colors to entities
                for entity in entities:
                    entity_type = entity.get("type", "other").lower()
                    entity["color"] = self.DEFAULT_COLORS.get(entity_type, self.DEFAULT_COLORS["other"])
                
                return entities
            else:
                print("No valid JSON found in LLM response")
                return []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Response text: {response_text}")
            return []
        except Exception as e:
            print(f"Unexpected error parsing LLM response: {e}")
            return []

# Example usage:
# client = LLMClient(provider="ollama", config={"model": "llama3"})
# entities = client.extract_entities("John from Acme Corp is working on the AI project with Sarah.")
# print(entities)
