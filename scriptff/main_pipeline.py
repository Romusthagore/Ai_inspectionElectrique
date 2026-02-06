#!/usr/bin/env python3
"""
Pipeline complet d'inspection électrique
Intègre: correction_pipeline + response_parser + report_generator
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from correction_pipeline import get_correction_pipeline
from report_generator import get_report_generator
from config import initialiser_repertoires, valider_configuration

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InspectionPipeline:
    """
    Pipeline complet pour l'inspection électrique
    De la saisie brute à la génération du rapport final
    """
    
    def __init__(self, output_dir: str = "rapports"):
        """
        Args:
            output_dir: Répertoire pour sauvegarder les rapports
        """
        self.correction_pipeline = get_correction_pipeline()
        self.report_generator = get_report_generator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ InspectionPipeline initialisé")
    
    def process_inspection(self,
                          observations_brutes: List[str],
                          metadata: Dict[str, Any],
                          k_documents: int = 5,
                          formats: List[str] = None) -> Dict[str, Any]:
        """
        Traite une inspection complète
        
        Args:
            observations_brutes: Liste des observations brutes saisies
            metadata: Métadonnées (site, inspecteur, date...)
            k_documents: Nombre de documents RAG par observation
            formats: Formats de rapport à générer (défaut: tous)
            
        Returns:
            Résultats complets avec observations corrigées et chemins des rapports
        """
        try:
            logger.info(f"🚀 Démarrage inspection: {len(observations_brutes)} observations")
            
            # Étape 1: Correction des observations
            logger.info("📝 Étape 1/3: Correction des observations...")
            observations_corrigees = self.correction_pipeline.traiter_lot_observations(
                observations_brutes, 
                k_documents=k_documents
            )
            
            # Étape 2: Validation et enrichissement
            logger.info("🔍 Étape 2/3: Validation et enrichissement...")
            observations_validees = self._valider_observations(observations_corrigees)
            
            # Étape 3: Génération des rapports
            logger.info("📄 Étape 3/3: Génération des rapports...")
            if formats is None:
                formats = ["json", "markdown", "html"]
            
            rapports = self._generer_rapports(
                observations_validees,
                metadata,
                formats
            )
            
            # Résumé
            stats = self._calculer_statistiques(observations_validees)
            
            logger.info("✅ Inspection terminée avec succès")
            
            return {
                "observations": observations_validees,
                "statistiques": stats,
                "rapports": rapports,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur pipeline inspection: {e}", exc_info=True)
            raise
    
    def _valider_observations(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valide et enrichit les observations"""
        validees = []
        
        for i, obs in enumerate(observations, 1):
            # Vérifier les champs obligatoires
            if not obs.get('observation_corrigee'):
                logger.warning(f"⚠️ Observation {i}: champ 'observation_corrigee' manquant")
                continue
            
            # Enrichir avec numéro
            obs['numero'] = i
            
            # Normaliser les champs
            obs['niveau_gravite'] = obs.get('niveau_gravite', 'Mineur')
            obs['localisation'] = obs.get('localisation', 'Non spécifiée')
            obs['delai_recommande'] = obs.get('delai_recommande', '30 jours')
            
            # S'assurer que les listes existent
            if not obs.get('references_normatives'):
                obs['references_normatives'] = ['À vérifier']
            if not obs.get('risques_identifies'):
                obs['risques_identifies'] = ['À évaluer']
            if not obs.get('actions_correctives'):
                obs['actions_correctives'] = ['Mise en conformité requise']
            
            validees.append(obs)
        
        logger.info(f"✅ {len(validees)}/{len(observations)} observations validées")
        return validees
    
    def _generer_rapports(self,
                         observations: List[Dict[str, Any]],
                         metadata: Dict[str, Any],
                         formats: List[str]) -> Dict[str, str]:
        """Génère les rapports dans les formats demandés"""
        rapports = {}
        
        # Préparer le nom de base
        numero_rapport = metadata.get('numero_rapport', 
                                     f"INSP-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        base_name = f"rapport_{numero_rapport}"
        
        for format_type in formats:
            try:
                output_file = self.output_dir / f"{base_name}.{format_type}"
                
                rapport = self.report_generator.generate_report(
                    observations,
                    metadata,
                    format=format_type,
                    output_file=str(output_file)
                )
                
                rapports[format_type] = str(output_file)
                logger.info(f"✅ Rapport {format_type.upper()} généré: {output_file}")
                
            except Exception as e:
                logger.error(f"❌ Erreur génération {format_type}: {e}")
        
        return rapports
    
    def _calculer_statistiques(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les statistiques de l'inspection"""
        stats = {
            "total": len(observations),
            "critique": 0,
            "majeur": 0,
            "mineur": 0,
            "avec_references": 0,
            "sans_localisation": 0
        }
        
        for obs in observations:
            gravite = obs.get('niveau_gravite', 'Mineur')
            if gravite == 'Critique':
                stats['critique'] += 1
            elif gravite == 'Majeur':
                stats['majeur'] += 1
            elif gravite == 'Mineur':
                stats['mineur'] += 1
            
            if obs.get('references_normatives'):
                stats['avec_references'] += 1
            
            if obs.get('localisation') in ['Non spécifiée', 'non spécifiée']:
                stats['sans_localisation'] += 1
        
        # Calculs supplémentaires
        if stats['total'] > 0:
            stats['taux_conformite'] = round(
                100 - (stats['critique'] / stats['total'] * 100), 1
            )
            stats['taux_references'] = round(
                (stats['avec_references'] / stats['total'] * 100), 1
            )
        else:
            stats['taux_conformite'] = 100.0
            stats['taux_references'] = 0.0
        
        return stats
    
    def process_single_observation(self,
                                   observation_brute: str,
                                   metadata: Optional[Dict[str, Any]] = None,
                                   k_documents: int = 5) -> Dict[str, Any]:
        """
        Traite une observation unique (mode rapide)
        
        Args:
            observation_brute: Observation brute
            metadata: Métadonnées optionnelles
            k_documents: Nombre de documents RAG
            
        Returns:
            Observation corrigée
        """
        logger.info(f"⚡ Mode rapide: observation unique")
        
        resultat = self.correction_pipeline.corriger_observation(
            observation_brute,
            k_documents=k_documents
        )
        
        return resultat
    
    def generate_summary_report(self, inspection_result: Dict[str, Any]) -> str:
        """
        Génère un résumé textuel de l'inspection
        
        Args:
            inspection_result: Résultat complet de process_inspection()
            
        Returns:
            Résumé textuel
        """
        stats = inspection_result['statistiques']
        metadata = inspection_result['metadata']
        
        summary = f"""
╔═══════════════════════════════════════════════════════════════╗
║           RÉSUMÉ D'INSPECTION ÉLECTRIQUE                      ║
╚═══════════════════════════════════════════════════════════════╝

📍 SITE: {metadata.get('site', 'N/A')}
👤 INSPECTEUR: {metadata.get('inspecteur', 'N/A')}
📅 DATE: {metadata.get('date_inspection', 'N/A')}

📊 STATISTIQUES:
   • Total d'observations: {stats['total']}
   • 🔴 Critiques: {stats['critique']} (intervention IMMÉDIATE requise)
   • 🟠 Majeurs: {stats['majeur']} (correction sous 30 jours)
   • 🟢 Mineurs: {stats['mineur']} (amélioration recommandée)

📈 INDICATEURS:
   • Taux de conformité: {stats['taux_conformite']}%
   • Observations avec références: {stats['taux_references']}%

📄 RAPPORTS GÉNÉRÉS:
"""
        
        for format_type, filepath in inspection_result['rapports'].items():
            summary += f"   • {format_type.upper()}: {filepath}\n"
        
        if stats['critique'] > 0:
            summary += f"""
⚠️  ATTENTION: {stats['critique']} observation(s) CRITIQUE(S)
    → Intervention immédiate nécessaire avant remise en service
"""
        
        return summary


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

_inspection_pipeline_instance = None

def get_inspection_pipeline(reset: bool = False) -> InspectionPipeline:
    """Retourne l'instance singleton du pipeline"""
    global _inspection_pipeline_instance
    if _inspection_pipeline_instance is None or reset:
        _inspection_pipeline_instance = InspectionPipeline()
    return _inspection_pipeline_instance


# =============================================================================
# EXEMPLE D'UTILISATION COMPLÈTE
# =============================================================================

def exemple_inspection_complete():
    """Exemple d'utilisation du pipeline complet"""
    
    print("🏢 EXEMPLE D'INSPECTION ÉLECTRIQUE COMPLÈTE")
    print("=" * 70)
    
    # 1. Données d'entrée
    observations_brutes = [
        "prise pas terre cuisine",
        "disjoncteur différentiel 30mA manquant salle de bain",
        "câble section insuffisante chauffage salon",
        "tableau électrique encombré garage",
        "protection parafoudre manquante"
    ]
    
    metadata = {
        "site": "Résidence Les Oliviers - Bâtiment A",
        "adresse": "45 Avenue de la République, 13001 Marseille",
        "inspecteur": "Jean-Pierre Martin",
        "date_inspection": datetime.now().strftime("%d/%m/%Y"),
        "numero_rapport": f"INSP-{datetime.now().strftime('%Y%m%d-%H%M')}"
    }
    
    print(f"\n📋 Observations brutes à traiter: {len(observations_brutes)}")
    for i, obs in enumerate(observations_brutes, 1):
        print(f"   {i}. {obs}")
    
    # 2. Initialiser le pipeline
    print("\n⚙️  Initialisation du pipeline...")
    pipeline = get_inspection_pipeline()
    
    # 3. Traiter l'inspection
    print("\n🔄 Traitement en cours...")
    resultat = pipeline.process_inspection(
        observations_brutes=observations_brutes,
        metadata=metadata,
        k_documents=3,
        formats=["json", "markdown", "html"]
    )
    
    # 4. Afficher le résumé
    print("\n" + "=" * 70)
    summary = pipeline.generate_summary_report(resultat)
    print(summary)
    
    # 5. Détails des observations critiques
    observations_critiques = [
        obs for obs in resultat['observations']
        if obs.get('niveau_gravite') == 'Critique'
    ]
    
    if observations_critiques:
        print("\n⚠️  DÉTAILS DES OBSERVATIONS CRITIQUES:")
        print("-" * 70)
        for obs in observations_critiques:
            print(f"\n🔴 {obs['observation_corrigee']}")
            print(f"   📍 Localisation: {obs['localisation']}")
            print(f"   🚨 Risques: {', '.join(obs['risques_identifies'][:2])}")
            print(f"   🔧 Action: {obs['actions_correctives'][0]}")
    
    print("\n" + "=" * 70)
    print("✅ INSPECTION TERMINÉE AVEC SUCCÈS")
    print("=" * 70)
    
    return resultat


def exemple_observation_unique():
    """Exemple de traitement d'une observation unique"""
    
    print("\n⚡ EXEMPLE: OBSERVATION UNIQUE (MODE RAPIDE)")
    print("=" * 70)
    
    pipeline = get_inspection_pipeline()
    
    observation = "prise de courant sans mise à la terre dans la cuisine"
    
    print(f"\n📝 Observation brute:")
    print(f"   '{observation}'")
    
    print("\n🔄 Correction en cours...")
    resultat = pipeline.process_single_observation(observation, k_documents=3)
    
    print("\n✅ Résultat:")
    print(f"   🔧 {resultat['observation_corrigee']}")
    print(f"   📚 Références: {', '.join(resultat['references_normatives'][:2])}")
    print(f"   ⚠️  Gravité: {resultat['niveau_gravite']}")
    print(f"   📍 Localisation: {resultat['localisation']}")
    print(f"   ⏰ Délai: {resultat['delai_recommande']}")
    
    print("\n" + "=" * 70)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔌 SYSTÈME D'INSPECTION ÉLECTRIQUE AUTOMATISÉ")
    print("=" * 70)
    
    try:
        # Vérifier la configuration
        print("\n🔧 Vérification de la configuration...")
        initialiser_repertoires()
        valider_configuration()
        print("✅ Configuration OK")
        
        # Exemple 1: Inspection complète
        print("\n" + "=" * 70)
        resultat_complet = exemple_inspection_complete()
        
        # Exemple 2: Observation unique
        exemple_observation_unique()
        
        print("\n" + "=" * 70)
        print("🎯 SYSTÈME OPÉRATIONNEL")
        print("   ✅ Pipeline de correction fonctionnel")
        print("   ✅ Génération de rapports multi-formats")
        print("   ✅ Statistiques automatiques")
        print("   ✅ Prêt pour production")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        logger.error("Erreur fatale", exc_info=True)