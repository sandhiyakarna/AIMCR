import requests
from typing import Dict, Any, Optional
from app.core.config import settings

class OllamaService:
    @staticmethod
    def is_available(timeout: float = 2.0) -> bool:
        """
        Checks if the local Ollama service is up and running.
        """
        url = f"{settings.OLLAMA_API_BASE}/api/tags"
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def generate(prompt: str, system_prompt: Optional[str] = None, timeout: float = 12.0) -> Dict[str, Any]:
        """
        Sends a query to local Ollama and returns structured results.
        Never modifies any forensic evidence.
        """
        url = f"{settings.OLLAMA_API_BASE}/api/generate"
        
        # Combine system prompt with the main prompt if present
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("response", "").strip(),
                    "model": settings.OLLAMA_MODEL,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "response": "",
                    "model": settings.OLLAMA_MODEL,
                    "error": f"Ollama service returned status code {response.status_code}"
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response": "",
                "model": settings.OLLAMA_MODEL,
                "error": "Ollama request timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "model": settings.OLLAMA_MODEL,
                "error": f"Ollama connection error: {str(e)}"
            }
