"""
LLM Service using Google Gemini API

This service handles text generation using Google's Gemini AI model.
Gemini is a family of large language models that excel at understanding 
and generating natural language text.
"""
import os
from google import genai


class LLMService:
    """
    Service for generating text using Google Gemini API
    
    Uses the official google-genai SDK to interact with Gemini models.
    Supports various Gemini models (gemini-2.5-flash, gemini-pro, etc.)
    """
    
    def __init__(
        self,
        gemini_api_key: str,
        gemini_model: str = "gemini-2.5-flash",
        max_context_length: int = 2000,
    ) -> None:
        """
        Initialize LLM service with Gemini API credentials
        
        Args:
            gemini_api_key: Google Gemini API key (get from https://makersuite.google.com/app/apikey)
            gemini_model: Model to use (gemini-2.5-flash is fast and cost-effective)
            max_context_length: Maximum tokens to use for context (to avoid exceeding model limits)
        """
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.max_context_length = max_context_length
        
        # Set API key in environment for the SDK to access
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        
        # Initialize the Gemini client (official SDK)
        self.client = genai.Client()
        print(f"✅ LLM Service initialized with model: {gemini_model}")

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Google Gemini API (main entry point)
        
        Args:
            prompt: The text prompt to send to Gemini
            
        Returns:
            Generated text response from Gemini
        """
        return self._generate_gemini(prompt)

    def _generate_gemini(self, prompt: str) -> str:
        """
        Internal method to call Gemini API using official SDK
        
        This method:
        1. Validates API key is present
        2. Calls Gemini's generate_content endpoint
        3. Extracts text from response
        4. Handles errors gracefully
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            Generated text or error message
        """
        if not self.gemini_api_key:
            print("❌ [LLM] Error: No API key configured")
            return "Error: Gemini API key is not configured."

        try:
            # Call Gemini API with the prompt
            # The model will generate a response based on the context provided
            print(f"🤖 [LLM] Sending request to {self.gemini_model}...")
            response = self.client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            
            # Extract text from response
            if response and response.text:
                print(f"✅ [LLM] Response received ({len(response.text)} chars)")
                return response.text.strip()
            else:
                print("⚠️  [LLM] Warning: Empty response from Gemini")
                return "Unable to generate an answer."
                
        except Exception as e:
            # Log detailed error for debugging
            print(f"❌ [LLM] Error calling Gemini API: {str(e)}")
            return f"Error generating answer: {e}"
