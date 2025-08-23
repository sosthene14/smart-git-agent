import os
import configparser
from pathlib import Path


def load_config(config_path: str) -> dict:
    """Load configuration from a file."""
    default_config = {
        'openrouter_api_key': '',
        'model': 'openai/gpt-4o',
        'language': 'français',
        'branch': 'main',
        'debounce_time': 10,
        'auto_push': True,
        'site_url': '',
        'site_name': '',
        'dry_run': False,
        'commit_template': '{emoji} {commit_type}{scope}: {description}',
        'ignored_patterns': '*.log,*.tmp,*.swp,*.swo,*.bak,.DS_Store,*.pyc,*.cache,dist/.*,build/.*,coverage/.*,node_modules/.*,__pycache__/.*,*.egg-info/.*,.vscode/.*,.idea/.*,venv/.*,.venv/.*'
    }

    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        if 'DEFAULT' in config:
            for key, value in config['DEFAULT'].items():
                if key in default_config:
                    if key in ['debounce_time']:
                        default_config[key] = int(value)
                    elif key in ['auto_push', 'dry_run']:
                        default_config[key] = value.lower() == 'true'
                    else:
                        default_config[key] = value

    return default_config


def create_default_config(config_path: str):
    """Create a default configuration file."""
    config_content = """[DEFAULT]
# OpenRouter API key (required)
openrouter_api_key = YOUR_API_KEY_HERE

# AI model to use
model = openai/gpt-4o

# Language for commit messages (français, english, español, etc.)
language = français

# Default branch
branch = main

# Debounce time before commit (seconds)
debounce_time = 10

# Auto-push after commit
auto_push = true

# Dry-run mode (simulate commits without making them)
dry_run = false

# Commit message template
# Placeholders: {emoji}, {commit_type}, {scope}, {description}
# Example: ✨ feat(auth): add JWT authentication
commit_template = {emoji} {commit_type}{scope}: {description}

# Custom file patterns to ignore (comma-separated regex patterns)
# Default patterns ignore logs, temporary files, build artifacts, IDE configs, and virtual environments
ignored_patterns = *.log,*.tmp,*.swp,*.swo,*.bak,.DS_Store,*.pyc,*.cache,dist/.*,build/.*,coverage/.*,node_modules/.*,__pycache__/.*,*.egg-info/.*,.vscode/.*,.idea/.*,venv/.*,.venv/.*

# Optional: site URL and name
site_url = 
site_name = 
"""
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print(f"✅ Configuration file created: {config_path}")
    print("👉 Please edit the file and add your OpenRouter API key")
