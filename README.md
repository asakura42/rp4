# rp4

simple python replacement for the bloated LLM frontends

4rp */fourp/* is a simple and minimalist LLM frontend initially written in a few days, not without the help of LLMs.

## Installation

```bash
pipx install 'git+https://github.com/asakura42/4rp.git'
```

```bash
pipx install rp4
```

## Usage

```bash
rp4 --gui
```

The program uses [https://github.com/xtekky/gpt4free](gpt4free) library or your own OpenAI-compatible completions API.

This program was written for the my own use and is still in development, so it may not always work the way the user expects. For example, if the model does not change, simply close and reopen the program. To delete preset, edit file `settings.json` manually.

TODO:
- various quotes handling
- aicg proxy parsing (do I really need it?)

Any improvements, issues, thoughts and pull requests will be appreciated.

===

*Gabriela from settings.json example taken from https://www.chub.ai/characters/summernon/practice-spanish-with-gabriela*
