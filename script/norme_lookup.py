# norme_lookup.py
from typing import List, Dict
from difflib import SequenceMatcher

def similar(a: str, b: str) -> float:
    """Retourne un score de similarité entre 0 et 1"""
    return SequenceMatcher(None, a, b).ratio()

def get_norme_from_db(observation: str, prescriptions: List[Dict]) -> str:
    """
    Cherche le document de la prescription le plus proche de l'observation
    et retourne l'ART_LIBELLE associé.
    
    Args:
        observation: texte saisi par l'utilisateur
        prescriptions: liste de dict avec au moins 'contenu' et 'ART_LIBELLE'
    
    Returns:
        str: Norme trouvée ou message d'erreur
    """
    if not prescriptions:
        return "❌ Base de prescriptions vide."

    best_score = 0
    best_doc = None

    for doc in prescriptions:
        contenu = doc.get("contenu", "")
        score = similar(observation.lower(), contenu.lower())
        if score > best_score:
            best_score = score
            best_doc = doc

    if best_doc and best_score > 0.5:  # seuil ajustable
        return f"🤖 Norme associée :\n{best_doc.get('ART_LIBELLE')}"
    else:
        return "❌ Aucune norme pertinente trouvée pour cette observation."
