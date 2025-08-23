# Smart Git AI Agent

🤖 **Smart Git AI Agent** is an intelligent Git automation tool that monitors file changes in a Git repository, automatically generates meaningful commit messages using AI, and optionally pushes changes to a remote repository. It uses emojis to categorize commits, supports custom ignore patterns, and includes features like dry-run mode for testing. Built as a Python package, it leverages the OpenRouter API for AI-generated commit messages and integrates seamlessly with existing Git workflows.

## Features

- **Automatic File Monitoring**: Watches for file changes using `watchdog`.
- **Smart Commit Messages**: Generates concise, professional commit messages with emojis (e.g., ✨ for features, 🐛 for fixes).
- **AI Integration**: Uses OpenRouter API to generate context-aware commit messages.
- **Multi-Language Support**: Automatically detects project languages and frameworks for optimal `.gitignore` generation.
- **Custom Ignore Patterns**: Ignores files based on default patterns, `.gitignore`, and user-defined patterns.
- **Dry-Run Mode**: Simulates commits without making changes.
- **Customizable Commit Messages**: Supports custom commit message templates.
- **Auto-Push**: Optionally pushes commits to the remote repository.
- **Installable Package**: Can be installed via `pip` and run as a CLI tool.

## Supported Languages & Frameworks

Smart Git AI Agent automatically detects your project type and creates appropriate `.gitignore` patterns:

### 🐍 **Python**
- **Detection**: `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile`, `poetry.lock`, `.py` files
- **Ignores**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `build/`, `.pytest_cache/`, `.mypy_cache/`, etc.

### 🌐 **JavaScript/Node.js**
- **Detection**: `package.json`
- **Ignores**: `node_modules/`, `npm-debug.log*`, `yarn-error.log*`, `.npm`, `.cache/`, etc.

#### **Frontend Frameworks:**
- **Next.js** 🚀
  - **Detection**: `next` in dependencies, `next.config.js`
  - **Ignores**: `.next/`, `next-env.d.ts`, `.vercel/`, `out/`

- **React** ⚛️
  - **Detection**: `react` in dependencies
  - **Ignores**: `build/`, `.expo/`, `.expo-shared/`

- **Vue.js** 💚
  - **Detection**: `vue` in dependencies, `vue.config.js`
  - **Ignores**: `dist/`, `.nuxt/`

- **Nuxt.js** 🟢
  - **Detection**: `nuxt` in dependencies, `nuxt.config.js`
  - **Ignores**: `.nuxt/`, `.output/`, `dist/`

- **Vite** ⚡
  - **Detection**: `vite` in dependencies, `vite.config.js`
  - **Ignores**: `dist/`, `dist-ssr/`, `*.local`

- **Angular** 🅰️
  - **Detection**: `@angular/core` in dependencies, `angular.json`
  - **Ignores**: `dist/`, `.angular/`, `bazel-out/`

- **Svelte** 🧡
  - **Detection**: `svelte` in dependencies, `svelte.config.js`
  - **Ignores**: `.svelte-kit/`, `package/`

### 🦀 **Rust**
- **Detection**: `Cargo.toml`
- **Ignores**: `target/`, `Cargo.lock`, `*.rs.bk`

### 🐹 **Go**
- **Detection**: `go.mod`, `.go` files
- **Ignores**: `vendor/`, `*.exe`, `*.test`, `*.out`

### ☕ **Java/Kotlin**
- **Detection**: `pom.xml`, `build.gradle`, `build.gradle.kts`
- **Ignores**: `target/`, `build/`, `*.class`, `*.jar`, `.gradle/`

### 🔷 **C#/.NET**
- **Detection**: `*.csproj`, `*.sln`, `Program.cs`
- **Ignores**: `bin/`, `obj/`, `*.user`, `.vs/`, `[Dd]ebug/`, `[Rr]elease/`

### 🐘 **PHP**
- **Detection**: `composer.json`, `.php` files
- **Ignores**: `vendor/`, `composer.lock`

### 💎 **Ruby**
- **Detection**: `Gemfile`, `.rb` files
- **Ignores**: `*.gem`, `.bundle/`, `vendor/`, `tmp/`

### 📱 **Flutter/Dart**
- **Detection**: `pubspec.yaml`
- **Ignores**: `.dart_tool/`, `.flutter-plugins`, `.pub-cache/`, `build/`

### 🍎 **Swift**
- **Detection**: `*.xcodeproj`, `*.xcworkspace`, `Package.swift`
- **Ignores**: `build/`, `DerivedData/`, `*.xcodeproj/xcuserdata/`

### 🐳 **Docker**
- **Detection**: `Dockerfile`, `docker-compose.yml`
- **Special handling**: Respects `.dockerignore`

### 🌍 **Web Technologies**
- **Detection**: `.html`, `.css`, `.js`, `.ts` files
- **Ignores**: `*.map`, `dist/`, `build/`

### 🔧 **Additional Electron Support**
- **Detection**: `electron` in dependencies
- **Ignores**: Platform-specific build directories

## Requirements

