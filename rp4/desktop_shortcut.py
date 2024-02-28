import pathlib

from rp4.client import PROGRAM_NAME

LAUNCH_INFO = f"""\
[Desktop Entry]
Type=Application
Terminal=false
Name={PROGRAM_NAME}
GenericName=ChatGPT
Comment=Simple python replacement for the bloated LLM frontends
TryExec={PROGRAM_NAME}
Exec={PROGRAM_NAME} --gui
Icon=irc-chat
Categories=Network;InstantMessaging;Chat;
Keywords=chat;im;messaging;messenger;sms;
StartupWMClass={PROGRAM_NAME}
"""


def setup_shortcut():
    desktop_file = pathlib.Path.home() / f".local/share/applications/{PROGRAM_NAME}.desktop"
    if desktop_file.parent.parent.is_dir() and desktop_file.is_file() is False:
        desktop_file.parent.mkdir(exist_ok=True, parents=True)
        desktop_file.write_text(LAUNCH_INFO)
