import argparse
from client import ChatGPTClient
import gui

def main():
    parser = argparse.ArgumentParser(description='CLI interface.', usage="Send messages to the server.")
    parser.add_argument('--fetch-models', dest='fetch_models', action='store_true', help='Fetch models')
    parser.add_argument('--list-presets', dest='print_presets', action='store_true', help='List presets.')
    parser.add_argument('-v', '--verbose', dest='be_verbose', action='store_true', help='Output some debug info.')
    parser.add_argument('--gui', dest='launch_gui', action='store_true', help='Launch GUI.')
    parser.add_argument('--ask', dest='ask_question', type=str, help='Ask model a question.')
    parser.add_argument('--preset', dest='set_preset', type=str, help='Pass a preset name.')
    args = parser.parse_args()

    client = ChatGPTClient()
    client.globals.verbose = bool(args.be_verbose)
    match args:
        case argparse.Namespace(fetch_models=True):
            return print(client.fetch_model_names())
        case argparse.Namespace(print_presets=True):
            return print("\n".join(client.presets))
        case argparse.Namespace() if (args.ask_question and args.set_preset):
            return print(client.send_message(args.ask_question, args.set_preset))
        case argparse.Namespace(launch_gui=True):
            return gui.main(client)
        case _:
            return parser.print_help()


if __name__ == '__main__':
    main()
