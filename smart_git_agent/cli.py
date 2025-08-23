import argparse
import logging
import time
import os
from watchdog.observers import Observer
from .smart_git_agent import SmartGitAgent
from .config_manager import load_config, create_default_config
from git import Repo
import keyboard  # Added for key press detection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="🤖 Smart Git AI Agent - Intelligent commits with emojis")
    parser.add_argument('--repo', default='.', help='Path to Git repository')
    parser.add_argument('--config', default='git-agent-config.ini', help='Configuration file path')
    parser.add_argument('--setup', action='store_true', help='Create default configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Simulate commits without making changes')

    args = parser.parse_args()

    # Setup mode
    if args.setup:
        create_default_config(args.config)
        return

    # Validate Git repository
    if not os.path.isdir(os.path.join(args.repo, '.git')):
        logger.error("❌ Specified path is not a Git repository")
        return

    # Load configuration
    config = load_config(args.config)
    if args.dry_run:
        config['dry_run'] = True

    if not config['openrouter_api_key'] or config['openrouter_api_key'] == 'YOUR_API_KEY_HERE':
        logger.error("❌ OpenRouter API key missing. Use --setup to create config file")
        return

    # Initialize empty repo
    repo = Repo(args.repo)
    if repo.head.is_detached or not repo.head.is_valid():
        logger.info("ℹ️ Empty repository, creating initial commit...")
        repo.git.add(A=True)
        repo.index.commit("🎉 Initial commit")
        logger.info("✅ Initial commit created")

    # Start agent
    event_handler = SmartGitAgent(args.repo, config)
    observer = Observer()
    observer.schedule(event_handler, args.repo, recursive=True)
    observer.start()

    logger.info(f"👀 🤖 Smart Git AI Agent active on {args.repo}")
    logger.info(f"🌍 Language: {config['language']} | 🚀 Model: {config['model']}")
    logger.info("Press 'p' to commit and push, or Ctrl+C to stop")

    try:
        while True:
            if keyboard.is_pressed('p'):
                logger.info("🛠️ Manual commit and push triggered by 'p' key")
                event_handler.commit_and_push()
                # Debounce to prevent multiple rapid presses
                time.sleep(0.5)
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping agent...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()