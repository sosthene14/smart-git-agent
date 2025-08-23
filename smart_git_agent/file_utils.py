import json
import os
import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import Counter, defaultdict
import csv
import fnmatch
import shutil
from git import Repo

logger = logging.getLogger(__name__)

class FileUtils:
    """Utility class for file operations and metrics analysis in CommitAnalyzer."""

    def __init__(self, repo_path: str = '.', config: Optional[Dict] = None):
        self.repo_path = repo_path
        self.base_path = repo_path
        self.repo = Repo(repo_path)  # Initialize Git Repo object
        self.metrics_file = os.path.join(self.base_path, '.commit_metrics.jsonl')
        self.config_file = os.path.join(self.base_path, '.commit_analyzer_config.json')
        self.cache_dir = os.path.join(self.base_path, '.commit_analyzer_cache')
        self.backup_dir = os.path.join(self.base_path, 'backups')
        self.detected_languages = self._detect_project_languages()
        self.ignored_patterns = self._load_ignored_patterns(config or {})
        self.file_hashes = {}
        self._ensure_directories()
        self._ensure_gitignore()

    def _ensure_directories(self):
        """Create necessary directories for metrics and cache."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create directories: {e}")

    def _detect_project_languages(self) -> Set[str]:
        """Auto-detect project languages/frameworks based on files present."""
        languages = set()
        root_files = os.listdir(self.repo_path) if os.path.exists(self.repo_path) else []

        language_files = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'poetry.lock', '*.py'],
            'nodejs': ['package.json'],
            'rust': ['Cargo.toml'],
            'go': ['go.mod', '*.go'],
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'csharp': ['*.csproj', '*.sln', 'Program.cs'],
            'php': ['composer.json', '*.php'],
            'ruby': ['Gemfile', '*.rb'],
            'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'flutter': ['pubspec.yaml'],
            'swift': ['*.xcodeproj', '*.xcworkspace', 'Package.swift'],
            'web': ['*.html', '*.css', '*.js', '*.ts']
        }

        config_files = {
            'vite.config.js': 'vite', 'vite.config.ts': 'vite',
            'next.config.js': 'nextjs', 'next.config.mjs': 'nextjs',
            'nuxt.config.js': 'nuxt', 'nuxt.config.ts': 'nuxt',
            'angular.json': 'angular',
            'vue.config.js': 'vue',
            'svelte.config.js': 'svelte'
        }

        for lang, patterns in language_files.items():
            if any(any(fnmatch.fnmatch(f, p) for p in patterns) for f in root_files):
                languages.add(lang)

        if 'package.json' in root_files:
            try:
                with open(os.path.join(self.repo_path, 'package.json'), 'r') as f:
                    package_data = json.load(f)
                    deps = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    frameworks = {
                        'next': 'nextjs', 'react': 'react', 'vue': 'vue', 'svelte': 'svelte',
                        'vite': 'vite', 'nuxt': 'nuxt', '@angular/core': 'angular', 'electron': 'electron'
                    }
                    for dep, framework in frameworks.items():
                        if dep in deps:
                            languages.add(framework)
            except Exception as e:
                logger.debug(f"Error reading package.json: {e}")

        for config_file, lang in config_files.items():
            if config_file in root_files:
                languages.add(lang)

        logger.info(f"🔍 Detected languages/frameworks: {', '.join(languages) if languages else 'generic'}")
        return languages

    def _get_language_patterns(self) -> Dict[str, Set[str]]:
        """Get ignore patterns for each detected language/framework."""
        patterns = {
            'python': {
                '__pycache__', '*.py[cod]', '*$py.class', '*.so', '.Python', 'pip-log.txt',
                'pip-delete-this-directory.txt', 'build', 'develop-eggs', 'dist', 'downloads',
                'eggs', '.eggs', 'lib', 'lib64', 'parts', 'sdist', 'var', 'wheels',
                'share/python-wheels', '*.egg-info', '.installed.cfg', '*.egg', 'MANIFEST',
                '.env', '.venv', 'env', 'venv', 'ENV', 'env.bak', 'venv.bak', 'pyvenv.cfg',
                '.tox', '.nox', '.coverage', '.coverage.*', '.cache', 'nosetests.xml',
                'coverage.xml', '*.cover', '*.py,cover', '.hypothesis', '.pytest_cache',
                '.mypy_cache', '.dmypy.json', 'dmypy.json', '.ipynb_checkpoints', '.python-version'
            },
            'nodejs': {
                'node_modules', 'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*', 'lerna-debug.log*',
                'pids', '*.pid', '*.seed', '*.pid.lock', 'coverage', '*.lcov', '.nyc_output', '.grunt',
                'bower_components', '.lock-wscript', 'build/Release', 'jspm_packages', '.npm',
                '.eslintcache', '*.tgz', '.yarn-integrity', '.cache', '.parcel-cache',
                '.yarn/cache', '.yarn/unplugged', '.yarn/build-state.yml', '.yarn/install-state.gz', '.pnp.*'
            },
            'nextjs': {'.next', 'next-env.d.ts', '.vercel', 'out'},
            'react': {'build', '.expo', '.expo-shared'},
            'vue': {'.nuxt', 'dist'},
            'nuxt': {'.nuxt', '.output', '.env', 'dist'},
            'vite': {'dist', 'dist-ssr', '*.local'},
            'angular': {'dist', 'tmp', 'out-tsc', 'bazel-out', '.angular'},
            'svelte': {'.svelte-kit', 'package', '.env.*', '!.env.example'},
            'rust': {'target', 'Cargo.lock', '*.rs.bk', '*.pdb'},
            'go': {'*.exe', '*.exe~', '*.dll', '*.so', '*.dylib', 'vendor', '*.test', '*.out', 'go.work'},
            'java': {
                'target', '*.class', '*.log', '*.ctxt', '.mtj.tmp', '*.jar', '*.war', '*.nar',
                '*.ear', '*.zip', '*.tar.gz', '*.rar', 'hs_err_pid*', 'replay_pid*', '.gradle',
                'build', 'gradle-app.setting', '!gradle-wrapper.jar', '.gradletasknamecache'
            },
            'csharp': {
                'bin', 'obj', '*.user', '*.userosscache', '*.sln.docstates', '.vs', '[Dd]ebug',
                '[Dd]ebugPublic', '[Rr]elease', '[Rr]eleases', 'x64', 'x86', 'bld', '[Bb]in',
                '[Oo]bj', '*.dll', '*.exe', '*.pdb'
            },
            'php': {'vendor', 'composer.lock', '*.log', '.env', '.env.local', '.env.*.local'},
            'ruby': {
                '*.gem', '*.rbc', '.bundle', '.config', 'coverage', 'InstalledFiles', 'lib/bundler/man',
                'pkg', 'rdoc', 'spec/reports', 'test/tmp', 'test/version_tmp', 'tmp', '.yardoc', '_yardoc', 'doc'
            },
            'flutter': {'.dart_tool', '.flutter-plugins', '.flutter-plugins-dependencies', '.packages', '.pub-cache', '.pub', 'build'},
            'swift': {
                'build', 'DerivedData', '*.hmap', '*.ipa', '*.dSYM.zip', '*.dSYM', 'timeline.xctimeline',
                'playground.xcworkspace', '.build', 'Packages', '*.xcodeproj/project.xcworkspace',
                '*.xcodeproj/xcuserdata', '*.xcworkspace/xcuserdata'
            },
            'docker': {'.dockerignore'},
            'web': {'*.map', 'dist', 'build'},
            'common': {
                '.vscode', '.idea', '*.swp', '*.swo', '*.tmp', '*~', '.sublime-project', '.sublime-workspace',
                '.DS_Store', '.DS_Store?', '._*', '.Spotlight-V100', '.Trashes', 'ehthumbs.db', 'Thumbs.db',
                'Desktop.ini', '*.log', 'logs', 'log', '.env', '.env.local', '.env.development.local',
                '.env.test.local', '.env.production.local', '*.bak', '*.backup', '*.old', '*.orig',
                '*.7z', '*.dmg', '*.gz', '*.iso', '*.rar', '*.tar', '*.zip', 'git-agent-config.ini',
                '.commit_metrics.jsonl', '.commit_analyzer_config.json', '.commit_analyzer_cache/*'
            }
        }
        return patterns

    def _ensure_gitignore(self):
        """Ensure .gitignore exists and includes git-agent-config.ini and metrics file."""
        gitignore_path = os.path.join(self.repo_path, '.gitignore')
        config_files = ['git-agent-config.ini', '.commit_metrics.jsonl', '.commit_analyzer_config.json', '.commit_analyzer_cache/']

        try:
            tracked_files = [item.a_path for item in self.repo.index.diff(None)] + self.repo.untracked_files
            index_entries = [path for path, _ in self.repo.index.entries.keys()]
            for config_file in config_files:
                if config_file in tracked_files or config_file in index_entries:
                    self.repo.index.remove([config_file], cached=True)
                    self.repo.index.commit(f"Remove '{config_file}' from tracking")
                    logger.info(f"Removed '{config_file}' from tracking")
        except Exception as e:
            logger.warning(f"Could not remove config files from tracking: {e}")

        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    for config_file in config_files:
                        if config_file not in lines:
                            with open(gitignore_path, 'a', encoding='utf-8') as f:
                                f.write(f"\n# Smart Git Agent configuration\n{config_file}\n")
                            logger.info(f"Added '{config_file}' to existing .gitignore")
            except Exception as e:
                logger.warning(f"Could not update .gitignore: {e}")
            return

        language_patterns = self._get_language_patterns()
        gitignore_content = ["# Auto-generated .gitignore", "# Created by Smart Git Agent", ""]
        if 'common' in language_patterns:
            gitignore_content.extend(["# === Common files ===", *sorted(language_patterns['common']), ""])
        for lang in sorted(self.detected_languages):
            if lang in language_patterns:
                gitignore_content.extend([f"# === {lang.upper()} ===", *sorted(language_patterns[lang]), ""])

        try:
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(gitignore_content))
            logger.info(f"Created .gitignore for: {', '.join(sorted(self.detected_languages)) if self.detected_languages else 'generic'}")
        except Exception as e:
            logger.warning(f"Could not create .gitignore: {e}")

    def _load_ignored_patterns(self, config: Dict) -> Set[str]:
        """Load all ignore patterns from gitignore and config."""
        patterns = set()
        language_patterns = self._get_language_patterns()

        if 'common' in language_patterns:
            patterns.update(language_patterns['common'])
        for lang in self.detected_languages:
            if lang in language_patterns:
                patterns.update(language_patterns[lang])
        patterns.update(self._load_gitignore_patterns())
        patterns.update(self._load_custom_patterns(config))
        return patterns

    def _load_gitignore_patterns(self) -> Set[str]:
        """Load patterns from .gitignore file."""
        patterns = set()
        gitignore_path = os.path.join(self.repo_path, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and line != '/':
                            pattern = line.lstrip('/')
                            if pattern:
                                patterns.add(pattern)
            except Exception as e:
                logger.warning(f"Error reading .gitignore: {e}")
        return patterns

    def _load_custom_patterns(self, config: Dict) -> Set[str]:
        """Load custom patterns from config."""
        patterns = set()
        config_patterns = config.get('ignored_patterns', '').split(',')
        for pattern in config_patterns:
            pattern = pattern.strip()
            if pattern:
                patterns.add(pattern)
        return patterns

    def should_ignore_file(self, file_path: str) -> bool:
        """Check if a file should be ignored using glob patterns."""
        try:
            relative_path = os.path.relpath(file_path, self.repo_path).replace(os.sep, '/')
        except ValueError:
            return True

        for pattern in self.ignored_patterns:
            pattern = pattern.replace(os.sep, '/')
            if self._match_pattern(relative_path, pattern):
                logger.debug(f"Ignoring {relative_path} (matches: {pattern})")
                return True
            path_parts = relative_path.split('/')
            for i in range(len(path_parts)):
                partial_path = '/'.join(path_parts[:i + 1])
                if self._match_pattern(partial_path, pattern):
                    logger.debug(f"Ignoring {relative_path} (parent {partial_path} matches: {pattern})")
                    return True
        return False

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a gitignore-style pattern."""
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            return path == pattern or path.startswith(pattern + '/')
        if '*' in pattern or '?' in pattern:
            return fnmatch.fnmatch(path, pattern)
        if path == pattern:
            return True
        if '/' in path and path.split('/')[0] == pattern:
            return True
        return False

    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate the MD5 hash of a file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, IOError) as e:
            logger.debug(f"Could not read file {file_path}: {e}")
            return None

    def update_file_hashes(self):
        """Update hashes for all files in the repo."""
        self.file_hashes.clear()
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d != '.git']
            for file in files:
                file_path = os.path.join(root, file)
                if not self.should_ignore_file(file_path):
                    hash_value = self.calculate_file_hash(file_path)
                    if hash_value:
                        self.file_hashes[file_path] = hash_value

    def has_meaningful_changes(self, repo: Repo) -> bool:
        """Check if there are significant changes in the repository."""
        try:
            diff_files = [item.a_path for item in repo.index.diff(None)]  # Current changes
            untracked_files = repo.untracked_files
            if not diff_files and not untracked_files:
                logger.debug("No changes detected in repository")
                return False

            significant_changes = 0
            for file_path in diff_files + untracked_files:
                full_path = os.path.join(self.repo_path, file_path)
                if self.should_ignore_file(full_path):
                    logger.debug(f"Skipping file (ignored): {file_path}")
                    continue
                significant_changes += 1
                logger.debug(f"Significant change detected: {file_path}")
            logger.debug(f"Total significant changes: {significant_changes}")
            return significant_changes > 0
        except Exception as e:
            logger.error(f"Error checking changes: {e}")
            return False

    def append_to_metrics_file(self, metrics_data: Dict[str, Any]):
        """Append metrics to the log file."""
        try:
            with open(self.metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metrics_data) + '\n')
        except Exception as e:
            logger.error(f"Error writing metrics: {e}")

    def load_metrics_stats(self) -> Dict[str, Any]:
        """Load and analyze metrics statistics."""
        try:
            if not os.path.exists(self.metrics_file):
                return {}

            metrics = []
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            metrics.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            if not metrics:
                return {}

            total_count = len(metrics)
            successful_count = sum(1 for m in metrics if m.get('success', False))
            cutoff_date = datetime.now() - timedelta(days=30)
            recent_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > cutoff_date
            ]

            return {
                'total': total_count,
                'recent_total': len(recent_metrics),
                'success_rate': successful_count / total_count if total_count > 0 else 0.0,
                'avg_confidence': sum(m.get('confidence', 0) for m in metrics) / total_count if total_count > 0 else 0.0,
                'common_types': Counter(m.get('commit_type') for m in recent_metrics).most_common(5),
                'avg_time': sum(m.get('generation_time', 0) for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0.0,
                'models_used': Counter(m.get('model_used') for m in recent_metrics).most_common(),
                'daily_usage': self._calculate_daily_usage(recent_metrics),
                'confidence_distribution': self._calculate_confidence_distribution(recent_metrics)
            }
        except Exception as e:
            logger.error(f"Error loading metrics stats: {e}")
            return {}

    def _calculate_daily_usage(self, metrics: List[Dict]) -> Dict[str, int]:
        """Calculate daily usage from metrics."""
        daily_counts = defaultdict(int)
        for metric in metrics:
            try:
                timestamp = datetime.fromisoformat(metric['timestamp'].replace('Z', '+00:00'))
                daily_counts[timestamp.strftime('%Y-%m-%d')] += 1
            except (KeyError, ValueError):
                continue
        return dict(daily_counts)

    def _calculate_confidence_distribution(self, metrics: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of confidence scores."""
        distribution = {'very_low': 0, 'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
        for metric in metrics:
            confidence = metric.get('confidence', 0)
            if confidence < 0.3:
                distribution['very_low'] += 1
            elif confidence < 0.5:
                distribution['low'] += 1
            elif confidence < 0.7:
                distribution['medium'] += 1
            elif confidence < 0.9:
                distribution['high'] += 1
            else:
                distribution['very_high'] += 1
        return distribution

    def export_metrics_to_csv(self, output_file: Optional[str] = None) -> str:
        """Export metrics to a CSV file."""
        if output_file is None:
            output_file = os.path.join(self.base_path, 'commit_metrics_export.csv')
        try:
            metrics = []
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                metrics.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            if not metrics:
                logger.warning("No metrics to export")
                return output_file

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                if metrics:
                    fieldnames = metrics[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(metrics)
            logger.info(f"Metrics exported to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error exporting metrics to CSV: {e}")
            return ""

    def cleanup_old_metrics(self, days_to_keep: int = 90):
        """Clean up metrics older than specified days."""
        try:
            if not os.path.exists(self.metrics_file):
                return

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            temp_file = self.metrics_file + '.tmp'
            kept_count = removed_count = 0

            with open(self.metrics_file, 'r', encoding='utf-8') as infile, \
                 open(temp_file, 'w', encoding='utf-8') as outfile:
                for line in infile:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        metric = json.loads(line)
                        timestamp = datetime.fromisoformat(metric['timestamp'].replace('Z', '+00:00'))
                        if timestamp > cutoff_date:
                            outfile.write(line + '\n')
                            kept_count += 1
                        else:
                            removed_count += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        outfile.write(line + '\n')
                        kept_count += 1

            if os.path.exists(temp_file):
                os.replace(temp_file, self.metrics_file)
                logger.info(f"Cleaned up metrics: kept {kept_count}, removed {removed_count}")
        except Exception as e:
            logger.error(f"Error cleaning up metrics: {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def save_project_config(self, config: Dict[str, Any]):
        """Save project configuration."""
        try:
            config_to_save = {
                **config,
                'last_updated': datetime.now().isoformat(),
                'version': '2.0'
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            logger.info("Project configuration saved")
        except Exception as e:
            logger.error(f"Error saving project config: {e}")

    def load_project_config(self) -> Dict[str, Any]:
        """Load project configuration."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading project config: {e}")
            return {}

    def get_project_insights(self) -> Dict[str, Any]:
        """Analyze project patterns for insights."""
        try:
            stats = self.load_metrics_stats()
            if not stats:
                return {}

            insights = {
                'productivity_score': 0.0,
                'consistency_score': 0.0,
                'recommendations': [],
                'trends': {}
            }

            total_commits = stats.get('total', 0)
            success_rate = stats.get('success_rate', 0.0)
            if total_commits > 0:
                usage_score = min(total_commits / 100, 1.0) * 50
                quality_score = success_rate * 50
                insights['productivity_score'] = usage_score + quality_score

            common_types = stats.get('common_types', [])
            if common_types:
                total_recent = stats.get('recent_total', 1)
                type_distribution = [count for _, count in common_types[:5]]
                if type_distribution:
                    mean_usage = sum(type_distribution) / len(type_distribution)
                    if mean_usage > 0:
                        variance = sum((x - mean_usage) ** 2 for x in type_distribution) / len(type_distribution)
                        cv = (variance ** 0.5) / mean_usage
                        insights['consistency_score'] = max(0, (1 - cv) * 100)

            recommendations = []
            if success_rate < 0.8:
                recommendations.append("Improve commit quality to increase success rate")
            if stats.get('avg_confidence', 0.0) < 0.6:
                recommendations.append("Write more descriptive commits for better detection")
            if common_types and common_types[0][1] / stats.get('recent_total', 1) > 0.6:
                recommendations.append(f"Diversify commit types (currently {common_types[0][1]/stats.get('recent_total', 1):.1%} are '{common_types[0][0]}')")
            if stats.get('avg_time', 0.0) > 5.0:
                recommendations.append("Optimize configuration to reduce generation time")
            insights['recommendations'] = recommendations

            daily_usage = stats.get('daily_usage', {})
            if daily_usage:
                last_7_days = []
                today = datetime.now()
                for i in range(7):
                    date = today - timedelta(days=i)
                    last_7_days.append(daily_usage.get(date.strftime('%Y-%m-%d'), 0))
                if len(last_7_days) >= 2:
                    recent_avg = sum(last_7_days[:3]) / 3
                    older_avg = sum(last_7_days[4:]) / max(len(last_7_days[4:]), 1)
                    if older_avg > 0:
                        trend_ratio = recent_avg / older_avg
                        insights['trends']['usage'] = 'increasing' if trend_ratio > 1.2 else 'decreasing' if trend_ratio < 0.8 else 'stable'
                    insights['trends']['daily_data'] = list(reversed(last_7_days))

            return insights
        except Exception as e:
            logger.error(f"Error generating project insights: {e}")
            return {}

    def backup_metrics(self, backup_dir: Optional[str] = None) -> str:
        """Create a backup of metrics."""
        if backup_dir is None:
            backup_dir = self.backup_dir
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'commit_metrics_backup_{timestamp}.jsonl')
            if os.path.exists(self.metrics_file):
                shutil.copy2(self.metrics_file, backup_file)
                logger.info(f"Metrics backed up to {backup_file}")
                return backup_file
            logger.warning("No metrics file to backup")
            return ""
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""

    def restore_metrics(self, backup_file: str) -> bool:
        """Restore metrics from a backup."""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
            if os.path.exists(self.metrics_file):
                current_backup = self.backup_metrics()
                logger.info(f"Current metrics backed up to {current_backup}")
            shutil.copy2(backup_file, self.metrics_file)
            logger.info(f"Metrics restored from {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error restoring metrics: {e}")
            return False

    def get_disk_usage(self) -> Dict[str, Any]:
        """Return disk usage of analyzer files."""
        usage = {
            'metrics_file_size': 0,
            'config_file_size': 0,
            'cache_dir_size': 0,
            'total_size': 0
        }
        try:
            if os.path.exists(self.metrics_file):
                usage['metrics_file_size'] = os.path.getsize(self.metrics_file)
            if os.path.exists(self.config_file):
                usage['config_file_size'] = os.path.getsize(self.config_file)
            if os.path.exists(self.cache_dir):
                cache_size = sum(os.path.getsize(os.path.join(root, file))
                                 for root, _, files in os.walk(self.cache_dir)
                                 for file in files)
                usage['cache_dir_size'] = cache_size
            usage['total_size'] = sum([usage['metrics_file_size'], usage['config_file_size'], usage['cache_dir_size']])
            for key in usage:
                size = usage[key]
                if size < 1024:
                    usage[f'{key}_readable'] = f"{size} B"
                elif size < 1024 * 1024:
                    usage[f'{key}_readable'] = f"{size / 1024:.1f} KB"
                else:
                    usage[f'{key}_readable'] = f"{size / (1024 * 1024):.1f} MB"
        except Exception as e:
            logger.error(f"Error calculating disk usage: {e}")
        return usage