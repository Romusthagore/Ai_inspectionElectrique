# script/app1.py
#!/usr/bin/env python3
"""
Application PyQt6 avec auto-complétion - Version SIMPLIFIÉE
"""

import sys
import os
import logging

# Configurez le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajoutez le chemin courant pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 Lancement de l'application...")

# Vérifiez et importez PyQt6
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton
    from PyQt6.QtCore import Qt
    print("✅ PyQt6 importé avec succès")
except ImportError as e:
    print(f"❌ PyQt6 non disponible : {e}")
    print("📦 Installez-le avec : pip install PyQt6")
    sys.exit(1)

# Importez vos widgets locaux
try:
    from pyqt_widgets import SuggestionPanel, SimpleSuggestionManager
    print("✅ Widgets PyQt importés")
except ImportError as e:
    print(f"❌ Erreur import widgets : {e}")
    print("📁 Assurez-vous que 'pyqt_widgets.py' est dans le même dossier")
    sys.exit(1)

# Essayez d'importer le moteur d'auto-complétion (optionnel)
try:
    from autocomplete_engine import create_suggestion_manager
    AUTOCOMPLETE_AVAILABLE = True
    print("✅ Moteur d'auto-complétion importé")
except ImportError:
    AUTOCOMPLETE_AVAILABLE = False
    print("⚠️ Moteur d'auto-complétion non disponible - utilisation du mode test")


class DemoApplication(QMainWindow):
    """Application de démonstration"""
    
    def __init__(self):
        super().__init__()
        
        # Initialisez le gestionnaire de suggestions
        self.suggestion_manager = self.create_suggestion_manager()
        
        self.setup_ui()
        self.setup_connections()
        
        logger.info("🎯 Application prête")
        print("✅ Interface graphique initialisée")
    
    def create_suggestion_manager(self):
        """Crée le gestionnaire de suggestions"""
        try:
            # Essayez de charger les données réelles
            if AUTOCOMPLETE_AVAILABLE:
                data_file = "../data/document_json/observations_validees.json"
                if os.path.exists(data_file):
                    manager = create_suggestion_manager(data_file)
                    print(f"✅ Données chargées depuis: {data_file}")
                    return manager
                else:
                    print(f"⚠️ Fichier non trouvé: {data_file}")
            
            # Sinon, utilisez le mode test
            print("🔧 Utilisation du mode test")
            return SimpleSuggestionManager()
            
        except Exception as e:
            logger.error(f"Erreur création manager: {e}")
            print(f"⚠️ Erreur: {e}")
            return SimpleSuggestionManager()
    
    def setup_ui(self):
        """Configure l'interface"""
        self.setWindowTitle("Assistant Rédaction - Auto-complétion")
        self.setGeometry(100, 100, 700, 500)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # En-tête
        header = QLabel("🎯 Système d'Auto-complétion Intelligent")
        header.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                color: white;
                border-radius: 10px;
                text-align: center;
            }
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Instructions
        instructions = QLabel(
            "💡 <b>Comment utiliser :</b><br>"
            "1. Tapez quelques lettres (ex: 'remp', 'câb', 'prot')<br>"
            "2. Sélectionnez une suggestion avec la souris ou flèches<br>"
            "3. Appuyez sur <b>Entrée</b> pour valider<br>"
            "4. Les normes suggérées apparaîtront automatiquement"
        )
        instructions.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #34495e;
                padding: 15px;
                background-color: #f8f9fa;
                border: 1px dashed #bdc3c7;
                border-radius: 8px;
            }
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Panel de suggestions
        self.panel = SuggestionPanel(self.suggestion_manager, self)
        layout.addWidget(self.panel)
        
        # Zone de statut
        self.status_label = QLabel("🟢 Prêt - Tapez pour commencer")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Boutons
        button_layout = QVBoxLayout()
        
        # Bouton test
        test_button = QPushButton("🧪 Tester l'auto-complétion")
        test_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        test_button.clicked.connect(self.run_tests)
        button_layout.addWidget(test_button)
        
        # Bouton effacer
        clear_button = QPushButton("🗑️  Tout effacer")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_button)
        
        layout.addLayout(button_layout)
        
        # Pied de page
        footer = QLabel(
            f"📊 Mode: {'REEL' if AUTOCOMPLETE_AVAILABLE else 'TEST'} | "
            f"© 2024 Assistant Électrique | v1.0"
        )
        footer.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #95a5a6;
                padding: 8px;
                text-align: center;
                border-top: 1px solid #ecf0f1;
                margin-top: 10px;
            }
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
    
    def setup_connections(self):
        """Connecte les signaux"""
        self.panel.prescriptionValidated.connect(self.on_prescription_validated)
        self.panel.normInserted.connect(self.on_norm_inserted)
    
    def on_prescription_validated(self, text: str):
        """Quand une prescription est validée"""
        self.status_label.setText(f"✅ Validé: {text[:40]}...")
        print(f"📝 Prescription: {text}")
    
    def on_norm_inserted(self, norm: str):
        """Quand une norme est insérée"""
        self.status_label.setText(f"📜 Norme insérée: {norm}")
        print(f"📜 Norme: {norm}")
    
    def run_tests(self):
        """Exécute des tests"""
        print("\n🧪 Lancement des tests...")
        
        test_cases = ["remp", "câb", "prot", "diff", "terr"]
        
        for prefix in test_cases:
            suggestions = self.suggestion_manager.get_autocomplete_suggestions(prefix)
            if suggestions:
                print(f"  '{prefix}' → {suggestions[:2]}")
        
        self.status_label.setText("🧪 Tests terminés - Voir console")
        print("✅ Tests terminés\n")
    
    def clear_all(self):
        """Efface tout"""
        self.panel.clear()
        self.status_label.setText("🧹 Tout effacé - Prêt à recommencer")
        print("🧹 Interface réinitialisée")


def main():
    """Point d'entrée principal"""
    print("\n" + "="*50)
    print("   ASSISTANT RÉDACTION - AUTO-COMPLÉTION")
    print("="*50)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Style moderne
    
    # Applique une palette de couleurs
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f7fa;
        }
        QTextEdit, QListWidget {
            border: 1px solid #d1d8e0;
            border-radius: 4px;
            padding: 5px;
            background-color: white;
        }
        QTextEdit:focus, QListWidget:focus {
            border: 2px solid #3498db;
        }
    """)
    
    window = DemoApplication()
    window.show()
    
    print("\n🎮 Application lancée avec succès!")
    print("💡 Tapez dans la zone de texte pour tester l'auto-complétion")
    print("🔄 Appuyez sur Entrée pour valider")
    print("❌ Fermez la fenêtre pour quitter\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()