- Python 3.8+
- Git installed and configured
- OpenRouter API key (obtainable from [OpenRouter](https://openrouter.ai/))

## Installation

1. **Install the Package**:
   Install `smart-git-agent` using pip:
   ```bash
   pip install .
   ```
   Or, if installing from a source distribution:
   ```bash
   pip install smart-git-agent
   ```

2. **Create Configuration File**:
   Generate a default configuration file:
   ```bash
   smart-git-agent --setup
   ```

3. **Configure the API Key**:
   Edit `git-agent-config.ini` (created in the current directory) to add your OpenRouter API key and customize settings (see [Configuration](#configuration)).

## Usage

Run the Smart Git AI Agent as a command-line tool:

```bash
smart-git-agent --repo /path/to/your/repo
```

### Command-Line Options

- `--repo <path>`: Path to the Git repository (default: current directory).
- `--config <path>`: Configuration file path (default: `git-agent-config.ini`).
- `--setup`: Create a default configuration file and exit.
- `--dry-run`: Simulate commits without making changes.

Example:
```bash
smart-git-agent --repo ./my-project --dry-run
```

Alternatively, run as a Python module:
```bash
python -m smart_git_agent --repo ./my-project
```

To stop the agent, press `Ctrl+C`.

## Configuration

The configuration file (`git-agent-config.ini`) allows customization:

```ini
[DEFAULT]
openrouter_api_key = YOUR_API_KEY_HERE
model = openai/gpt-4o
language = français
branch = main
debounce_time = 10
auto_push = true
dry_run = false
commit_template = {emoji} {commit_type}{scope}: {description}
ignored_patterns =
site_url =
site_name =
```

### Configuration Options

- `openrouter_api_key`: Required OpenRouter API key.
- `model`: AI model for commit messages (default: `openai/gpt-4o`).
- `language`: Commit message language (e.g., `français`, `english`).
- `branch`: Default Git branch (default: `main`).
- `debounce_time`: Seconds between commits (default: 10).
- `auto_push`: Push commits to remote (`true` or `false`).
- `dry_run`: Simulate commits (`true` or `false`).
- `commit_template`: Commit message format (supports `{emoji}`, `{commit_type}`, `{scope}`, `{description}`).
- `ignored_patterns`: Comma-separated regex patterns to ignore files (e.g., `*.bak, temp/.*`).
- `site_url`, `site_name`: Optional metadata for OpenRouter API.

## Smart .gitignore Generation

When the agent detects your project for the first time, it automatically creates a comprehensive `.gitignore` file based on detected languages and frameworks. For example:

### Multi-Framework Project Detection
```bash
🔍 Detected languages/frameworks: nextjs, react, nodejs, python, docker
✅ Created .gitignore for: nextjs, nodejs, python, docker, react
```

### Generated .gitignore Example (Next.js + Python)
```gitignore
# === Common files ===
.DS_Store
.env
.env.local
*.log
*.tmp
.vscode/
.idea/

# === NODEJS ===
node_modules/
npm-debug.log*
.cache/
.npm

# === NEXTJS ===
.next/
next-env.d.ts
.vercel/
out/

# === PYTHON ===
__pycache__/
*.pyc
.venv/
venv/
build/
dist/
*.egg-info/
.pytest_cache/
```

## Commit Types and Emojis

| Type       | Emoji | Keywords                              |
|------------|-------|---------------------------------------|
| feat       | ✨     | add, create, implement, introduce    |
| fix        | 🐛     | fix, resolve, correct, repair        |
| docs       | 📚     | readme, documentation, comment, doc  |
| style      | 💅     | format, style, lint, prettier        |
| refactor   | ♻️     | refactor, restructure, reorganize    |
| perf       | ⚡     | performance, optimize, speed         |
| test       | 🧪     | test, spec, unittest                 |
| chore      | 🔧     | config, build, deps, dependency      |
| security   | 🔒     | security, auth, permission           |
| update     | 🔄     | update, upgrade, bump                |
| remove     | 🗑️     | remove, delete, clean                |
| init       | 🎉     | initial, first, setup                |

## Development Setup

1. **Clone or Set Up the Repository**:
   ```bash
   git clone <repository-url>
   cd PythonProject
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Unix/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the Package Locally**:
   ```bash
   pip install -e .
   ```

5. **Run Tests**:
   (Add tests in a future update, e.g., using `pytest`.)

## Example Usage Scenarios

### Web Development Project (Next.js + TypeScript)
```bash
cd my-nextjs-app
smart-git-agent --repo .
# 🔍 Detected: nextjs, react, nodejs, web
# ✅ Auto-ignores: .next/, node_modules/, *.local
```

### Python Data Science Project
```bash
cd ml-project  
smart-git-agent --repo .
# 🔍 Detected: python
# ✅ Auto-ignores: __pycache__/, .venv/, *.pyc, .jupyter/
```

### Full-Stack Project (Next.js + Python API)
```bash
cd fullstack-app
smart-git-agent --repo .
# 🔍 Detected: nextjs, python, nodejs, docker
# ✅ Comprehensive .gitignore for all detected technologies
```

## Troubleshooting

- **ImportError**: Ensure you're running the script as a module (`python -m smart_git_agent`) or the package is installed (`pip install .`).
- **Missing API Key**: Set `openrouter_api_key` in `git-agent-config.ini`.
- **Invalid Repository**: Verify the `--repo` path contains a `.git` directory.
- **API Errors**: Check your OpenRouter API key and internet connection.
- **Files Still Being Committed**: Check the debug logs to see pattern matching. Use `ignored_patterns` in config for additional custom patterns.
- **Clear Cache**: Remove `__pycache__` directories if issues persist:
  ```bash
  rmdir /s /q smart_git_agent\__pycache__
  ```

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/new-feature`).
3. Commit changes (`smart-git-agent` can automate this!).
4. Submit a pull request.

## License

MIT License (see [LICENSE](LICENSE)).

## Contact

For issues or feature requests, open an issue on the project's GitHub repository.