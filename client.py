import dataclasses
import json
import typing
from pprint import pprint

import g4f
import requests

GLOBAL_SETTINGS_FILE_PATH = 'global_settings.json'
PRESETS_SETTINGS_FILE_PATH = 'settings.json'


@dataclasses.dataclass
class GlobalSettings:
    api_type: str = "URL_JSON_API"
    api_key: str = "desu"
    base_url: str = "https://juan-finite-suddenly-volume.trycloudflare.com/proxy/azure/openai/v1"
    model: str = "gpt-4"  # todo deprecate
    theme: str = "Light"
    verbose: bool = False
    model_names: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Preset:
    system_prompt1: str = ""
    system_prompt2: str = ""
    system_prompt3: str = ""
    character_description: str = ""
    first_ai_message: str = ""
    example_chat: str = ""
    world_lore: str = ""
    model: str = "gpt-4"


class ChatHistoryEntry(typing.TypedDict):
    role: str
    content: str


class FetchError(requests.RequestException):
    pass


class ChatGPTClient:
    def __init__(self,
                 globals_file_path: str = GLOBAL_SETTINGS_FILE_PATH,
                 presets_file_path: str = PRESETS_SETTINGS_FILE_PATH,
                 **kwargs):
        # global settings
        self.globals_file_path = globals_file_path
        self.globals = GlobalSettings()
        self.set_kwargs(kwargs)
        self.load_global_settings(globals_file_path)
        # presets
        self.presets_file_path = presets_file_path
        self.presets = {"Assistant": Preset()}
        self.load_presets(presets_file_path)
        # history
        self.chat_history: list[ChatHistoryEntry] = []

    def save_global_settings(self):
        with open(self.globals_file_path, 'w', encoding="utf-8") as of:
            json.dump(dataclasses.asdict(self.globals), of, indent=4, ensure_ascii=False)

    def load_global_settings(self, file_path):
        try:
            with open(file_path, 'r') as f:
                self.globals = dataclasses.replace(
                    self.globals,
                    **json.load(f)
                )
        except FileNotFoundError:
            print("Global settings file is not found.")

    def load_presets(self, settings_file: str):
        try:
            with open(settings_file, 'r') as f:
                self.presets = {
                    preset_name: Preset(**data)
                    for preset_name, data in json.load(f).items()
                }
        except FileNotFoundError:
            print("Presets settings file is not found.")

    def construct_initial_chat_history(self, preset_name: str):
        preset = self.presets.get(preset_name, Preset())
        if preset.model:
            # todo remove
            self.globals.model = preset.model

        if preset.system_prompt1:
            self.chat_history.append({"role": "system", "content": preset.system_prompt1})
        if preset.system_prompt2:
            self.chat_history.append({"role": "system", "content": preset.system_prompt2})
        if preset.character_description:
            self.chat_history.append(
                {"role": "system", "content": "AI CHARACTER DESCRIPTION:\\n" + preset.character_description})
        if preset.example_chat:
            self.chat_history.append(
                {"role": "system", "content": "EXAMPLE CHAT WITH THIS CHARACTER:\\n" + preset.example_chat})
        if preset.world_lore:
            self.chat_history.append({"role": "system", "content": "WORLD LORE:\\n" + preset.world_lore})
        if preset.first_ai_message:
            self.chat_history.append({"role": "assistant", "content": preset.first_ai_message})

    def send_message(self, user_message: str, preset_name: str) -> str:
        response = None
        assistant_response = "Empty response!"

        if not self.chat_history:
            self.construct_initial_chat_history(preset_name)

        self.chat_history.append({"role": "user", "content": user_message})

        preset = self.presets.get(preset_name, Preset())
        if preset.system_prompt3:
            self.chat_history.append({"role": "system", "content": preset.system_prompt3})

        if self.globals.api_type == "gpt4free":
            response = g4f.ChatCompletion.create(
                model=self.globals.model,
                messages=self.chat_history,
            )
            assistant_response = response
        elif self.globals.api_type == "URL_JSON_API":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.globals.api_key}"
            }
            data = {
                "model": self.globals.model,
                "messages": self.chat_history,
                "max_tokens": 1000,
                "frequency_penalty": 0.7,
                "temperature": 0.9,
                "presence_penalty": 0.7,
                "top_p": 1,
                "stream": True
            }
            response = requests.post(self.globals.base_url + "/chat/completions", json=data, headers=headers,
                                     stream=True)
            response.raise_for_status()

            assistant_response = ''
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line == 'data: [DONE]':
                        break
                    elif decoded_line.startswith('data:'):
                        json_line = json.loads(decoded_line[5:].strip())
                        content = json_line.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        assistant_response += content

        if response:
            try:
                self.chat_history.append({"role": "assistant", "content": assistant_response})
            except (IndexError, KeyError):
                assistant_response = "The response does not contain a valid assistant message."
        else:
            assistant_response = "No response received."

        return assistant_response

    def set_kwargs(self, kwargs):
        self.globals = dataclasses.replace(
            self.globals,
            **{key: val for key, val in kwargs.items() if (key and val)}
        )

    def save_presets_to_disk(self):
        payload = {
            preset_name: dataclasses.asdict(preset_data)
            for preset_name, preset_data
            in self.presets.items()
        }
        with open(self.presets_file_path, 'w') as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    def fetch_model_names(self) -> list[str]:
        url = self.globals.base_url + "/models"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.globals.api_key}"
        }
        try:
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            json_data = response.json()
            if self.globals.verbose:
                pprint(json_data, indent=2)
        except Exception as ex:
            if self.globals.verbose:
                print(ex)
            raise FetchError("Couldn't get model names") from ex
        else:
            return [model['id'] for model in json_data.get('data', [])]
