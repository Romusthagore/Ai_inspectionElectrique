#!/usr/bin/env python3
"""
Application PyQt6 - Système d'Inspection Électrique Intelligent
Interface inspirée de Claude avec zone de conversation et reformulation
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QSplitter, QTabWidget,
    QLineEdit, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Imports de vos modules
try:
    from vector_store import get_vector_store
    from correction_pipeline import get_correction_pipeline
    from suggestion_engine import get_suggestion_engine
    from report_generator import get_report_generator
except ImportError as e:
    print(f"❌ Erreur import : {e}")
    sys.exit(1)

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# WORKER THREAD POUR SUGGESTIONS
# =============================================================================

class SuggestionWorker(QThread):
    """Thread pour générer les suggestions sans bloquer l'UI"""
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, suggestion_engine, text: str):
        super().__init__()
        self.suggestion_engine = suggestion_engine
        self.text = text
    
    def run(self):
        try:
            suggestions = self.suggestion_engine.get_suggestions(self.text)
            self.finished.emit(suggestions)
        except Exception as e:
            logger.error(f"Erreur dans SuggestionWorker: {e}")
            self.error.emit(str(e))


class CorrectionWorker(QThread):
    """Thread pour la correction/reformulation"""
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, correction_pipeline, text: str, location: str = ""):
        super().__init__()
        self.correction_pipeline = correction_pipeline
        self.text = text
        self.location = location
    
    def run(self):
        try:
            if self.location:
                text = f"{self.text} - Localisation: {self.location}"
            else:
                text = self.text
            
            result = self.correction_pipeline.corriger_observation(text)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Erreur dans CorrectionWorker: {e}")
            self.error.emit(str(e))


# =============================================================================
# MESSAGE BUBBLE WIDGET
# =============================================================================

