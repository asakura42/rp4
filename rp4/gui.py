import datetime
import sys
from typing import Optional

import markdown2
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import *

from rp4.client import ChatGPTClient, Preset, FetchError, GlobalSettings, PROGRAM_NAME


def generate_theme_style(
    bg_color,
    text_color,
    border_color,
    button_hover_color,
    button_pressed_color,
    scrollbar_handle_color,
    scrollbar_handle_hover_color,
    line_color,
):
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
        width: 4px;
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


warm_theme_style = generate_theme_style(
    "#1F2937",
    "#F1FAEE",
    "#E07A5F",
    "#E07A5F",
    "#D62828",
    "#E07A5F",
    "#D62828",
    "#E07A5F",
)
dark_monokai_theme_style = generate_theme_style(
    "#272822",
    "#F8F8F2",
    "#F8F8F2",
    "#75715E",
    "#49483E",
    "#75715E",
    "#49483E",
    "#F8F8F2",
)
gruvbox_theme_style = generate_theme_style(
    "#282828",
    "#EBDBB2",
    "#EBDBB2",
    "#504945",
    "#665C54",
    "#504945",
    "#665C54",
    "#EBDBB2",
)
light_theme_style = generate_theme_style(
    "#FFFFFF",
    "#000000",
    "#000000",
    "#C0C0C0",
    "#808080",
    "#888",
    "#555",
    "#000000",
)
dark_theme_style = generate_theme_style(
    "#2b2b2b",
    "#a9b7c6",
    "#214283",
    "#4e5b6e",
    "#214283",
    "#888",
    "#555",
    "#214283",
)


class Worker(QThread):
    finished = pyqtSignal(str)  # todo pass struct with fields (msg, role)

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


class UserMsgForm(QTextEdit):
    sendPressed = pyqtSignal()

    def keyPressEvent(self, event: Optional[QKeyEvent]):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.sendPressed.emit()
        else:
            super().keyPressEvent(event)


def highlight_quoted_text(message, color):
    quote = '"'
    quote_pairs = message.split(quote)
    for i in range(1, len(quote_pairs), 2):
        quote_pairs[i] = f'<span style="color: {color};">{quote_pairs[i]}</span>'
    return quote.join(quote_pairs)


