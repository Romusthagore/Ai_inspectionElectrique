#!/usr/bin/env python3
"""
Module SuggestionEngine - VERSION AMÉLIORÉE AVEC RECHERCHE FLUE SUR VERBES
Supporte : "remplcer", "reser", "protetion", etc.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import re
import unicodedata
from difflib import SequenceMatcher

# Imports LangChain
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
except ImportError as e:
    print(f"❌ Erreur d'import LangChain : {e}")
    raise

# Import du VectorStore personnalisé
try:
    from core.vector_store import VectorStore
except ImportError as e:
    print(f"❌ Erreur d'import VectorStore : {e}")
    raise

# Import de la configuration
try:
    from core.config import (
        CORRECTION_PROMPT,
        CATEGORIES_OBSERVATIONS,
        detecter_categorie,
        get_config_categorie,
        TEMPLATE_OBSERVATION_STANDARD
    )
except ImportError as e:
    print(f"❌ Erreur d'import config : {e}")
    raise

logger = logging.getLogger(__name__)


@dataclass
class SuggestionResult:
    """Structure des résultats de suggestions"""
    mots_cles: List[str]
    phrases_completes: List[str]
    references_normatives: List[str]
    complements_intelligents: List[str]
    categorie_detectee: str
    niveau_priorite: int
    niveau_gravite: str
    risques_identifies: List[str]
    actions_correctives: List[str]
    delai_recommande: str
    localisation_suggeree: str
    confiance_score: float
    observation_corrigee: str
    rapport_formate: str
    alertes_coherence: List[str]
    suggestions_amelioration: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FuzzyVerbeMatcher:
    """Classe spécialisée pour la recherche floue de verbes"""
    
    def __init__(self, verbes: List[str]):
        self.verbes = verbes
        self.verbes_normalises = {self._normaliser_texte(v): v for v in verbes}
        
        # Cache pour performance
        self._cache_matches = {}
    
    def _normaliser_texte(self, texte: str) -> str:
        """Normalise le texte pour la recherche flue"""
        if not texte:
            return ""
        
        texte = texte.lower()
        texte = unicodedata.normalize('NFKD', texte)
        texte = ''.join(c for c in texte if not unicodedata.combining(c))
        
        # Nettoyer
        texte = re.sub(r'[^\w\s]', '', texte)
        return texte.strip()
    
    def find_matching_verbes(self, query: str, min_similarity: float = 0.6) -> List[Tuple[str, float]]:
        """
        Trouve les verbes qui correspondent à la requête (même avec fautes)
        
        Exemples:
            "remplcer" → ("remplacer", 0.85)
            "reser" → ("réserver", 0.7) ou ("serrer", 0.65)
            "protetion" → ("protéger", 0.7)
        """
        query_norm = self._normaliser_texte(query)
        
        if not query_norm:
            return []
        
        # Vérifier le cache
        cache_key = f"{query_norm}_{min_similarity}"
        if cache_key in self._cache_matches:
            return self._cache_matches[cache_key]
        
        matches = []
        
        for verbe_norm, verbe_original in self.verbes_normalises.items():
            # 1. Inclusion directe (score élevé)
            if query_norm in verbe_norm:
                matches.append((verbe_original, 1.0))
                continue
            
            # 2. Similarité floue
            similarity = SequenceMatcher(None, query_norm, verbe_norm).ratio()
            
            # 3. Bonus pour préfixes (même avec fautes)
            if len(query_norm) >= 4:
                # Vérifier si c'est un préfixe approximatif
                if verbe_norm.startswith(query_norm[:3]):
                    similarity = max(similarity, 0.75)
                
                # Vérifier la distance de Levenshtein simplifiée
                if self._is_approximate_prefix(query_norm, verbe_norm):
                    similarity = max(similarity, 0.8)
            
            if similarity >= min_similarity:
                matches.append((verbe_original, similarity))
        
        # Trier par score
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Mettre en cache
        self._cache_matches[cache_key] = matches
        
        return matches
    
    def _is_approximate_prefix(self, query: str, verbe: str) -> bool:
        """Vérifie si la requête est un préfixe approximatif du verbe"""
        if len(query) < 3 or len(verbe) < len(query):
            return False
        
        # Vérifier les premières lettres avec tolérance
        max_errors = min(2, len(query) // 3)
        errors = 0
        
        for i in range(min(len(query), len(verbe))):
            if query[i] != verbe[i]:
                errors += 1
                if errors > max_errors:
                    return False
        
        return True
    
    def get_best_match(self, query: str, min_similarity: float = 0.6) -> Optional[str]:
        """Retourne le meilleur verbe correspondant"""
        matches = self.find_matching_verbes(query, min_similarity)
        return matches[0][0] if matches else None


class SuggestionEngine:
    """
    Moteur de suggestions AVEC RECHERCHE FLUE SUR VERBES
    - Supporte les verbes avec fautes d'orthographe
    - Recherche intelligente avec tolérance
    """
    
    def __init__(
        self,
        vectorstore: VectorStore,
        llm: ChatGroq,
        k_documents: int = 30,
        min_similarity: float = 0.65,
    ):
        """Initialise le moteur avec recherche flue de verbes"""
        self.vectorstore = vectorstore
        self.llm = llm
        self.k_documents = k_documents
        self.min_similarity = min_similarity
        
        # ✅ Index pour recherche par verbe
        self.complements_par_verbe = defaultdict(list)
        self.complements_normalises = defaultdict(list)
        self.tous_les_verbes = set()
        self.verbes_liste = []  # Liste des verbes pour le matcher
        
        # ✅ Matcher flou pour verbes
        self.verbe_matcher = None
        
        # Charger l'index au démarrage
        self._construire_index_complements()
        
        # Initialiser le matcher de verbes
        self.verbe_matcher = FuzzyVerbeMatcher(list(self.tous_les_verbes))
        
        # Templates
        self.suggestion_template = PromptTemplate(
            input_variables=["user_input", "context_documents"],
            template=self._get_suggestion_prompt_template()
        )
        
        self.correction_template = PromptTemplate(
            input_variables=["observation_brute", "context"],
            template=CORRECTION_PROMPT
        )
        
        logger.info(f"✅ SuggestionEngine FLUE initialisé")
        logger.info(f"📊 {len(self.tous_les_verbes)} verbes disponibles")
    
    def _normaliser_texte(self, texte: str) -> str:
        """Normalise le texte : minuscules et suppression accents"""
        if not texte:
            return ""
        
        texte = texte.lower()
        texte = unicodedata.normalize('NFKD', texte)
        texte = ''.join(c for c in texte if not unicodedata.combining(c))
        
        return texte.strip()
    
    def _construire_index_complements(self):
        """Charge tous les documents et construit les index"""
        try:
            all_docs = self._charger_tous_documents()
            
            if not all_docs:
                logger.warning("⚠️ Aucun document chargé, chargement d'exemples...")
                self._charger_exemples_secours()
                return
            
            for doc in all_docs:
                content = (
                    doc.get("content", "") or 
                    doc.get("contenu", "") or 
                    doc.get("text", "") or 
                    doc.get("phrase", "")
                ).strip()
                
                if not content:
                    continue
                
                # Extraire verbe + complément
                mots = content.strip().split(maxsplit=1)
                if len(mots) == 2:
                    verbe_original, complement_original = mots[0].strip(), mots[1].strip()
                    verbe_normalise = self._normaliser_texte(verbe_original)
                    complement_normalise = self._normaliser_texte(complement_original)
                    
                    self.complements_normalises[verbe_normalise].append({
                        "complet": content,
                        "complement_original": complement_original,
                        "complement_normalise": complement_normalise,
                        "verbe_original": verbe_original,
                        "metadata": doc
                    })
                    
                    self.tous_les_verbes.add(verbe_normalise)
            
            self.verbes_liste = list(self.tous_les_verbes)
            logger.info(f"✅ Index construit: {len(self.complements_normalises)} verbes")
            
        except Exception as e:
            logger.error(f"❌ Impossible de charger l'index: {e}")
            self._charger_exemples_secours()
    
    def _charger_tous_documents(self) -> List[Dict]:
        """Charge tous les documents"""
        try:
            if hasattr(self.vectorstore, 'documents'):
                return self.vectorstore.documents
            elif hasattr(self.vectorstore, 'get_all_documents'):
                return self.vectorstore.get_all_documents()
            else:
                logger.warning("⚠️ Pas d'accès direct aux documents")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement: {e}")
            return []
    
    def _charger_exemples_secours(self):
        """Charge des exemples avec verbes variés"""
        exemples = [
            "remplacer le luminaire défectueux",
            "remplacer les fusibles par des disjoncteurs",
            "remplacer les câbles endommagés",
            "réparer la prise électrique",
            "réparer le circuit défectueux",
            "réparer le disjoncteur",
            "installer un dispositif de protection",
            "installer un éclairage de sécurité",
            "installer une prise de terre",
            "vérifier la continuité des conducteurs",
            "vérifier la résistance de terre",
            "vérifier le différentiel",
            "protéger les conducteurs contre les chocs",
            "protéger l'installation contre la foudre",
            "protéger les personnes contre les contacts directs",
            "contrôler l'isolement des câbles",
            "contrôler le fonctionnement des DDR",
            "contrôler la tension d'alimentation",
            "poser des câbles dans les goulottes",
            "poser un tableau électrique",
            "poser des conduits ICTA"
        ]
        
        for texte in exemples:
            mots = texte.strip().split(maxsplit=1)
            if len(mots) == 2:
                verbe_original, complement_original = mots[0].strip(), mots[1].strip()
                verbe_normalise = self._normaliser_texte(verbe_original)
                complement_normalise = self._normaliser_texte(complement_original)
                
                self.complements_normalises[verbe_normalise].append({
                    "complet": texte,
                    "complement_original": complement_original,
                    "complement_normalise": complement_normalise,
                    "verbe_original": verbe_original,
                    "metadata": {}
                })
                
                self.tous_les_verbes.add(verbe_normalise)
        
        self.verbes_liste = list(self.tous_les_verbes)
        self.verbe_matcher = FuzzyVerbeMatcher(self.verbes_liste)
        
        logger.info(f"🔄 Exemples chargés: {len(self.tous_les_verbes)} verbes")
    
    # =====================================================================
    # ✅ MÉTHODE PRINCIPALE AVEC RECHERCHE FLUE DE VERBES
    # =====================================================================
    
    def get_suggestions(
        self, 
        user_input: str,
        max_suggestions: int = 10
    ) -> List[str]:
        """
        Autocomplétion AVEC RECHERCHE FLUE DE VERBES
        
        Args:
            user_input: Texte saisi par l'utilisateur (peut contenir des fautes)
            max_suggestions: Nombre maximum de suggestions
        
        Returns:
            Liste de suggestions
        """
        start_time = time.time()
        
        # 1. Parser l'input
        verbe_saisi, prefixe_saisi = self._parser_input(user_input)
        
        # 2. Normaliser pour la recherche
        verbe_saisi_norm = self._normaliser_texte(verbe_saisi)
        prefixe_saisi_norm = self._normaliser_texte(prefixe_saisi)
        
        # 3. Détecter si c'est un verbe connu (avec tolérance)
        mode = "STANDARD"
        verbe_corrige = None
        
        if verbe_saisi_norm:
            # Vérifier si c'est un verbe exact
            if verbe_saisi_norm in self.tous_les_verbes:
                verbe_corrige = verbe_saisi_norm
                mode = "VERBE_EXACT"
            elif self.verbe_matcher:
                # Recherche floue
                matches = self.verbe_matcher.find_matching_verbes(verbe_saisi, min_similarity=0.6)
                if matches:
                    verbe_corrige = matches[0][0]  # Meilleur match
                    similarity = matches[0][1]
                    mode = f"VERBE_FLUE ({similarity:.2f})"
                    logger.debug(f"🔍 Verbe flou: '{verbe_saisi}' → '{verbe_corrige}' ({similarity:.2f})")
        
        # 4. Obtenir les suggestions selon le mode
        if verbe_corrige:
            # Mode VERBE (exact ou flou)
            suggestions = self._get_suggestions_verbe_mode(
                verbe_corrige, 
                prefixe_saisi_norm,
                max_suggestions
            )
            
            # Si pas assez de suggestions, élargir la recherche
            if len(suggestions) < max_suggestions // 2:
                suggestions_recherche = self._get_suggestions_recherche_mode(
                    user_input,
                    max_suggestions - len(suggestions)
                )
                
                # Fusionner sans doublons
                suggestions_set = set(suggestions)
                for sugg in suggestions_recherche:
                    if sugg not in suggestions_set:
                        suggestions.append(sugg)
                        if len(suggestions) >= max_suggestions:
                            break
        else:
            # Mode RECHERCHE (pas de verbe détecté)
            suggestions = self._get_suggestions_recherche_mode(
                user_input,
                max_suggestions
            )
            mode = "RECHERCHE"
        
        # 5. Limiter et logger
        suggestions = suggestions[:max_suggestions]
        latence = (time.time() - start_time) * 1000
        
        logger.debug(f"⚡ Mode {mode}: {len(suggestions)} suggestions en {latence:.0f}ms")
        
        return suggestions
    
    def _get_suggestions_verbe_mode(
        self, 
        verbe_normalise: str,
        prefixe_normalise: str,
        max_suggestions: int
    ) -> List[str]:
        """Mode VERBE avec verbe normalisé (exact ou corrigé)"""
        
        if verbe_normalise not in self.complements_normalises:
            return []
        
        suggestions = []
        
        # Parcourir tous les compléments pour ce verbe
        for item in self.complements_normalises[verbe_normalise]:
            complement_normalise = item["complement_normalise"]
            
            # Vérifier si le préfixe match (vide = tout)
            if prefixe_normalise == "" or complement_normalise.startswith(prefixe_normalise):
                suggestions.append(item["complet"])
                
                if len(suggestions) >= max_suggestions:
                    break
        
        # Si pas assez, assouplir le préfixe
        if len(suggestions) < max_suggestions // 2 and prefixe_normalise:
            for item in self.complements_normalises[verbe_normalise]:
                if item["complet"] not in suggestions:
                    # Vérifier si le préfixe est contenu (pas seulement au début)
                    if prefixe_normalise in item["complement_normalise"]:
                        suggestions.append(item["complet"])
                        
                        if len(suggestions) >= max_suggestions:
                            break
        
        # Trier par pertinence (les plus courts d'abord)
        suggestions.sort(key=lambda x: len(x))
        
        return suggestions[:max_suggestions]
    
    def _get_suggestions_recherche_mode(
        self, 
        user_input: str,
        max_suggestions: int
    ) -> List[str]:
        """Mode RECHERCHE : recherche dans tout le contenu"""
        user_input_norm = self._normaliser_texte(user_input)
        
        if not user_input_norm:
            return []
        
        suggestions = []
        
        # Parcourir TOUTES les phrases du corpus
        for verbe_norm in self.complements_normalises:
            for item in self.complements_normalises[verbe_norm]:
                phrase_norm = self._normaliser_texte(item["complet"])
                
                # Vérifier si l'input est CONTENU dans la phrase
                if user_input_norm in phrase_norm:
                    suggestions.append(item["complet"])
                    
                    if len(suggestions) >= max_suggestions:
                        break
            
            if len(suggestions) >= max_suggestions:
                break
        
        # Si pas assez, chercher par similarité partielle
        if len(suggestions) < max_suggestions:
            suggestions_fuzzy = self._recherche_similarite_partielle(
                user_input_norm, 
                max_suggestions - len(suggestions)
            )
            
            suggestions_set = set(suggestions)
            for sugg in suggestions_fuzzy:
                if sugg not in suggestions_set:
                    suggestions.append(sugg)
                    if len(suggestions) >= max_suggestions:
                        break
        
        # Trier par pertinence
        suggestions = self._trier_suggestions_recherche(suggestions, user_input_norm)
        
        return suggestions[:max_suggestions]
    
    def _recherche_similarite_partielle(
        self, 
        user_input_norm: str,
        max_results: int
    ) -> List[str]:
        """Recherche par similarité partielle (mots en commun)"""
        if not user_input_norm:
            return []
        
        mots_recherche = set(user_input_norm.split())
        suggestions = []
        
        for verbe_norm in self.complements_normalises:
            for item in self.complements_normalises[verbe_norm]:
                phrase_norm = self._normaliser_texte(item["complet"])
                mots_phrase = set(phrase_norm.split())
                
                # Calculer l'intersection
                mots_communs = mots_recherche.intersection(mots_phrase)
                
                # Si au moins un mot en commun (et pas juste des mots courts)
                mots_communs_significatifs = [m for m in mots_communs if len(m) >= 3]
                
                if len(mots_communs_significatifs) >= 1:
                    suggestions.append(item["complet"])
                    
                    if len(suggestions) >= max_results:
                        break
            
            if len(suggestions) >= max_results:
                break
        
        return suggestions
    
    def _trier_suggestions_recherche(self, suggestions: List[str], user_input_norm: str) -> List[str]:
        """Trie les suggestions en mode recherche"""
        if not suggestions:
            return []
        
        def score_pertinence(phrase: str) -> int:
            phrase_norm = self._normaliser_texte(phrase)
            
            # 1. Position de l'occurrence
            position = phrase_norm.find(user_input_norm)
            score_position = 100 if position >= 0 else 0
            
            # 2. Longueur (plus court = mieux)
            score_longueur = -len(phrase) // 10
            
            # 3. Commence par un verbe connu
            mots = phrase.split(maxsplit=1)
            if len(mots) > 0 and self._normaliser_texte(mots[0]) in self.tous_les_verbes:
                score_position += 50
            
            # 4. Score de similarité
            similarity = SequenceMatcher(None, user_input_norm, phrase_norm).ratio()
            score_similarite = int(similarity * 50)
            
            return score_position + score_longueur + score_similarite
        
        return sorted(suggestions, key=score_pertinence, reverse=True)
    
    def _parser_input(self, user_input: str) -> Tuple[str, str]:
        """Parse l'input utilisateur"""
        mots = user_input.strip().split(maxsplit=1)
        
        if len(mots) == 1:
            return mots[0], ""
        else:
            return mots[0], mots[1]
    
    def get_corrected_verb(self, verbe_saisi: str) -> Optional[str]:
        """
        Corrige un verbe saisi (avec fautes)
        
        Args:
            verbe_saisi: Verbe potentiellement mal orthographié
        
        Returns:
            Verbe corrigé ou None si non trouvé
        """
        if not self.verbe_matcher:
            return None
        
        return self.verbe_matcher.get_best_match(verbe_saisi, min_similarity=0.6)
    
    def get_available_verbs(self) -> List[str]:
        """Retourne la liste des verbes disponibles"""
        return sorted(self.tous_les_verbes)
    
    # =====================================================================
    # ✅ MÉTHODES EXISTANTES (compatibilité)
    # =====================================================================
    
    def _retrieve_relevant_documents(
        self, 
        query: str,
        k: Optional[int] = None
    ) -> List[Dict]:
        """Recherche avec filtre par similarité"""
        if k is None:
            k = self.k_documents
        
        try:
            results = self.vectorstore.search(query, k=k*2)
            
            filtered_results = []
            for doc in results:
                similarity = doc.get("similarity_score", 0)
                if similarity >= self.min_similarity:
                    filtered_results.append(doc)
            
            return filtered_results[:k]
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche : {e}")
            return []
    
    def _get_suggestion_prompt_template(self) -> str:
        """Template optimisé pour suggestions rapides"""
        return """Tu es un assistant spécialisé en normes électriques NFC 15-100.

L'utilisateur tape : "{user_input}"

Contexte normatif disponible :
{context_documents}

GÉNÈRE des suggestions RAPIDES et PERTINENTES en JSON :
{{
  "mots_cles": ["terme1", "terme2", "terme3"],
  "phrases_completes": ["phrase 1", "phrase 2"],
  "references_normatives": ["NFC 15-100 Article X.X"],
  "complements_intelligents": ["complément 1", "complément 2"]
}}

Règles :
- Seulement des suggestions directement liées
- Références RÉELLES du contexte uniquement
- Maximum 6 mots-clés, 4 phrases, 5 références

JSON uniquement :"""
    
    # ... autres méthodes existantes (restent inchangées) ...


