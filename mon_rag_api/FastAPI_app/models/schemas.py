from pydantic import BaseModel, Field
from typing import List, Optional

class AutocompleteRequest(BaseModel):
    """Requête pour l'autocomplétion"""
    query: str = Field(..., description="Texte à compléter")
    max_suggestions: Optional[int] = Field(10, ge=1, le=50)

class AutocompleteResponse(BaseModel):
    """Réponse d'autocomplétion"""
    query: str
    suggestions: List[str]
    count: int

class HealthResponse(BaseModel):
    """Réponse de santé"""
    status: str
    engine_ready: bool
    vector_store_ready: bool