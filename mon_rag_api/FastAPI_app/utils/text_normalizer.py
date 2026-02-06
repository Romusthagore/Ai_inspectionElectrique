import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Normalise le texte : minuscules + suppression accents
    """
    if not text:
        return ""
    
    # Minuscules
    text = text.lower()
    
    # Supprimer les accents
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Nettoyer
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# Cache pour améliorer les performances
_normalization_cache = {}

def normalize_cached(text: str) -> str:
    """Version avec cache de la normalisation"""
    if text in _normalization_cache:
        return _normalization_cache[text]
    
    normalized = normalize_text(text)
    _normalization_cache[text] = normalized
    return normalized