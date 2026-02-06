# script/pyqt_widgets.py
#!/usr/bin/env python3
"""
Widgets PyQt6 pour l'interface utilisateur
Version COMPLÈTE avec toutes les classes
"""

import logging
from typing import List, Dict, Any

# PyQt6
try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
    from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, 
                                 QListWidget, QListWidgetItem, QLabel, 
                                 QPushButton, QTextCursor)
    from PyQt6.QtGui import QFont, QColor
except ImportError as e:
    print(f"⚠️ PyQt6 non disponible : {e}")
    print("Installez avec: pip install PyQt6")
    raise

logger = logging.getLogger(__name__)


class SimpleSuggestionManager:
    """Gestionnaire de suggestions simplifié pour le test"""
    def __init__(self):
        # Données de test basées sur vos prescriptions
        self.test_suggestions = {
            "remp": ["Remplacer le câble rigide par un souple", 
                    "Remplacer le DDR défectueux",
                    "Remplacer le disjoncteur"],
            "câb": ["câble d'alimentation", "câble section insuffisante"],
            "prot": ["protection différentielle", "protection contre les contacts directs"],
            "diff": ["différentiel 30mA", "différentiel type A"],
            "terr": ["mise à la terre", "prise de terre"]
        }
    
    def get_autocomplete_suggestions(self, prefix: str) -> List[str]:
        """Retourne des suggestions basiques"""
        prefix_lower = prefix.lower()
        results = []
        
        # Recherche dans les clés
        for key, suggestions in self.test_suggestions.items():
            if key.startswith(prefix_lower[:3]):
                results.extend(suggestions)
        
        # Suggestions génériques si vide
        if not results and len(prefix) >= 2:
            results = [
                f"{prefix} [suggestion 1]",
                f"{prefix} [suggestion 2]",
                f"{prefix} [suggestion 3]"
            ]
        
        return list(set(results))[:5]  # Limite à 5, sans doublons
    
    def validate_and_suggest_norms(self, text: str):
        """Version simplifiée"""
        logger.info(f"Validation de: {text}")
        
        # Simulation de normes
        normes = [
            {"reference": "NFC 15-100 Article 411.3.3", "confidence": 0.85},
            {"reference": "NF C 15-100 § 531", "confidence": 0.75},
            {"reference": "R.4226-12", "confidence": 0.65}
        ]
        
        # Simulation de prescription
        prescription = {
            "id": "test_001",
            "text": text[:50],
            "theme": "Test"
        }
        
        return prescription, normes


class AutoCompleteTextEdit(QTextEdit):
    """Zone de texte avec auto-complétion"""
    
    suggestionSelected = pyqtSignal(dict)  # Quand une suggestion est choisie
    textValidated = pyqtSignal(str)       # Quand le texte est validé
    
    def __init__(self, suggestion_manager=None, parent=None):
        super().__init__(parent)
        self.suggestion_manager = suggestion_manager or SimpleSuggestionManager()
        self.suggestions = []
        self.current_prefix = ""
        self.setup_ui()
        self.setup_timers()
        
    def setup_ui(self):
        """Configure l'interface"""
        self.setPlaceholderText("Commencez à taper... (ex: 'remp', 'câb', 'prot')")
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.setFont(QFont("Arial", 11))
        
        # Popup de suggestions
        self.suggestion_popup = QListWidget()
        self.suggestion_popup.setWindowFlags(Qt.WindowType.Popup)
        self.suggestion_popup.setVisible(False)
        self.suggestion_popup.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        self.suggestion_popup.itemClicked.connect(self.on_suggestion_clicked)
        
    def setup_timers(self):
        """Configure les timers pour l'auto-complétion"""
        self.suggestion_timer = QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.setInterval(300)  # 300ms de délai
        self.suggestion_timer.timeout.connect(self.show_suggestions)
        
    def keyPressEvent(self, event):
        """Gère les touches"""
        # ENTER = valider
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.validate_text()
            return
        
        # ESC = cacher suggestions
        elif event.key() == Qt.Key.Key_Escape:
            self.hide_suggestions()
        
        # Flèche bas = naviguer dans suggestions
        elif event.key() == Qt.Key.Key_Down and self.suggestion_popup.isVisible():
            self.suggestion_popup.setFocus()
            if self.suggestion_popup.count() > 0:
                self.suggestion_popup.setCurrentRow(0)
        
        else:
            super().keyPressEvent(event)
            
            # Démarre le timer pour suggestions
            self.suggestion_timer.start()
    
    def validate_text(self):
        """Valide le texte actuel"""
        text = self.toPlainText().strip()
        if text:
            logger.info(f"✅ Texte validé: {text}")
            self.textValidated.emit(text)
            self.hide_suggestions()
    
    def show_suggestions(self):
        """Affiche les suggestions d'auto-complétion"""
        text = self.toPlainText()
        
        if len(text) < 2:
            self.hide_suggestions()
            return
        
        # Récupère le mot courant
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        current_word = cursor.selectedText()
        
        if not current_word or len(current_word) < 2:
            # Si pas de mot sélectionné, prendre les derniers caractères
            current_word = text.split()[-1] if text.split() else text
        
        if len(current_word) < 2:
            self.hide_suggestions()
            return
        
        # Récupère les suggestions
        self.current_prefix = current_word
        suggestions = self.suggestion_manager.get_autocomplete_suggestions(current_word)
        
        if not suggestions:
            self.hide_suggestions()
            return
        
        # Met à jour la popup
        self.suggestion_popup.clear()
        for suggestion in suggestions:
            item = QListWidgetItem(suggestion)
            self.suggestion_popup.addItem(item)
        
        # Positionne la popup
        cursor_rect = self.cursorRect()
        popup_pos = self.mapToGlobal(cursor_rect.bottomLeft())
        self.suggestion_popup.move(popup_pos)
        self.suggestion_popup.setFixedWidth(400)
        self.suggestion_popup.setFixedHeight(min(200, len(suggestions) * 30 + 10))
        self.suggestion_popup.show()
    
    def hide_suggestions(self):
        """Cache la popup de suggestions"""
        self.suggestion_popup.hide()
    
    def on_suggestion_clicked(self, item):
        """Quand une suggestion est cliquée"""
        suggestion_text = item.text()
        
        # Remplacer le texte complet
        self.setText(suggestion_text)
        
        # Émettre le signal
        self.suggestionSelected.emit({
            'text': suggestion_text,
            'prefix': self.current_prefix
        })
        
        self.hide_suggestions()
        logger.info(f"🔤 Suggestion sélectionnée: {suggestion_text}")