def wrap_code_blocks(message):
    code_block = "```"
    block_pairs = message.split(code_block)
    for i in range(1, len(block_pairs), 2):
        block_pairs[i] = f"<pre>{block_pairs[i]}</pre>"
    return code_block.join(block_pairs)


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

    def update_api_type(self, api_type):
        self.chatgpt_client.globals.api_type = self.api_dropdown.currentText()
        self.populate_model_dropdown(self.model_dropdown.currentText())

    def init_ui(self):
        chat_layout = QVBoxLayout()
        self.messages_text = QTextEdit(self)
        self.messages_text.setObjectName("messages_text")
        self.messages_text.setReadOnly(True)
        chat_layout.addWidget(self.messages_text)

        self.user_message = UserMsgForm(self)
        # self.user_message.enterEvent.connect(self.send_message)
        self.user_message.setAcceptRichText(False)
        self.user_message.setMinimumHeight(100)
        self.user_message.setMaximumHeight(200)
        self.user_message.sendPressed.connect(self.send_message)
        chat_layout.addWidget(self.user_message)

        self.font_size = 16

        self.increase_font_button = QPushButton("+", self)
        self.increase_font_button.setFixedSize(32, 32)
        self.increase_font_button.clicked.connect(self.increase_font_size)

        self.decrease_font_button = QPushButton("-", self)
        self.decrease_font_button.setFixedSize(32, 32)
        self.decrease_font_button.clicked.connect(self.decrease_font_size)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.clear_history_button = QPushButton("Clear history")
        self.clear_history_button.clicked.connect(self.clear_history)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.decrease_font_button)
        button_layout.addWidget(self.increase_font_button)
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_history_button)

        chat_layout.addLayout(button_layout)

        settings_layout = QVBoxLayout()

        self.api_dropdown = QComboBox(self)
        self.api_dropdown.addItem("gpt4free")
        self.api_dropdown.addItem("URL_JSON_API")
        self.api_dropdown.currentTextChanged.connect(self.update_api_type)
        settings_layout.addWidget(QLabel("Select API:"))
        settings_layout.addWidget(self.api_dropdown)

        self.base_url_field = QLineEdit(self)
        self.base_url_field.setText(self.chatgpt_client.globals.base_url)
        self.base_url_field.editingFinished.connect(self.update_base_url)
        settings_layout.addWidget(
            ql := QLabel('Base URL (<a href="https://rentry.org/desudeliveryservice">find URLs</a>):')
        )
        ql.setOpenExternalLinks(True)
        settings_layout.addWidget(self.base_url_field)

        self.api_key_field = QLineEdit(self)
        self.api_key_field.setText(self.chatgpt_client.globals.api_key)
        settings_layout.addWidget(QLabel("API Key:"))
        settings_layout.addWidget(self.api_key_field)

        self.theme_dropdown = QComboBox(self)
        self.theme_dropdown.addItem("Dark")
        self.theme_dropdown.addItem("Warm")
        self.theme_dropdown.addItem("Light")
        self.theme_dropdown.addItem("Monokai")
        self.theme_dropdown.addItem("Gruvbox")
        self.theme_dropdown.currentTextChanged.connect(self.switch_theme)
        settings_layout.addWidget(QLabel("Select Theme:"))
        settings_layout.addWidget(self.theme_dropdown)
        self.theme_dropdown.setCurrentText(self.chatgpt_client.globals.theme)

        # model dropdown (gpt-4, etc.)
        self.model_dropdown = QComboBox(self)
        settings_layout.addWidget(QLabel("Select Model:"))
        settings_layout.addWidget(self.model_dropdown)
        self.populate_model_dropdown(self.chatgpt_client.globals.selected_model)

        self.format_md_checkbox = QCheckBox("Markdown as HTML")
        self.format_md_checkbox.setChecked(self.chatgpt_client.globals.md2html)
        settings_layout.addWidget(self.format_md_checkbox)

        # HR
        hline = QFrame(self)
        hline.setObjectName("line")
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        hline.setMinimumSize(50, 4)
        settings_layout.addWidget(hline)

        # Preset selector
        hbox = QHBoxLayout()
        self.preset_dropdown = QComboBox(self)
        hbox.addWidget(QLabel("Select Preset:"))
        hbox.addWidget(self.preset_dropdown)
        self.preset_dropdown.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        settings_layout.addLayout(hbox)

        # System prompts
        settings_layout.addWidget(QLabel("#1 System Prompt:"))
        self.system_prompt1 = QTextEdit(self)
        settings_layout.addWidget(self.system_prompt1)

        settings_layout.addWidget(QLabel("#2 NSFW Prompt:"))
        self.system_prompt2 = QTextEdit(self)
        settings_layout.addWidget(self.system_prompt2)

        settings_layout.addWidget(QLabel("#3 JailBreak prompt:"))
        self.system_prompt3 = QTextEdit(self)
        settings_layout.addWidget(self.system_prompt3)

        settings_layout.addWidget(QLabel("Character Description:"))
        self.character_description = QTextEdit(self)
        settings_layout.addWidget(self.character_description)

        settings_layout.addWidget(QLabel("First AI Message:"))
        self.first_ai_message = QTextEdit(self)
        settings_layout.addWidget(self.first_ai_message)

        settings_layout.addWidget(QLabel("Example Chat:"))
        self.example_chat = QTextEdit(self)
        settings_layout.addWidget(self.example_chat)

        settings_layout.addWidget(QLabel("World Lore:"))
        self.world_lore = QTextEdit(self)
        settings_layout.addWidget(self.world_lore)

        # Add a new preset
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(32, 32)
        hbox.addWidget(self.add_btn)
        self.add_btn.pressed.connect(self.add_preset)

        # save settings.
        self.save_settings_button = QPushButton("Save settings", self)
        self.save_settings_button.clicked.connect(self.save_settings_to_disk)
        settings_layout.addWidget(self.save_settings_button)

        # Chat history + input box
        chat_area = QWidget()
        chat_area.setLayout(chat_layout)

        # Chat settings
        setting_widget = QWidget()
        setting_widget.setLayout(settings_layout)
        settings_area = QScrollArea()
        settings_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        settings_area.setWidgetResizable(True)
        settings_area.setWidget(setting_widget)

        # Splitter
        splitter = QSplitter()
        # Left tab
        splitter.addWidget(chat_area)
        # Right tab
        splitter.addWidget(settings_area)
        splitter.setSizes([300, 100])

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.setMinimumSize(600, 400)

        self.api_dropdown.setCurrentText(self.chatgpt_client.globals.api_type)

        #  Populate presets (and system prompt fields)
        self.populate_preset_names()
        self.preset_dropdown.currentTextChanged.connect(self.apply_preset)

        # Focus message box
        self.user_message.setFocus()

    def populate_preset_names(self):
        self.preset_dropdown.clear()
        self.preset_dropdown.addItems(self.chatgpt_client.presets)
        self.preset_dropdown.setCurrentText(self.chatgpt_client.globals.selected_preset)
        self.apply_preset(self.chatgpt_client.globals.selected_preset)

    def increase_font_size(self):
        self.font_size += 1
        self.messages_text.setStyleSheet(f"font-size: {self.font_size}px")

    def decrease_font_size(self):
        if self.font_size > 1:
            self.font_size -= 1
            self.messages_text.setStyleSheet(f"font-size: {self.font_size}px")

    def update_base_url(self):
        if self.base_url_field.text() and self.base_url_field.text() != self.chatgpt_client.globals.base_url:
            self.chatgpt_client.globals.base_url = self.base_url_field.text()
            self.populate_model_dropdown(self.model_dropdown.currentText(), new_base_url=True)

    def _current_settings_from_gui(self):
        """
        dump current settings from the GUI layout.
        """
        return GlobalSettings(
            api_type=self.api_dropdown.currentText(),
            api_key=self.api_key_field.text(),
            base_url=self.base_url_field.text(),
            selected_model=self.model_dropdown.currentText(),
            theme=self.theme_dropdown.currentText(),
            model_names=[self.model_dropdown.itemText(item) for item in range(self.model_dropdown.count())],
            selected_preset=self.preset_dropdown.currentText(),
            verbose=False,
            md2html=self.format_md_checkbox.isChecked(),
        )

    def sync_settings_with_backend(self):
        # global settings
        self.chatgpt_client.globals = self._current_settings_from_gui()
        # presets
        if current_preset_name := self.preset_dropdown.currentText():
            self.chatgpt_client.presets[current_preset_name] = self._get_current_preset_from_gui()

    def save_settings_to_disk(self):
        self.sync_settings_with_backend()
        self.chatgpt_client.save_global_settings_to_disk()
        self.chatgpt_client.save_presets_to_disk()

    def format_message(self, message: str, role: str):
        html_role = f"START{role}:"
        message = f"{html_role} {message}"
        if self.chatgpt_client.globals.md2html:
            message = str(markdown2.markdown(message, safe_mode=False))
        else:
            message = message.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        message = message.replace("&quot;", '"')

        message = highlight_quoted_text(message, color="gray")
        message = wrap_code_blocks(message)

        message = message.replace(
            html_role,
            f'<div style="font-size: 20px; border-bottom: 1px solid gray;"><b>{datetime.datetime.now().strftime("%H:%M")}</b>: {role}</div>',
            1,
        )
        return message

    def clear_history(self):
        self.messages_text.clear()
        self.chatgpt_client.chat_history.clear()

    def apply_preset(self, preset_name: str):
        if preset_name in self.chatgpt_client.presets:
            if self.chatgpt_client.chat_history:
                reply = QMessageBox.question(
                    self,
                    "New Conversation",
                    "Changing the preset will start a new conversation. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.clear_history()
                else:
                    return
            else:
                self.clear_history()

            preset = self.chatgpt_client.presets[preset_name]
            self.system_prompt1.setText(preset.system_prompt1)
            self.system_prompt2.setText(preset.system_prompt2)
            self.system_prompt3.setText(preset.system_prompt3)
            self.character_description.setPlainText(preset.character_description)
            self.first_ai_message.setText(preset.first_ai_message)
            self.example_chat.setPlainText(preset.example_chat)
            self.world_lore.setPlainText(preset.world_lore)

            if preset.first_ai_message:
                self.messages_text.append(self.format_message(preset.first_ai_message, preset_name))
                self.user_message.setDisabled(True)
                self.user_message.clear()
                self.user_message.setDisabled(False)
                self.user_message.setFocus()

    def _get_current_preset_from_gui(self) -> Preset:
        return Preset(
            system_prompt1=self.system_prompt1.toPlainText(),
            system_prompt2=self.system_prompt2.toPlainText(),
            system_prompt3=self.system_prompt3.toPlainText(),
            character_description=self.character_description.toPlainText(),
            first_ai_message=self.first_ai_message.toPlainText(),
            example_chat=self.example_chat.toPlainText(),
            world_lore=self.world_lore.toPlainText(),
        )

    def add_preset(self):
        new_preset_name, ok = QInputDialog.getText(self, "Add Preset", "Enter preset name:")
        if ok and new_preset_name:
            self.chatgpt_client.presets[new_preset_name] = self._get_current_preset_from_gui()
            self.preset_dropdown.addItem(new_preset_name)
            self.preset_dropdown.setCurrentText(new_preset_name)

    def populate_model_dropdown(self, selected_model: str, new_base_url: bool = False):
        print("populating models")
        self.model_dropdown.clear()
        if self.chatgpt_client.globals.api_type == "gpt4free":
            self.chatgpt_client.globals.model_names = [
                "gpt-3.5-turbo-16k",
                "gpt-4-turbo",
            ]
            self.model_dropdown.addItems(self.chatgpt_client.globals.model_names)
        elif self.chatgpt_client.globals.api_type == "URL_JSON_API":
            try:
                if not self.chatgpt_client.globals.model_names or new_base_url is True:
                    self.chatgpt_client.globals.model_names = self.chatgpt_client.fetch_model_names()
                self.model_dropdown.addItems(self.chatgpt_client.globals.model_names)
            except FetchError as ex:
                print(ex)
        self.model_dropdown.setCurrentText(selected_model)

    def send_message(self):
        user_message = self.user_message.toPlainText()

        self.sync_settings_with_backend()

        self.update_ui(user_message, is_user=True)

        if self.worker and self.worker.isRunning():
            self.worker.wait()

        self.worker = Worker(self.chatgpt_client, user_message, self.preset_dropdown.currentText())
        self.worker.finished.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, message: str, is_user: bool = False):
        role = "User" if is_user else self.preset_dropdown.currentText()
        self.messages_text.append(self.format_message(message, role))
        if is_user:
            self.user_message.clear()
            self.user_message.setDisabled(True)
            self.send_button.setDisabled(True)
        else:
            self.user_message.clear()
            self.user_message.setDisabled(False)
            self.send_button.setDisabled(False)
            self.user_message.setFocus()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()


def show_window(chatgpt_client: ChatGPTClient | None = None):
    app = QApplication(sys.argv)
    app.setStyleSheet(warm_theme_style)  # DEFAULT THEME
    chat_gui = ChatGUI(chatgpt_client or ChatGPTClient(), app)
    chat_gui.setWindowTitle(PROGRAM_NAME)
    chat_gui.setGeometry(100, 100, 400, 600)
    chat_gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    show_window()
