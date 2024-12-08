from pydantic import BaseModel
from typing import Optional, Dict, Any

class LawyerProfile(BaseModel):
    """Data model for scraped lawyer information"""
    url: str
    raw_content: str
    structured_data: Dict[str, Any]