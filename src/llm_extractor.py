"""
LLM-based Structured Data Extraction Module
Supports Ollama (local LLMs)
"""
import json
import re
from typing import Dict, Optional, List
import requests
from config import Config

class LLMExtractor:
    """Extract structured data from text using LLM"""
    
    def __init__(self):
        """Initialize LLM extractor"""
        self.ollama_url = Config.OLLAMA_BASE_URL
        # Use mistral as default (smaller and more stable than llama3)
        self.model = "mistral"
    
    def create_extraction_prompt(self, text: str, fields: Optional[List[str]] = None) -> str:
        """
        Create a structured extraction prompt
        
        Args:
            text: Text to extract from
            fields: List of fields to extract
            
        Returns:
            Formatted prompt
        """
        if fields is None:
            fields = Config.EXTRACTION_FIELDS
        
        prompt = f"""You are a data extraction AI specialized in trade documents. Extract the following fields from the invoice text.

FIELDS TO EXTRACT:
{', '.join(fields)}

INVOICE TEXT:
{text}

INSTRUCTIONS:
1. Extract ONLY the requested fields
2. Return the data in valid JSON format
3. If a field is not found, use null
4. For dates, use ISO format (YYYY-MM-DD) if possible
5. For amounts, extract only the numeric value
6. For currency, use 3-letter ISO code (USD, EUR, etc.)

RESPOND WITH ONLY THE JSON OBJECT, NO EXPLANATIONS:
"""
        return prompt
    
    
    def extract_with_ollama(self, text: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Extract structured data using Ollama (local LLM)
        
        Args:
            text: Text to extract from
            fields: List of fields to extract
            
        Returns:
            Extracted data as dictionary
        """
        prompt = self.create_extraction_prompt(text, fields)
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1  # Low temperature for consistent JSON extraction
                },
                timeout=120  # Increased timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the response text
            generated_text = result.get("response", "").strip()
            
            # Try to parse as JSON (first try direct parsing)
            try:
                return json.loads(generated_text)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response (in case it has text before/after)
                import re
                json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                raise Exception(f"No valid JSON found in Ollama response: {generated_text[:200]}")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama request failed: {str(e)}. Make sure Ollama is running.")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Ollama response as JSON: {str(e)}")
    
    def extract(self, text: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Main extraction method using Ollama
        
        Args:
            text: Text to extract from
            fields: List of fields to extract
            
        Returns:
            Extracted data as dictionary
        """
        return self.extract_with_ollama(text, fields)
    
    def validate_extraction(self, extracted_data: Dict, required_fields: Optional[List[str]] = None) -> Dict:
        """
        Validate extracted data
        
        Args:
            extracted_data: Extracted data dictionary
            required_fields: List of required fields
            
        Returns:
            Validation result with warnings
        """
        if required_fields is None:
            required_fields = Config.EXTRACTION_FIELDS
        
        validation_result = {
            "is_valid": True,
            "missing_fields": [],
            "warnings": []
        }
        
        # Check for missing required fields
        for field in required_fields:
            if field not in extracted_data or extracted_data[field] is None:
                validation_result["missing_fields"].append(field)
                validation_result["is_valid"] = False
        
        # Check data types
        if "total_amount" in extracted_data:
            try:
                float(str(extracted_data["total_amount"]).replace(",", ""))
            except (ValueError, TypeError):
                validation_result["warnings"].append("total_amount may not be a valid number")
        
        return validation_result