class MessageBubble(QFrame):
    """Bulle de message style chat"""
    
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        
        # Label pour le texte
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        
        if is_user:
            self.text_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 14px;
                    line-height: 1.5;
                    background: transparent;
                }
            """)
            self.setStyleSheet("""
                QFrame {
                    background-color: #2F2F2F;
                    border-radius: 12px;
                    border: 1px solid #3F3F3F;
                }
            """)
        else:
            self.text_label.setStyleSheet("""
                QLabel {
                    color: #E8E8E8;
                    font-size: 14px;
                    line-height: 1.5;
                    background: transparent;
                }
            """)
            self.setStyleSheet("""
                QFrame {
                    background-color: #1E1E1E;
                    border-radius: 12px;
                    border: 1px solid #2E2E2E;
                }
            """)
        
        layout.addWidget(self.text_label)


# =============================================================================
# SUGGESTION CARD WIDGET
# =============================================================================

class SuggestionCard(QFrame):
    """Carte de suggestion cliquable"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, title: str, text: str, icon: str = "✨", parent=None):
        super().__init__(parent)
        
        self.suggestion_text = text
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # En-tête avec icône
        header_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #A0A0A0;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Texte de suggestion
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("""
            QLabel {
                color: #E8E8E8;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(text_label)
        
        # Style de la carte
        self.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
            }
            QFrame:hover {
                background-color: #323232;
                border: 1px solid #4A4A4A;
            }
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.suggestion_text)
        super().mousePressEvent(event)


# =============================================================================
# FENÊTRE PRINCIPALE
# =============================================================================

class MainWindow(QMainWindow):
    """Fenêtre principale style Claude"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("⚡ Inspection Électrique - Assistant IA")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialisation des composants IA
        self.init_ai_components()
        
        # Variables
        self.current_suggestions = None
        self.conversation_history = []
        self.suggestion_timer = QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self.trigger_suggestions)
        self.last_suggestion_text = ""  # Pour éviter les doublons
        
        # Initialiser l'interface
        self.init_ui()
        
        # Style
        self.apply_claude_theme()
    
    def init_ai_components(self):
        """Initialiser les composants IA"""
        try:
            logger.info("🔧 Initialisation des composants IA...")
            
            self.vectorstore = get_vector_store()
            self.correction_pipeline = get_correction_pipeline()
            self.report_generator = get_report_generator()
            
            # Extraire le LLM
            if hasattr(self.correction_pipeline, 'llm'):
                llm = self.correction_pipeline.llm
            else:
                llm = self.correction_pipeline._llm
            
            self.suggestion_engine = get_suggestion_engine(
                vectorstore=self.vectorstore,
                llm=llm
            )
            
            logger.info("✅ Composants IA initialisés")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation IA : {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'initialiser l'IA : {e}")
            sys.exit(1)
    
    def init_ui(self):
        """Initialiser l'interface utilisateur"""
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # En-tête
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Zone principale avec conversation
        content = self.create_content_area()
        main_layout.addWidget(content, 1)
        
        # Zone de saisie en bas (fixe)
        input_area = self.create_input_area()
        main_layout.addWidget(input_area)
        
        # Status bar
        self.statusBar().showMessage("✅ Assistant IA prêt")
    
    def create_header(self):
        """Créer l'en-tête"""
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet("""
            QFrame {
                background-color: #1E1E1E;
                border-bottom: 1px solid #2E2E2E;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # Bouton Paramètres en haut à gauche
        btn_settings = QPushButton("⚙️")
        btn_settings.setFixedSize(40, 40)
        btn_settings.setToolTip("Paramètres")
        btn_settings.clicked.connect(self.show_settings)
        btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #2F2F2F;
                color: #E8E8E8;
                border: 1px solid #3F3F3F;
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
                border: 1px solid #4A4A4A;
            }
        """)
        layout.addWidget(btn_settings)
        
        # Espacement
        layout.addSpacing(20)
        
        # Logo et titre
        title_layout = QVBoxLayout()
        title = QLabel("⚡ Assistant d'Inspection Électrique")
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 600;
            }
        """)
        subtitle = QLabel("Powered by AI • Reformulation intelligente")
        subtitle.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 12px;
            }
        """)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_layout.setSpacing(2)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Bouton nouvelle conversation
        btn_new = QPushButton("Nouvelle conversation")
        btn_new.clicked.connect(self.new_conversation)
        btn_new.setStyleSheet("""
            QPushButton {
                background-color: #2F2F2F;
                color: #E8E8E8;
                border: 1px solid #3F3F3F;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
                border: 1px solid #4A4A4A;
            }
        """)
        layout.addWidget(btn_new)
        
        return header
    
    def create_content_area(self):
        """Créer la zone de contenu avec conversation"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Zone de conversation (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #159595;
            }
        """)
        
        # Conteneur des messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(24, 24, 24, 24)
        self.messages_layout.setSpacing(16)
        self.messages_layout.addStretch()
        
        scroll.setWidget(self.messages_container)
        layout.addWidget(scroll)
        
        # Zone des suggestions (cachée par défaut)
        self.suggestions_area = QWidget()
        suggestions_layout = QVBoxLayout(self.suggestions_area)
        suggestions_layout.setContentsMargins(24, 16, 24, 16)
        suggestions_layout.setSpacing(12)
        
        sugg_title = QLabel("💡 Suggestions de reformulation")
        sugg_title.setStyleSheet("""
            QLabel {
                color: #A0A0A0;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        suggestions_layout.addWidget(sugg_title)
        
        # Conteneur pour les cartes de suggestions
        self.suggestions_cards = QVBoxLayout()
        self.suggestions_cards.setSpacing(8)
        suggestions_layout.addLayout(self.suggestions_cards)
        
        self.suggestions_area.setStyleSheet("""
            QWidget {
                background-color: #1A1A1A;
                border-top: 1px solid #2E2E2E;
            }
        """)
        self.suggestions_area.hide()
        
        layout.addWidget(self.suggestions_area)
        
        return content
    
    def create_input_area(self):
        """Créer la zone de saisie en bas"""
        input_widget = QFrame()
        input_widget.setStyleSheet("""
            QFrame {
                background-color: #1E1E1E;
                border-top: 1px solid #2E2E2E;
            }
        """)
        
        layout = QVBoxLayout(input_widget)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)
        
        # Zone de saisie
        input_container = QHBoxLayout()
        
        # TextEdit pour saisie
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Décrivez votre observation électrique...")
        self.input_text.setMaximumHeight(120)
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                padding: 12px;
                color: #E8E8E8;
                font-size: 14px;
                selection-background-color: #4A4A4A;
            }
            QTextEdit:focus {
                border: 1px solid #4A4A4A;
            }
        """)
        
        # Connecter le signal de texte modifié pour les suggestions automatiques
        self.input_text.textChanged.connect(self.on_text_changed)
        
        input_container.addWidget(self.input_text, 1)
        
        # Boutons d'action
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Bouton Reformuler (principal)
        self.btn_reformulate = QPushButton("✨ Reformuler")
        self.btn_reformulate.setFixedSize(140, 45)
        self.btn_reformulate.clicked.connect(self.reformulate_observation)
        self.btn_reformulate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c8ff5, stop:1 #8a5fb8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5668d8, stop:1 #653a8e);
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #606060;
            }
        """)
        buttons_layout.addWidget(self.btn_reformulate)
        
        # Bouton Chatbot Ins (remplace Suggestions)
        self.btn_chatbot = QPushButton("🤖 Chatbot Ins")
        self.btn_chatbot.setFixedSize(140, 38)
        self.btn_chatbot.clicked.connect(self.open_chatbot)
        self.btn_chatbot.setStyleSheet("""
            QPushButton {
                background-color: #2A2A2A;
                color: #E8E8E8;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #323232;
                border: 1px solid #4A4A4A;
            }
            QPushButton:disabled {
                background-color: #1A1A1A;
                color: #606060;
            }
        """)
        buttons_layout.addWidget(self.btn_chatbot)
        
        input_container.addLayout(buttons_layout)
        
        layout.addLayout(input_container)
        
        # Localisation (optionnel)
        location_layout = QHBoxLayout()
        location_label = QLabel("📍 Localisation (optionnel):")
        location_label.setStyleSheet("color: #808080; font-size: 12px;")
        self.input_location = QLineEdit()
        self.input_location.setPlaceholderText("Ex: Cuisine, Tableau principal...")
        self.input_location.setMaximumWidth(300)
        self.input_location.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px 12px;
                color: #E8E8E8;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4A4A4A;
            }
        """)
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.input_location)
        location_layout.addStretch()
        
        layout.addLayout(location_layout)
        
        return input_widget
    
    # =========================================================================
    # GESTION DES SUGGESTIONS AUTOMATIQUES
    # =========================================================================
    
    def on_text_changed(self):
        text = self.input_text.toPlainText().strip()
        self.suggestion_timer.stop()

        if len(text) >= 3:          # seulement si >=3 caractères
            self.suggestion_timer.start(800)
        else:
            self.suggestions_area.hide()          # cacher suggestions si <3
            self.last_suggestion_text = ""

    def trigger_suggestions(self):
        text = self.input_text.toPlainText().strip()
        
        if len(text) < 3:
            self.suggestions_area.hide()
            return
        
        if text == self.last_suggestion_text:
            return

        self.last_suggestion_text = text
        self.get_suggestions(auto_mode=True)

    
    # =========================================================================
    # GESTION DES MESSAGES
    # =========================================================================
    
    def add_message(self, text: str, is_user: bool = True):
        """Ajouter un message à la conversation"""
        
        # Créer le conteneur du message
        message_container = QWidget()
        container_layout = QHBoxLayout(message_container)
        container_layout.setContentsMargins(100, 100, 100, 100)
        
        # Créer la bulle
        bubble = MessageBubble(text, is_user)
        bubble.setMaximumWidth(2000)
        
        # Alignement
        if is_user:
            container_layout.addStretch()
            container_layout.addWidget(bubble)
        else:
            container_layout.addWidget(bubble)
            container_layout.addStretch()
        
        # Insérer avant le stretch
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, message_container)
        
        # Scroller vers le bas
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroller vers le bas de la conversation"""
        scroll_area = self.messages_container.parent().parent()
        if isinstance(scroll_area, QScrollArea):
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
    
    # =========================================================================
    # REFORMULATION
    # =========================================================================
    
    def reformulate_observation(self):
        """Reformuler l'observation"""
        text = self.input_text.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, "Attention", "Veuillez saisir une observation")
            return
        
        location = self.input_location.text().strip()
        
        # Désactiver les boutons
        self.btn_reformulate.setEnabled(False)
        self.btn_chatbot.setEnabled(False)
        self.btn_reformulate.setText("⏳ Reformulation...")
        
        # Ajouter le message utilisateur
        self.add_message(text, is_user=True)
        
        # Cacher les suggestions
        self.suggestions_area.hide()
        
        # Lancer la reformulation
        self.correction_worker = CorrectionWorker(
            self.correction_pipeline, text, location
        )
        self.correction_worker.finished.connect(self.on_reformulation_ready)
        self.correction_worker.error.connect(self.on_reformulation_error)
        self.correction_worker.start()
    
    def on_reformulation_ready(self, result: dict):
        """Reformulation prête"""
        
        # Réactiver les boutons
        self.btn_reformulate.setEnabled(True)
        self.btn_chatbot.setEnabled(True)
        self.btn_reformulate.setText("✨ Reformuler")
        
        # Construire la réponse
        response = f"✨ **Observation reformulée :**\n\n{result.get('observation_corrigee', 'N/A')}\n\n"
        response += f"📊 **Gravité :** {result.get('niveau_gravite', 'N/A')}\n"
        response += f"⏱️ **Délai recommandé :** {result.get('delai_recommande', 'N/A')}\n"
        
        if result.get('references_normatives'):
            response += f"\n📚 **Références normatives :**\n"
            for ref in result['references_normatives'][:3]:
                response += f"  • {ref}\n"
        
        # Ajouter la réponse
        self.add_message(response, is_user=False)
        
        # Vider le champ de saisie
        self.input_text.clear()
        self.input_location.clear()
        self.last_suggestion_text = ""
    
    def on_reformulation_error(self, error: str):
        """Erreur lors de la reformulation"""
        
        self.btn_reformulate.setEnabled(True)
        self.btn_chatbot.setEnabled(True)
        self.btn_reformulate.setText("✨ Reformuler")
        
        self.add_message(f"❌ Erreur : {error}", is_user=False)
    
    # =========================================================================
    # SUGGESTIONS
    # =========================================================================
    
    def get_suggestions(self, auto_mode: bool = False):
        """Obtenir des suggestions (manuel ou automatique)"""
        text = self.input_text.toPlainText().strip()
        
        if not text or len(text) < 3:
            if not auto_mode:
                QMessageBox.warning(
                    self, "Attention", 
                    "Veuillez saisir au moins 3 caractères pour obtenir des suggestions"
                )
            return
        
        # Désactiver les boutons en mode manuel
        if not auto_mode:
            self.btn_reformulate.setEnabled(False)
            self.btn_chatbot.setEnabled(False)
            self.btn_chatbot.setText("⏳ Chargement...")
        
        # Lancer les suggestions
        self.suggestion_worker = SuggestionWorker(self.suggestion_engine, text)
        self.suggestion_worker.finished.connect(lambda s: self.on_suggestions_ready(s, auto_mode))
        self.suggestion_worker.error.connect(lambda e: self.on_suggestions_error(e, auto_mode))
        self.suggestion_worker.start()
    
    def on_suggestions_ready(self, suggestions, auto_mode: bool = False):
        """Suggestions prêtes"""
        
        # Réactiver les boutons en mode manuel
        if not auto_mode:
            self.btn_reformulate.setEnabled(True)
            self.btn_chatbot.setEnabled(True)
            self.btn_chatbot.setText("🤖 Chatbot Ins")
        
        self.current_suggestions = suggestions
        
        # Vider les anciennes cartes
        while self.suggestions_cards.count():
            item = self.suggestions_cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # DEBUG: Afficher le contenu des suggestions
        logger.info(f"Suggestions reçues: {suggestions}")
        
        # Vérifier la structure des suggestions
        if hasattr(suggestions, 'phrases_completes') and suggestions.phrases_completes:
            suggestions_list = suggestions.phrases_completes
        elif hasattr(suggestions, 'suggestions') and suggestions.suggestions:
            suggestions_list = suggestions.suggestions
        elif isinstance(suggestions, list) and suggestions:
            suggestions_list = suggestions
        else:
            # Aucune suggestion disponible
            if not auto_mode:
                self.show_fallback_suggestions()
            else:
                self.suggestions_area.hide()
            return
        
        # Ajouter les nouvelles suggestions
        if suggestions_list:
            for idx, phrase in enumerate(suggestions_list[:3]):
                if idx == 0:
                    icon = "⭐"
                    title = "Meilleure suggestion"
                elif idx == 1:
                    icon = "✨"
                    title = "Alternative"
                else:
                    icon = "💡"
                    title = "Autre option"
                
                card = SuggestionCard(title, str(phrase), icon)
                card.clicked.connect(self.use_suggestion)
                self.suggestions_cards.addWidget(card)
            
            # Afficher la zone de suggestions
            self.suggestions_area.show()
            
            # En mode automatique, on peut ajouter un message d'info
            if auto_mode:
                self.statusBar().showMessage("💡 Suggestions automatiques générées")
        else:
            self.show_fallback_suggestions()
    
    def show_fallback_suggestions(self):
        """Afficher des suggestions par défaut si aucune n'est disponible"""
        # Suggestions par défaut basées sur des observations électriques courantes
        fallback_suggestions = [
            "Fils électriques dénudés présentant un risque de court-circuit",
            "Disjoncteur différentiel ne déclenchant pas lors du test mensuel",
            "Prises électriques sans terre dans une pièce d'eau",
            "Câbles empilés créant un échauffement anormal",
            "Gaine électrique endommagée exposant les conducteurs"
        ]
        
        for idx, phrase in enumerate(fallback_suggestions[:3]):
            if idx == 0:
                icon = "⚠️"
                title = "Suggestion type"
            elif idx == 1:
                icon = "🔧"
                title = "Exemple courant"
            else:
                icon = "💡"
                title = "Observation standard"
            
            card = SuggestionCard(title, phrase, icon)
            card.clicked.connect(self.use_suggestion)
            self.suggestions_cards.addWidget(card)
        
        self.suggestions_area.show()
        self.statusBar().showMessage("💡 Suggestions par défaut affichées")
    
    def on_suggestions_error(self, error: str, auto_mode: bool = False):
        """Erreur lors des suggestions"""
        
        # Réactiver les boutons en mode manuel
        if not auto_mode:
            self.btn_reformulate.setEnabled(True)
            self.btn_chatbot.setEnabled(True)
            self.btn_chatbot.setText("🤖 Chatbot Ins")
            
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération : {error}")
        else:
            # En mode automatique, on log juste l'erreur
            logger.warning(f"Erreur suggestions automatiques: {error}")
            # Afficher les suggestions par défaut en cas d'erreur
            self.show_fallback_suggestions()
    
    def use_suggestion(self, text: str):
        """Utiliser une suggestion"""
        self.input_text.setPlainText(text)
        self.suggestions_area.hide()
        self.statusBar().showMessage("✅ Suggestion appliquée")
    
    # =========================================================================
    # FONCTIONNALITÉS NOUVELLES
    # =========================================================================
    
    def open_chatbot(self):
        """Ouvrir l'interface du chatbot Ins"""
        # Pour l'instant, on utilise le bouton pour forcer les suggestions
        text = self.input_text.toPlainText().strip()
        if text:
            self.get_suggestions(auto_mode=False)
        else:
            QMessageBox.information(
                self, 
                "Chatbot Ins", 
                "Interface Chatbot Ins - À configurer ultérieurement\n\n"
                "Pour l'instant, ce bouton génère des suggestions manuelles."
            )
    
    def show_settings(self):
        """Afficher les paramètres"""
        QMessageBox.information(
            self,
            "Paramètres",
            "Paramètres de l'application - À configurer ultérieurement\n\n"
            "Cette interface permettra de configurer:\n"
            "• Paramètres IA\n"
            "• Préférences d'affichage\n"
            "• Options de sauvegarde\n"
            "• Configuration des rapports"
        )
    
    # =========================================================================
    # AUTRES
    # =========================================================================
    
    def new_conversation(self):
        """Nouvelle conversation"""
        # Vider les messages
        while self.messages_layout.count() > 1:  # Garder le stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Vider les champs
        self.input_text.clear()
        self.input_location.clear()
        
        # Cacher les suggestions
        self.suggestions_area.hide()
        
        # Arrêter le timer des suggestions
        self.suggestion_timer.stop()
        self.last_suggestion_text = ""
        
        self.statusBar().showMessage("✅ Nouvelle conversation démarrée")
    
    def apply_claude_theme(self):
        """Appliquer le thème style Claude"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #151515;
            }
            QWidget {
                background-color: #151515;
                color: #E8E8E8;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            }
            QScrollBar:vertical {
                background-color: #1E1E1E;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #3A3A3A;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4A4A4A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background-color: #1E1E1E;
                color: #808080;
                border-top: 1px solid #2E2E2E;
                font-size: 12px;
            }
        """)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Point d'entrée principal"""
    
    app = QApplication(sys.argv)
    app.setApplicationName("Inspection Électrique IA")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()