class NormSuggestionWidget(QWidget):
    """Affiche les suggestions de normes"""
    
    normSelected = pyqtSignal(dict)  # Quand une norme est choisie
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Titre
        title = QLabel("Normes suggérées :")
        title.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                color: #2c3e50; 
                font-size: 12px;
                padding-bottom: 5px;
            }
        """)
        layout.addWidget(title)
        
        # Liste des normes
        self.norm_list = QListWidget()
        self.norm_list.setMaximumHeight(150)
        self.norm_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: #f9f9f9;
            }
        """)
        self.norm_list.itemClicked.connect(self.on_norm_clicked)
        layout.addWidget(self.norm_list)
        
        # Bouton
        self.insert_button = QPushButton("📋 Insérer la norme sélectionnée")
        self.insert_button.setEnabled(False)
        self.insert_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.insert_button.clicked.connect(self.emit_selected_norm)
        layout.addWidget(self.insert_button)
        
    def update_norms(self, norms: List[Dict[str, Any]]):
        """Met à jour la liste des normes"""
        self.norm_list.clear()
        
        if not norms:
            item = QListWidgetItem("Aucune norme suggérée")
            item.setForeground(QColor("#7f8c8d"))
            self.norm_list.addItem(item)
            self.insert_button.setEnabled(False)
            return
        
        self.insert_button.setEnabled(True)
        
        for norm in norms:
            item_text = f"📜 {norm['reference']}"
            if 'confidence' in norm:
                item_text += f" (confiance: {norm['confidence']:.0%})"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, norm)
            
            # Couleur selon la confiance
            if 'confidence' in norm:
                if norm['confidence'] > 0.8:
                    item.setForeground(QColor("#27ae60"))  # Vert
                elif norm['confidence'] > 0.6:
                    item.setForeground(QColor("#2980b9"))  # Bleu
                else:
                    item.setForeground(QColor("#f39c12"))  # Orange
            
            self.norm_list.addItem(item)
        
        # Sélectionne le premier élément
        self.norm_list.setCurrentRow(0)
    
    def on_norm_clicked(self, item):
        """Quand une norme est cliquée"""
        norm = item.data(Qt.ItemDataRole.UserRole)
        if norm:
            self.normSelected.emit(norm)
    
    def emit_selected_norm(self):
        """Émet la norme sélectionnée"""
        current_item = self.norm_list.currentItem()
        if current_item:
            norm = current_item.data(Qt.ItemDataRole.UserRole)
            if norm:
                self.normSelected.emit(norm)
                logger.info(f"📜 Norme émise: {norm['reference']}")


