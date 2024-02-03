import re
import sys

import markdown2
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import *

from client import ChatGPTClient, Preset


def generate_theme_style(bg_color, text_color, border_color, button_hover_color, button_pressed_color,
                         scrollbar_handle_color, scrollbar_handle_hover_color, line_color):
    return f"""
    QWidget {{
        background-color: {bg_color};
        color: {text_color};
        font-family: "Monospace";
        font-size: 10pt;
    }}

    QFrame#line {{
        background-color: {line_color};
    }}

    QTextEdit {{
        background-color: {bg_color};
        color: {text_color};
        border-bottom: 2px dotted {border_color};
    }}

    #messages_text {{
        background-color: {bg_color};
        color: {text_color};
        font-family: "Sans";
        font-size: 15px;
        border: 1px dotted {border_color};
    }}

    QLineEdit {{
        background-color: {bg_color};
        color: {text_color};
        border-bottom: 1px dotted {border_color};
    }}

    QPushButton {{
        background-color: {bg_color};
        color: {text_color};
        border-bottom: 1px dotted {border_color};
        padding: 5px;
    }}

    QPushButton:hover {{
        background-color: {button_hover_color};
    }}

    QPushButton:pressed {{
        background-color: {button_pressed_color};
    }}

    QComboBox {{
        background-color: {bg_color};
        color: {text_color};
        border-bottom: 1px dotted {border_color};
    }}

    QComboBox:hover {{
        background-color: {button_hover_color};
    }}

    QComboBox QAbstractItemView {{
        background-color: {bg_color};
        color: {text_color};
        selection-background-color: {button_pressed_color};
    }}

    QLabel {{
        color: {text_color};
    }}

    QScrollBar:vertical {{
        border: none;
        background: {bg_color};
        width: 2px;
        margin: 15px 0 15px 0;
        border-radius: 0px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {scrollbar_handle_color};
        min-height: 50px;
        border-radius: 1px;
    }}

    QScrollBar::handle:vertical:hover{{
        background-color: {scrollbar_handle_hover_color};
    }}

    QScrollBar::add-line:vertical {{
        border: none;
        background: none;
    }}

    QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}
    """


warm_theme_style = generate_theme_style("#1F2937", "#F1FAEE", "#E07A5F", "#E07A5F", "#D62828", "#E07A5F", "#D62828",
                                        "#E07A5F")
dark_monokai_theme_style = generate_theme_style("#272822", "#F8F8F2", "#F8F8F2", "#75715E", "#49483E", "#75715E",
                                                "#49483E", "#F8F8F2")
gruvbox_theme_style = generate_theme_style("#282828", "#EBDBB2", "#EBDBB2", "#504945", "#665C54", "#504945", "#665C54",
                                           "#EBDBB2")
light_theme_style = generate_theme_style("#FFFFFF", "#000000", "#000000", "#C0C0C0", "#808080", "#888", "#555",
                                         "#000000")
dark_theme_style = generate_theme_style("#2b2b2b", "#a9b7c6", "#214283", "#4e5b6e", "#214283", "#888", "#555",
                                        "#214283")


class Worker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, chatgpt_client: ChatGPTClient, user_message: str, preset_name: str):
        super().__init__()
        self.chatgpt_client = chatgpt_client
        self.user_message = user_message
        self.preset_name = preset_name

    def run(self):
        try:
            assistant_response = self.chatgpt_client.send_message(self.user_message, self.preset_name)
            self.finished.emit(assistant_response)
        except Exception as e:
            self.finished.emit(f"An error occurred: {e}")


class EnterLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(event)


