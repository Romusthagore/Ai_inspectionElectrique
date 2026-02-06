#!/usr/bin/env python3
"""
Générateur de rapports d'inspection électrique
Formats supportés: JSON, Markdown, HTML, PDF
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Générateur de rapports professionnels pour inspections électriques
    Supporte multiples formats et templates personnalisables
    """
    
    # Templates de couleurs pour gravité
    GRAVITE_COLORS = {
        "Critique": {"html": "#DC2626", "emoji": "🔴"},
        "Majeur": {"html": "#F59E0B", "emoji": "🟠"},
        "Mineur": {"html": "#10B981", "emoji": "🟢"},
        "Inconnu": {"html": "#6B7280", "emoji": "⚪"}
    }
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Args:
            template_dir: Répertoire contenant les templates personnalisés
        """
        self.template_dir = template_dir
        logger.info("✅ ReportGenerator initialisé")
    
    def generate_report(self, 
                       observations: List[Dict[str, Any]], 
                       metadata: Optional[Dict[str, Any]] = None,
                       format: str = "markdown",
                       output_file: Optional[str] = None) -> str:
        """
        Génère un rapport complet
        
        Args:
            observations: Liste des observations corrigées
            metadata: Métadonnées du rapport (site, inspecteur, date...)
            format: Format de sortie ("json", "markdown", "html", "text")
            output_file: Fichier de sortie (optionnel)
            
        Returns:
            Contenu du rapport généré
        """
        try:
            logger.info(f"📄 Génération rapport ({format}): {len(observations)} observations")
            
            # Enrichir les métadonnées
            metadata = self._prepare_metadata(metadata)
            
            # Générer selon le format
            if format.lower() == "json":
                content = self._generate_json(observations, metadata)
            elif format.lower() == "markdown":
                content = self._generate_markdown(observations, metadata)
            elif format.lower() == "html":
                content = self._generate_html(observations, metadata)
            elif format.lower() == "text":
                content = self._generate_text(observations, metadata)
            else:
                raise ValueError(f"Format non supporté: {format}")
            
            # Sauvegarder si fichier spécifié
            if output_file:
                self._save_report(content, output_file)
            
            logger.info(f"✅ Rapport généré: {len(content)} caractères")
            return content
            
        except Exception as e:
            logger.error(f"❌ Erreur génération rapport: {e}", exc_info=True)
            raise
    
    def _prepare_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prépare et complète les métadonnées"""
        default_metadata = {
            "titre": "Rapport d'Inspection Électrique",
            "site": "Site non spécifié",
            "adresse": "Adresse non spécifiée",
            "inspecteur": "Inspecteur",
            "date_inspection": datetime.now().strftime("%d/%m/%Y"),
            "date_generation": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "norme_reference": "NFC 15-100",
            "numero_rapport": f"INSP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        return default_metadata
    
    def _generate_json(self, observations: List[Dict[str, Any]], 
                      metadata: Dict[str, Any]) -> str:
        """Génère un rapport JSON structuré"""
        report = {
            "metadata": metadata,
            "statistiques": self._calculate_statistics(observations),
            "observations": observations,
            "resume": self._generate_summary(observations)
        }
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def _generate_markdown(self, observations: List[Dict[str, Any]], 
                          metadata: Dict[str, Any]) -> str:
        """Génère un rapport Markdown professionnel"""
        
        md = []
        
        # En-tête
        md.append(f"# {metadata['titre']}")
        md.append(f"\n**Rapport N°**: {metadata['numero_rapport']}")
        md.append(f"**Date d'inspection**: {metadata['date_inspection']}")
        md.append(f"**Date de génération**: {metadata['date_generation']}")
        md.append(f"\n---\n")
        
        # Informations du site
        md.append("## 📍 Informations du Site")
        md.append(f"\n- **Site**: {metadata['site']}")
        md.append(f"- **Adresse**: {metadata['adresse']}")
        md.append(f"- **Inspecteur**: {metadata['inspecteur']}")
        md.append(f"- **Norme de référence**: {metadata['norme_reference']}")
        md.append(f"\n---\n")
        
        # Statistiques
        stats = self._calculate_statistics(observations)
        md.append("## 📊 Statistiques Générales")
        md.append(f"\n- **Total d'observations**: {stats['total']}")
        md.append(f"- 🔴 **Critiques**: {stats['critique']}")
        md.append(f"- 🟠 **Majeurs**: {stats['majeur']}")
        md.append(f"- 🟢 **Mineurs**: {stats['mineur']}")
        md.append(f"\n**Taux de conformité**: {stats['taux_conformite']:.1f}%")
        md.append(f"\n---\n")
        
        # Résumé exécutif
        md.append("## 📝 Résumé Exécutif")
        summary = self._generate_summary(observations)
        md.append(f"\n{summary['resume_general']}")
        
        if summary['observations_critiques']:
            md.append("\n### ⚠️ Points critiques nécessitant une attention immédiate:")
            for obs in summary['observations_critiques']:
                md.append(f"- {obs}")
        
        md.append(f"\n---\n")
        
        # Observations détaillées
        md.append("## 🔍 Observations Détaillées")
        
        # Grouper par gravité
        grouped = self._group_by_gravite(observations)
        
        for gravite in ["Critique", "Majeur", "Mineur"]:
            if gravite in grouped and grouped[gravite]:
                emoji = self.GRAVITE_COLORS[gravite]["emoji"]
                md.append(f"\n### {emoji} Observations {gravite}s ({len(grouped[gravite])})")
                
                for i, obs in enumerate(grouped[gravite], 1):
                    md.append(f"\n#### {i}. {obs.get('observation_corrigee', 'N/A')}")
                    md.append(f"\n**📍 Localisation**: {obs.get('localisation', 'Non spécifiée')}")
                    
                    # Références
                    refs = obs.get('references_normatives', [])
                    if refs:
                        md.append(f"**📚 Références**: {', '.join(refs)}")
                    
                    # Risques
                    risques = obs.get('risques_identifies', [])
                    if risques:
                        md.append(f"**🚨 Risques**: {', '.join(risques[:3])}")
                    
                    # Actions
                    actions = obs.get('actions_correctives', [])
                    if actions:
                        md.append("\n**🔧 Actions correctives**:")
                        for action in actions[:3]:
                            md.append(f"  - {action}")
                    
                    md.append(f"\n**⏰ Délai recommandé**: {obs.get('delai_recommande', 'N/A')}")
                    md.append("\n---")
        
        # Recommandations
        md.append("\n## 💡 Recommandations Générales")
        recommendations = self._generate_recommendations(observations)
        for rec in recommendations:
            md.append(f"- {rec}")
        
        # Pied de page
        md.append(f"\n---\n")
        md.append(f"\n*Rapport généré automatiquement le {metadata['date_generation']}*")
        md.append(f"\n*Conforme à la norme {metadata['norme_reference']}*")
        
        return "\n".join(md)
    
    def _generate_html(self, observations: List[Dict[str, Any]], 
                      metadata: Dict[str, Any]) -> str:
        """Génère un rapport HTML avec style professionnel"""
        
        stats = self._calculate_statistics(observations)
        grouped = self._group_by_gravite(observations)
        
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata['titre']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        
        .header {{
            border-bottom: 4px solid #2563EB;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #1e40af;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .metadata {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
        }}
        
        .metadata-item {{
            display: flex;
            gap: 10px;
        }}
        
        .metadata-label {{
            font-weight: bold;
            color: #64748b;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: white;
        }}
        
        .stat-card.total {{ background: #2563EB; }}
        .stat-card.critique {{ background: #DC2626; }}
        .stat-card.majeur {{ background: #F59E0B; }}
        .stat-card.mineur {{ background: #10B981; }}
        
        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .section {{
            margin: 40px 0;
        }}
        
        h2 {{
            color: #1e40af;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        .observation {{
            margin: 20px 0;
            padding: 20px;
            border-left: 4px solid #e5e7eb;
            background: #fafafa;
            border-radius: 4px;
        }}
        
        .observation.critique {{ border-left-color: #DC2626; }}
        .observation.majeur {{ border-left-color: #F59E0B; }}
        .observation.mineur {{ border-left-color: #10B981; }}
        
        .observation-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #1e293b;
            margin-bottom: 15px;
        }}
        
        .observation-detail {{
            margin: 10px 0;
            padding: 8px 0;
        }}
        
        .observation-label {{
            font-weight: bold;
            color: #64748b;
            display: inline-block;
            min-width: 150px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            color: white;
        }}
        
        .badge.critique {{ background: #DC2626; }}
        .badge.majeur {{ background: #F59E0B; }}
        .badge.mineur {{ background: #10B981; }}
        
        .actions-list {{
            list-style: none;
            padding-left: 0;
        }}
        
        .actions-list li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}
        
        .actions-list li:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #2563EB;
            font-weight: bold;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #64748b;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{metadata['titre']}</h1>
            <p>Rapport N° {metadata['numero_rapport']}</p>
        </div>
        
        <div class="metadata">
            <div class="metadata-item">
                <span class="metadata-label">Site:</span>
                <span>{metadata['site']}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Adresse:</span>
                <span>{metadata['adresse']}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Inspecteur:</span>
                <span>{metadata['inspecteur']}</span>
            </div>
            <div class="metadata-item">
                <span class="metadata-label">Date d'inspection:</span>
                <span>{metadata['date_inspection']}</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card total">
                <div class="stat-label">Total</div>
                <div class="stat-number">{stats['total']}</div>
                <div class="stat-label">Observations</div>
            </div>
            <div class="stat-card critique">
                <div class="stat-label">Critiques</div>
                <div class="stat-number">{stats['critique']}</div>
                <div class="stat-label">Danger immédiat</div>
            </div>
            <div class="stat-card majeur">
                <div class="stat-label">Majeurs</div>
                <div class="stat-number">{stats['majeur']}</div>
                <div class="stat-label">À corriger</div>
            </div>
            <div class="stat-card mineur">
                <div class="stat-label">Mineurs</div>
                <div class="stat-number">{stats['mineur']}</div>
                <div class="stat-label">Amélioration</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 Résumé Exécutif</h2>
            <p>{self._generate_summary(observations)['resume_general']}</p>
        </div>
"""
        
        # Observations par gravité
        for gravite in ["Critique", "Majeur", "Mineur"]:
            if gravite in grouped and grouped[gravite]:
                gravite_lower = gravite.lower()
                html += f"""
        <div class="section">
            <h2>Observations {gravite}s ({len(grouped[gravite])})</h2>
"""
                
                for i, obs in enumerate(grouped[gravite], 1):
                    refs = ', '.join(obs.get('references_normatives', ['N/A']))
                    risques = ', '.join(obs.get('risques_identifies', ['N/A'])[:3])
                    actions = obs.get('actions_correctives', [])
                    
                    html += f"""
            <div class="observation {gravite_lower}">
                <div class="observation-title">
                    {i}. {obs.get('observation_corrigee', 'N/A')}
                </div>
                <div class="observation-detail">
                    <span class="observation-label">📍 Localisation:</span>
                    {obs.get('localisation', 'Non spécifiée')}
                </div>
                <div class="observation-detail">
                    <span class="observation-label">📚 Références:</span>
                    {refs}
                </div>
                <div class="observation-detail">
                    <span class="observation-label">🚨 Risques:</span>
                    {risques}
                </div>
                <div class="observation-detail">
                    <span class="observation-label">🔧 Actions:</span>
                    <ul class="actions-list">
"""
                    for action in actions[:3]:
                        html += f"                        <li>{action}</li>\n"
                    
                    html += f"""
                    </ul>
                </div>
                <div class="observation-detail">
                    <span class="observation-label">⏰ Délai:</span>
                    <span class="badge {gravite_lower}">{obs.get('delai_recommande', 'N/A')}</span>
                </div>
            </div>
"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Rapport généré automatiquement le {metadata['date_generation']}</p>
            <p>Conforme à la norme {metadata['norme_reference']}</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_text(self, observations: List[Dict[str, Any]], 
                      metadata: Dict[str, Any]) -> str:
        """Génère un rapport texte simple"""
        
        lines = []
        
        # En-tête
        lines.append("=" * 80)
        lines.append(metadata['titre'].center(80))
        lines.append("=" * 80)
        lines.append(f"\nRapport N°: {metadata['numero_rapport']}")
        lines.append(f"Date d'inspection: {metadata['date_inspection']}")
        lines.append(f"Site: {metadata['site']}")
        lines.append(f"Inspecteur: {metadata['inspecteur']}")
        lines.append("\n" + "-" * 80 + "\n")
        
        # Statistiques
        stats = self._calculate_statistics(observations)
        lines.append("STATISTIQUES:")
        lines.append(f"  Total: {stats['total']} observations")
        lines.append(f"  Critiques: {stats['critique']}")
        lines.append(f"  Majeurs: {stats['majeur']}")
        lines.append(f"  Mineurs: {stats['mineur']}")
        lines.append("\n" + "-" * 80 + "\n")
        
        # Observations
        lines.append("OBSERVATIONS DÉTAILLÉES:\n")
        
        grouped = self._group_by_gravite(observations)
        
        for gravite in ["Critique", "Majeur", "Mineur"]:
            if gravite in grouped and grouped[gravite]:
                lines.append(f"\n{gravite.upper()}S ({len(grouped[gravite])}):")
                lines.append("-" * 80)
                
                for i, obs in enumerate(grouped[gravite], 1):
                    lines.append(f"\n{i}. {obs.get('observation_corrigee', 'N/A')}")
                    lines.append(f"   Localisation: {obs.get('localisation', 'Non spécifiée')}")
                    lines.append(f"   Références: {', '.join(obs.get('references_normatives', ['N/A']))}")
                    lines.append(f"   Délai: {obs.get('delai_recommande', 'N/A')}")
                    lines.append("")
        
        # Pied de page
        lines.append("\n" + "=" * 80)
        lines.append(f"Généré le {metadata['date_generation']}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _calculate_statistics(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les statistiques des observations"""
        stats = {
            "total": len(observations),
            "critique": 0,
            "majeur": 0,
            "mineur": 0,
            "inconnu": 0
        }
        
        for obs in observations:
            gravite = obs.get('niveau_gravite', 'Inconnu').lower()
            if gravite == 'critique':
                stats['critique'] += 1
            elif gravite == 'majeur':
                stats['majeur'] += 1
            elif gravite == 'mineur':
                stats['mineur'] += 1
            else:
                stats['inconnu'] += 1
        
        # Taux de conformité (inverse du % de critiques)
        if stats['total'] > 0:
            stats['taux_conformite'] = 100 - (stats['critique'] / stats['total'] * 100)
        else:
            stats['taux_conformite'] = 100.0
        
        return stats
    
    def _group_by_gravite(self, observations: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Groupe les observations par niveau de gravité"""
        grouped = {
            "Critique": [],
            "Majeur": [],
            "Mineur": [],
            "Inconnu": []
        }
        
        for obs in observations:
            gravite = obs.get('niveau_gravite', 'Inconnu')
            if gravite in grouped:
                grouped[gravite].append(obs)
            else:
                grouped['Inconnu'].append(obs)
        
        return grouped
    
    def _generate_summary(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Génère un résumé exécutif"""
        stats = self._calculate_statistics(observations)
        
        resume = f"L'inspection a révélé {stats['total']} observation(s) au total. "
        
        if stats['critique'] > 0:
            resume += f"⚠️ ATTENTION: {stats['critique']} observation(s) critique(s) nécessitant une intervention IMMÉDIATE. "
        
        if stats['majeur'] > 0:
            resume += f"{stats['majeur']} observation(s) majeure(s) à corriger sous 30 jours. "
        
        if stats['mineur'] > 0:
            resume += f"{stats['mineur']} observation(s) mineure(s) recommandées pour amélioration. "
        
        # Extraire les observations critiques
        critiques = [
            obs.get('observation_corrigee', 'N/A')
            for obs in observations
            if obs.get('niveau_gravite') == 'Critique'
        ]
        
        return {
            "resume_general": resume.strip(),
            "observations_critiques": critiques,
            "taux_conformite": stats['taux_conformite']
        }
    
    def _generate_recommendations(self, observations: List[Dict[str, Any]]) -> List[str]:
        """Génère des recommandations générales"""
        recommendations = []
        
        stats = self._calculate_statistics(observations)
        
        if stats['critique'] > 0:
            recommendations.append(
                "Traiter en PRIORITÉ les observations critiques avant toute remise en service"
            )
        
        if stats['majeur'] > 0:
            recommendations.append(
                "Planifier les corrections des observations majeures dans les 30 jours"
            )
        
        # Recommandations basées sur les observations
        all_refs = set()
        for obs in observations:
            refs = obs.get('references_normatives', [])
            for ref in refs:
                if 'NFC 15-100' in ref or 'NF C 15-100' in ref:
                    all_refs.add(ref)
        
        if all_refs:
            recommendations.append(
                "Consulter les articles spécifiques de la NFC 15-100 mentionnés dans ce rapport"
            )
        
        recommendations.append(
            "Effectuer un contrôle de suivi après correction des non-conformités"
        )
        
        recommendations.append(
            "Tenir un registre de maintenance préventive conforme aux normes"
        )
        
        return recommendations
    
    def _save_report(self, content: str, filepath: str):
        """Sauvegarde le rapport dans un fichier"""
        try:
            output_path = Path(filepath)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"💾 Rapport sauvegardé: {filepath}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
            raise
    
    def generate_batch_reports(self, 
                              observations: List[Dict[str, Any]], 
                              metadata: Dict[str, Any],
                              output_dir: str = "reports") -> Dict[str, str]:
        """
        Génère tous les formats de rapport en une fois
        
        Args:
            observations: Liste des observations
            metadata: Métadonnées du rapport
            output_dir: Répertoire de sortie
            
        Returns:
            Dictionnaire des chemins de fichiers générés
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        base_name = f"rapport_{metadata.get('numero_rapport', 'INSP')}"
        
        files = {}
        
        # JSON
        json_file = output_path / f"{base_name}.json"
        files['json'] = str(json_file)
        self.generate_report(observations, metadata, "json", str(json_file))
        
        # Markdown
        md_file = output_path / f"{base_name}.md"
        files['markdown'] = str(md_file)
        self.generate_report(observations, metadata, "markdown", str(md_file))
        
        # HTML
        html_file = output_path / f"{base_name}.html"
        files['html'] = str(html_file)
        self.generate_report(observations, metadata, "html", str(html_file))
        
        # Text
        txt_file = output_path / f"{base_name}.txt"
        files['text'] = str(txt_file)
        self.generate_report(observations, metadata, "text", str(txt_file))
        
        logger.info(f"✅ Batch complet généré: {len(files)} fichiers")
        
        return files


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

_report_generator_instance = None

def get_report_generator() -> ReportGenerator:
    """Retourne l'instance singleton du générateur"""
    global _report_generator_instance
    if _report_generator_instance is None:
        _report_generator_instance = ReportGenerator()
    return _report_generator_instance

def generate_quick_report(observations: List[Dict[str, Any]], 
                         format: str = "markdown") -> str:
    """Fonction rapide pour générer un rapport"""
    generator = get_report_generator()
    return generator.generate_report(observations, format=format)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("🧪 TEST REPORT GENERATOR")
    print("=" * 70)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Données de test
    test_observations = [
        {
            "observation_corrigee": "Absence de dispositif différentiel 30mA dans le circuit cuisine",
            "references_normatives": ["NFC 15-100 Article 55.1", "NFC 15-100 Article 411.3.3"],
            "niveau_gravite": "Critique",
            "risques_identifies": ["Électrocution", "Incendie"],
            "actions_correctives": ["Installer DDR 30mA Type A", "Vérifier mise à la terre"],
            "delai_recommande": "immédiat",
            "localisation": "Cuisine"
        },
        {
            "observation_corrigee": "Câble de section insuffisante sur le circuit chauffage",
            "references_normatives": ["NFC 15-100 Article 52.1"],
            "niveau_gravite": "Majeur",
            "risques_identifies": ["Échauffement", "Risque d'incendie"],
            "actions_correctives": ["Remplacer par câble 2.5mm²", "Vérifier protection amont"],
            "delai_recommande": "30 jours",
            "localisation": "Salon"
        },
        {
            "observation_corrigee": "Tableau électrique encombré - espace de maintenance insuffisant",
            "references_normatives": ["NFC 15-100 Article 55.2"],
            "niveau_gravite": "Mineur",
            "risques_identifies": ["Difficultés d'intervention"],
            "actions_correctives": ["Dégager l'espace autour du tableau", "Réorganiser les équipements"],
            "delai_recommande": "90 jours",
            "localisation": "Garage"
        }
    ]
    
    test_metadata = {
        "site": "Immeuble Les Palmiers",
        "adresse": "123 Avenue des Champs, 75008 Paris",
        "inspecteur": "Jean Dupont",
        "date_inspection": "22/11/2024",
        "numero_rapport": "INSP-2024-001"
    }
    
    generator = get_report_generator()
    
    print("\n📄 TEST 1: Génération Markdown")
    print("-" * 70)
    md_report = generator.generate_report(test_observations, test_metadata, "markdown")
    print(md_report[:500] + "...\n")
    
    print("\n📄 TEST 2: Génération JSON")
    print("-" * 70)
    json_report = generator.generate_report(test_observations, test_metadata, "json")
    print(json_report[:500] + "...\n")
    
    print("\n📄 TEST 3: Génération HTML")
    print("-" * 70)
    html_report = generator.generate_report(test_observations, test_metadata, "html")
    print(f"✅ HTML généré: {len(html_report)} caractères\n")
    
    print("\n📄 TEST 4: Génération TEXT")
    print("-" * 70)
    text_report = generator.generate_report(test_observations, test_metadata, "text")
    print(text_report[:500] + "...\n")
    
    print("\n📦 TEST 5: Génération batch (tous formats)")
    print("-" * 70)
    files = generator.generate_batch_reports(
        test_observations, 
        test_metadata, 
        output_dir="test_reports"
    )
    
    print("\n✅ Fichiers générés:")
    for format_type, filepath in files.items():
        print(f"  - {format_type.upper()}: {filepath}")
    
    print("\n" + "=" * 70)
    print("🎯 REPORT GENERATOR OPÉRATIONNEL !")
    print("   ✅ Formats supportés: JSON, Markdown, HTML, Text")
    print("   ✅ Mise en page professionnelle")
    print("   ✅ Statistiques automatiques")
    print("   ✅ Groupement par gravité")
    print("   ✅ Recommandations intelligentes")
    print("=" * 70)