class SuggestionPanel(QWidget):
    """Panel complet de suggestions (auto-complétion + normes)"""
    
    prescriptionValidated = pyqtSignal(str)  # Quand une prescription est validée
    normInserted = pyqtSignal(str)          # Quand une norme est insérée
    
    def __init__(self, suggestion_manager=None, parent=None):
        super().__init__(parent)
        self.suggestion_manager = suggestion_manager or SimpleSuggestionManager()
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Zone de texte avec auto-complétion
        input_label = QLabel("📝 Prescription :")
        input_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(input_label)
        
        self.text_edit = AutoCompleteTextEdit(self.suggestion_manager, self)
        layout.addWidget(self.text_edit)
        
        # Suggestions de normes
        self.norm_widget = NormSuggestionWidget(self)
        layout.addWidget(self.norm_widget)
        
        # Bouton de validation
        self.validate_button = QPushButton("✅ Valider la prescription")
        self.validate_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.validate_button.clicked.connect(self.validate_prescription)
        layout.addWidget(self.validate_button)
        
    def setup_connections(self):
        """Connecte les signaux"""
        self.text_edit.textValidated.connect(self.on_text_validated)
        self.norm_widget.normSelected.connect(self.on_norm_selected)
        self.text_edit.suggestionSelected.connect(self.on_suggestion_selected)
    
    def on_text_validated(self, text: str):
        """Quand le texte est validé"""
        logger.info(f"🔍 Validation de la prescription: {text}")
        
        try:
            prescription, normes = self.suggestion_manager.validate_and_suggest_norms(text)
            
            if prescription:
                logger.info(f"✅ Prescription validée: {prescription.get('id', 'N/A')}")
            
            # Affiche les normes suggérées
            self.norm_widget.update_norms(normes)
            
            # Émet le signal
            self.prescriptionValidated.emit(text)
            
        except Exception as e:
            logger.error(f"❌ Erreur validation: {e}")
    
    def on_suggestion_selected(self, suggestion: Dict):
        """Quand une suggestion d'auto-complétion est sélectionnée"""
        logger.info(f"🔤 Suggestion sélectionnée: {suggestion['text'][:50]}...")
        # Auto-validation après sélection
        self.on_text_validated(suggestion['text'])
    
    def on_norm_selected(self, norm: Dict):
        """Quand une norme est sélectionnée"""
        norm_text = norm['reference']
        logger.info(f"📜 Norme sélectionnée: {norm_text}")
        
        # Émet le signal pour insertion
        self.normInserted.emit(norm_text)
    
    def validate_prescription(self):
        """Valide manuellement la prescription"""
        text = self.text_edit.toPlainText().strip()
        if text:
            logger.info(f"🔄 Validation manuelle: {text}")
            self.on_text_validated(text)
        else:
            logger.warning("⚠️ Aucun texte à valider")
    
    def clear(self):
        """Réinitialise le panel"""
        self.text_edit.clear()
        self.norm_widget.update_norms([])
        logger.info("🧹 Panel réinitialisé")


# ============================================================================
# FONCTIONS D'UTILITAIRE ET TEST
# ============================================================================

class SimpleDemoWindow(QWidget):
    """Fenêtre de démonstration simplifiée"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Démo Auto-complétion")
        self.setGeometry(100, 100, 500, 400)
        
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("🎯 Test Auto-complétion")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Testez avec: 'remp', 'câb', 'prot', 'diff', 'terr'\n"
            "Appuyez sur Entrée pour valider"
        )
        instructions.setStyleSheet("color: #7f8c8d; padding: 5px;")
        layout.addWidget(instructions)
        
        # Panel de suggestions
        self.panel = SuggestionPanel()
        layout.addWidget(self.panel)
        
        # Logs
        self.log_label = QLabel("État: Prêt")
        self.log_label.setStyleSheet("background-color: #f1f2f6; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.log_label)
        
        # Connecte les signaux
        self.panel.prescriptionValidated.connect(
            lambda text: self.log_label.setText(f"✅ Validé: {text[:30]}...")
        )
        self.panel.normInserted.connect(
            lambda norm: self.log_label.setText(f"📜 Norme: {norm}")
        )


def test_widgets():
    """Teste les widgets indépendamment"""
    print("🧪 Test des widgets PyQt6...")
    
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    window = SimpleDemoWindow()
    window.show()
    
    print("✅ Widgets fonctionnels!")
    print("💡 Testez avec: remp, câb, prot, diff, terr")
    
    sys.exit(app.exec())


# ============================================================================
# EXPORTS
# ============================================================================

# Exportez toutes les classes nécessaires
__all__ = [
    'SimpleSuggestionManager',
    'AutoCompleteTextEdit',
    'NormSuggestionWidget',
    'SuggestionPanel',
    'SimpleDemoWindow',
    'test_widgets'
]

if __name__ == "__main__":
    print("✅ Module PyQt Widgets chargé")
    print("📋 Widgets disponibles :")
    print("  - SimpleSuggestionManager")
    print("  - AutoCompleteTextEdit")
    print("  - NormSuggestionWidget")
    print("  - SuggestionPanel")
    print("  - SimpleDemoWindow (pour test rapide)")
    print("\n🧪 Pour tester: python pyqt_widgets.py")
    print("   ou: python -c 'import pyqt_widgets; pyqt_widgets.test_widgets()'")
    
    # Lancez le test si exécuté directement
    test_widgets()