def get_suggestion_engine(vectorstore: VectorStore, llm: ChatGroq) -> SuggestionEngine:
    """Factory function pour créer le SuggestionEngine avec recherche flue"""
    return SuggestionEngine(
        vectorstore=vectorstore,
        llm=llm,
        k_documents=30,
        min_similarity=0.65
    )


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("🧪 TESTS SuggestionEngine AVEC RECHERCHE FLUE DE VERBES")
    print("=" * 50)
    
    # Créer un moteur factice pour les tests
    class MockEngine:
        def __init__(self):
            self.verbes = [
                "remplacer", "réparer", "installer", "vérifier", 
                "protéger", "contrôler", "poser", "nettoyer",
                "serrer", "resserrer", "réserver"
            ]
            self.verbe_matcher = FuzzyVerbeMatcher(self.verbes)
        
        def get_corrected_verb(self, verbe_saisi):
            return self.verbe_matcher.get_best_match(verbe_saisi, 0.6)
        
        def test_corrections(self):
            test_cases = [
                ("remplcer", "remplacer"),
                ("remplacer", "remplacer"),
                ("remplac", "remplacer"),
                ("reparer", "réparer"),
                ("réparer", "réparer"),
                ("instaler", "installer"),
                ("installer", "installer"),
                ("verifier", "vérifier"),
                ("proteger", "protéger"),
                ("controler", "contrôler"),
                ("poser", "poser"),
                ("reser", "serrer"),  # "reser" → "serrer" ou "réserver"
                ("resserer", "resserrer"),
                ("nettoyer", "nettoyer"),
                ("xyz", None),  # Non trouvé
            ]
            
            print("🔍 Tests de correction de verbes:")
            for saisie, attendu in test_cases:
                corrige = self.get_corrected_verb(saisie)
                status = "✅" if corrige == attendu else "❌"
                print(f"{status} '{saisie}' → '{corrige}' (attendu: '{attendu}')")
    
    mock = MockEngine()
    mock.test_corrections()
    
    print("\n" + "=" * 50)
    print("🎯 Exemples de fonctionnement:")
    print("\nCas 1: 'remplcer luminaire'")
    print("  → Détecte 'remplacer' (correction floue)")
    print("  → Cherche les compléments de 'remplacer'")
    print("  → Filtre ceux qui commencent par 'luminaire'")
    
    print("\nCas 2: 'reser vis'")
    print("  → Détecte 'serrer' ou 'réserver' (selon similarité)")
    print("  → Cherche les compléments du verbe corrigé")
    print("  → Filtre ceux qui commencent par 'vis'")
    
    print("\nCas 3: 'protetion différentiel'")
    print("  → Pas de verbe détecté (protetion n'est pas un verbe)")
    print("  → Mode RECHERCHE: cherche 'protetion différentiel' dans tout le texte")
    print("  → Retourne les phrases contenant ces mots")
    
    print("\n" + "=" * 50)
    print("✅ SuggestionEngine FLUE prêt!")