class ChatGUI(QWidget):
    def __init__(self, chatgpt_client: ChatGPTClient, app: QApplication):
        super().__init__()
        self.chatgpt_client = chatgpt_client
        self.app = app
        self.worker = None
        self.init_ui()

    def switch_theme(self, theme):
        if theme == "Dark":
            self.app.setStyleSheet(dark_theme_style)
        elif theme == "Warm":
            self.app.setStyleSheet(warm_theme_style)
        elif theme == "Light":
            self.app.setStyleSheet(light_theme_style)
        elif theme == "Monokai":
            self.app.setStyleSheet(dark_monokai_theme_style)
        elif theme == "Gruvbox":
            self.app.setStyleSheet(gruvbox_theme_style)
        self.chatgpt_client.globals.theme = theme
        self.chatgpt_client.save_global_settings()

    def update_api_type(self, api_type):
        self.chatgpt_client.globals.api_type = api_type
        self.populate_model_dropdown()
        self.chatgpt_client.save_global_settings()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        chat_layout = QVBoxLayout()
        self.messages_text = QTextEdit(self)
        self.messages_text.setObjectName("messages_text")
        self.messages_text.setReadOnly(True)
        chat_layout.addWidget(self.messages_text)

        self.input_entry = EnterLineEdit(self)
        self.input_entry.returnPressed.connect(self.send_message)
        chat_layout.addWidget(self.input_entry)

        self.font_size = 15

        self.increase_font_button = QPushButton("+", self)
        self.increase_font_button.setFixedSize(32, 32)
        self.increase_font_button.clicked.connect(self.increase_font_size)

        self.decrease_font_button = QPushButton("-", self)
        self.decrease_font_button.setFixedSize(32, 32)
        self.decrease_font_button.clicked.connect(self.decrease_font_size)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.decrease_font_button)
        button_layout.addWidget(self.increase_font_button)
        button_layout.addWidget(self.send_button)

        chat_layout.addLayout(button_layout)

        main_layout.addLayout(chat_layout, 3)

        roleplay_layout = QVBoxLayout()

        self.api_dropdown = QComboBox(self)
        self.api_dropdown.addItem("gpt4free")
        self.api_dropdown.addItem("URL_JSON_API")
        self.api_dropdown.currentTextChanged.connect(self.update_api_type)
        roleplay_layout.addWidget(QLabel("Select API:"))
        roleplay_layout.addWidget(self.api_dropdown)

        self.base_url_field = QLineEdit(self)
        self.base_url_field.setText(self.chatgpt_client.globals.base_url)
        self.base_url_field.textChanged.connect(self.update_base_url)
        roleplay_layout.addWidget(QLabel("Base URL (should end with 'v1'):"))
        roleplay_layout.addWidget(self.base_url_field)

        self.api_key_field = QLineEdit(self)
        self.api_key_field.setText(self.chatgpt_client.globals.api_key)
        self.api_key_field.textChanged.connect(self.update_api_key)
        roleplay_layout.addWidget(QLabel("API Key:"))
        roleplay_layout.addWidget(self.api_key_field)

        self.model_dropdown = QComboBox(self)
        self.populate_model_dropdown()
        roleplay_layout.addWidget(QLabel("Select Model:"))
        roleplay_layout.addWidget(self.model_dropdown)
        self.model_dropdown.currentTextChanged.connect(self.update_model)

        self.theme_dropdown = QComboBox(self)
        self.theme_dropdown.addItem("Dark")
        self.theme_dropdown.addItem("Warm")
        self.theme_dropdown.addItem("Light")
        self.theme_dropdown.addItem("Monokai")
        self.theme_dropdown.addItem("Gruvbox")
        self.theme_dropdown.currentTextChanged.connect(self.switch_theme)
        roleplay_layout.addWidget(QLabel("Select Theme:"))
        roleplay_layout.addWidget(self.theme_dropdown)

        hline = QFrame(self)
        hline.setObjectName("line")
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        roleplay_layout.addWidget(hline)

        roleplay_layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt1 = QTextEdit(self)
        roleplay_layout.addWidget(self.system_prompt1)

        roleplay_layout.addWidget(QLabel("NSFW Prompt:"))
        self.system_prompt2 = QTextEdit(self)
        roleplay_layout.addWidget(self.system_prompt2)

        roleplay_layout.addWidget(QLabel("JailBreak prompt:"))
        self.system_prompt3 = QTextEdit(self)
        roleplay_layout.addWidget(self.system_prompt3)

        roleplay_layout.addWidget(QLabel("Character Description:"))
        self.character_description = QTextEdit(self)
        roleplay_layout.addWidget(self.character_description)

        roleplay_layout.addWidget(QLabel("First AI Message:"))
        self.first_ai_message = QTextEdit(self)
        roleplay_layout.addWidget(self.first_ai_message)

        roleplay_layout.addWidget(QLabel("Example Chat:"))
        self.example_chat = QTextEdit(self)
        roleplay_layout.addWidget(self.example_chat)

        roleplay_layout.addWidget(QLabel("World Lore:"))
        self.world_lore = QTextEdit(self)
        roleplay_layout.addWidget(self.world_lore)

        ## preset selector
        hbox = QHBoxLayout()
        roleplay_layout.addLayout(hbox)
        self.preset_dropdown = QComboBox(self)
        self.preset_dropdown.currentIndexChanged.connect(self.apply_preset)
        self.preset_dropdown.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        hbox.addWidget(QLabel("Select Preset:"))
        hbox.addWidget(self.preset_dropdown)
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(32, 32)
        hbox.addWidget(self.add_btn)
        self.add_btn.pressed.connect(self.add_preset)

        self.save_preset_button = QPushButton("Save Preset", self)
        self.save_preset_button.clicked.connect(self.save_preset)
        roleplay_layout.addWidget(self.save_preset_button)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        roleplay_widget = QWidget()
        roleplay_widget.setLayout(roleplay_layout)

        scroll_area.setWidget(roleplay_widget)

        main_layout.addWidget(scroll_area, 1)

        self.setLayout(main_layout)

        self.api_dropdown.setCurrentText(self.chatgpt_client.globals.api_type)
        self.theme_dropdown.setCurrentText(self.chatgpt_client.globals.theme)
        self.populate_preset_names()

    def increase_font_size(self):
        self.font_size += 1
        self.messages_text.setStyleSheet(f"font-size: {self.font_size}px")

    def decrease_font_size(self):
        if self.font_size > 1:
            self.font_size -= 1
            self.messages_text.setStyleSheet(f"font-size: {self.font_size}px")

    def update_base_url(self, base_url):
        self.chatgpt_client.globals.base_url = base_url
        self.chatgpt_client.save_global_settings()

    def update_model(self, model):
        self.chatgpt_client.globals.model = model
        self.chatgpt_client.save_global_settings()

    def update_api_key(self, api_key):
        self.chatgpt_client.globals.api_key = api_key
        self.chatgpt_client.save_global_settings()

    # def update_api_type(self, api_type):
    # self.chatgpt_client.api_type = api_type

    def populate_preset_names(self):
        self.preset_dropdown.clear()
        self.preset_dropdown.addItems(self.chatgpt_client.presets)

    def format_message(self, message, is_user=False):
        role = "User" if is_user else self.preset_dropdown.currentText()
        formatted_message = f"START{role}: {message}"

        formatted_message = markdown2.markdown(formatted_message, safe_mode=False)

        formatted_message = formatted_message.replace('&quot;', '"')

        quote_pairs = formatted_message.split('"')
        for i in range(1, len(quote_pairs), 2):
            quote_pairs[i] = f'<span style="color: gray;">{quote_pairs[i]}</span>'
        formatted_message = '"'.join(quote_pairs)

        html_role = f"START{role}"
        formatted_message = re.sub(html_role, f'<b>{role}</b>', formatted_message, count=1)

        return formatted_message

    def apply_preset(self):
        preset_name = self.preset_dropdown.currentText()
        if preset_name in self.chatgpt_client.presets:
            if self.chatgpt_client.chat_history:
                reply = QMessageBox.question(self, 'New Conversation',
                                             'Changing the preset will start a new conversation. Continue?',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.messages_text.clear()
                    self.chatgpt_client.chat_history.clear()
                else:
                    return
            else:
                self.messages_text.clear()

            preset = self.chatgpt_client.presets[preset_name]
            if preset.model:
                self.chatgpt_client.globals.model = preset.model  # todo remove
            self.system_prompt1.setText(preset.system_prompt1)
            self.system_prompt2.setText(preset.system_prompt2)
            self.system_prompt3.setText(preset.system_prompt3)
            self.character_description.setPlainText(preset.character_description)
            self.first_ai_message.setText(preset.first_ai_message)
            self.example_chat.setPlainText(preset.example_chat)
            self.world_lore.setPlainText(preset.world_lore)

            self.model_dropdown.setCurrentText(self.chatgpt_client.globals.model)

            if preset.first_ai_message:
                self.messages_text.append(self.format_message(preset.first_ai_message))
                self.input_entry.setDisabled(True)
                self.input_entry.clear()
                self.input_entry.setDisabled(False)
                self.input_entry.setFocus()

    def _get_current_preset_from_gui(self) -> Preset:
        return Preset(
            system_prompt1=self.system_prompt1.toPlainText(),
            system_prompt2=self.system_prompt2.toPlainText(),
            system_prompt3=self.system_prompt3.toPlainText(),
            character_description=self.character_description.toPlainText(),
            first_ai_message=self.first_ai_message.toPlainText(),
            example_chat=self.example_chat.toPlainText(),
            world_lore=self.world_lore.toPlainText(),
            model=self.model_dropdown.currentText(),
        )

    def save_preset(self):
        current_preset_name = self.preset_dropdown.currentText()
        if current_preset_name:
            self.chatgpt_client.presets[current_preset_name] = self._get_current_preset_from_gui()
            self.chatgpt_client.save_presets_to_disk()

    def add_preset(self):
        new_preset_name, ok = QInputDialog.getText(self, 'Add Preset', 'Enter preset name:')
        if ok and new_preset_name:
            self.chatgpt_client.presets[new_preset_name] = self._get_current_preset_from_gui()
            self.preset_dropdown.addItem(new_preset_name)
            self.preset_dropdown.setCurrentText(new_preset_name)
            self.chatgpt_client.save_presets_to_disk()

    def fetch_and_populate_models(self):
        self.model_dropdown.clear()
        self.model_dropdown.addItems(self.chatgpt_client.fetch_model_names())

    def populate_model_dropdown(self):
        self.model_dropdown.clear()

        if self.chatgpt_client.globals.api_type == "gpt4free":
            models = [
                'gpt-3.5-turbo-16k',
                'gpt-4-turbo',
            ]
            for model in models:
                self.model_dropdown.addItem(model)
        elif self.chatgpt_client.globals.api_type == "URL_JSON_API":
            self.fetch_and_populate_models()
        self.model_dropdown.setCurrentText(self.chatgpt_client.globals.model)

    def send_message(self):
        user_message = self.input_entry.text()
        self.chatgpt_client.globals.api_type = self.api_dropdown.currentText()
        self.chatgpt_client.presets[self.preset_dropdown.currentText()] = self._get_current_preset_from_gui()
        self.update_ui(user_message, is_user=True)
        self.input_entry.setDisabled(True)

        if self.worker and self.worker.isRunning():
            self.worker.wait()

        self.worker = Worker(self.chatgpt_client, user_message, self.preset_dropdown.currentText())
        self.worker.finished.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, message, is_user=False):
        role = "User" if is_user else self.preset_dropdown.currentText()
        formatted_message = self.format_message(message, is_user)
        self.messages_text.append(formatted_message)

        if not is_user:
            self.input_entry.clear()
            self.input_entry.setDisabled(False)
            self.input_entry.setFocus()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


def main():
    chatgpt_client = ChatGPTClient()
    app = QApplication(sys.argv)
    app.setStyleSheet(warm_theme_style)  # DEFAULT THEME
    chat_gui = ChatGUI(chatgpt_client, app)
    chat_gui.setWindowTitle("4rp")
    chat_gui.setGeometry(100, 100, 400, 600)
    chat_gui.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
