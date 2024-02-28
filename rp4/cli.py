import argparse

from rp4.gui import show_window
from rp4.client import ChatGPTClient


def main():
    parser = argparse.ArgumentParser(description="CLI interface.", usage="Send messages to the server.")
    parser.add_argument("--fetch-models", dest="fetch_models", action="store_true", help="Fetch models")
    parser.add_argument("--list-presets", dest="print_presets", action="store_true", help="List presets.")
    parser.add_argument("--list-models", dest="print_models", action="store_true", help="List models.")
    parser.add_argument("-v", "--verbose", dest="be_verbose", action="store_true", help="Output some debug info.")
    parser.add_argument("--gui", dest="launch_gui", action="store_true", help="Launch GUI.")
    parser.add_argument("--ask", dest="ask_question", type=str, help="Ask model a question.")
    parser.add_argument("--preset", dest="set_preset", type=str, help="Pass a preset name.")
    parser.add_argument("--model", dest="model_name", type=str, help="Pass a model name.")
    args = parser.parse_args()

    client = ChatGPTClient()
    client.globals.verbose = bool(args.be_verbose)
    match args:
        case argparse.Namespace(fetch_models=True):
            return print(client.fetch_model_names())
        case argparse.Namespace(print_models=True):
            return print("\n".join(client.globals.model_names))
        case argparse.Namespace(print_presets=True):
            return print("\n".join(client.presets))
        case argparse.Namespace() if args.ask_question:
            return print(
                client.send_message(
                    args.ask_question, (args.set_preset or client.globals.selected_preset), args.model_name
                )
            )
        case argparse.Namespace(launch_gui=True):
            return show_window(client)
        case _:
            return parser.print_help()


if __name__ == "__main__":
    main()
