import json
import os
import ast
import re
import requests
import logging
import functools
import hashlib
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import Counter
from .file_utils import FileUtils

logger = logging.getLogger(__name__)


@dataclass
class FileAnalysis:

    imports_added: List[str]
    functions_added: List[str]
    classes_added: List[str]
    lines_complexity: int
    file_types: Set[str]
    language: str
    patterns: List[str]


@dataclass
class CommitMetrics:
    timestamp: datetime
    commit_type: str
    confidence: float
    message_length: int
    files_count: int
    success: bool
    model_used: str
    generation_time: float


class CommitAnalyzer:
    def __init__(self, config: dict, file_utils: FileUtils):
        self.config = config
        self.file_utils = file_utils
        self.commit_patterns = self._load_commit_patterns()
        self._cache = {}
        self._cache_expiry = timedelta(minutes=5)
        self.context_templates = self._load_context_templates()
        self.language_patterns = self._load_language_patterns()

    def _load_commit_patterns(self) -> Dict[str, Dict]:
        """Load commit patterns with emojis and enhanced keywords."""
        return {
            'feat': {
                'emoji': '✨',
                'keywords': ['add', 'create', 'implement', 'introduce', 'new', 'feature', 'endpoint', 'component'],
                'weight': 1.0
            },
            'fix': {
                'emoji': '🐛',
                'keywords': ['fix', 'resolve', 'correct', 'repair', 'bug', 'error', 'issue', 'crash', 'exception'],
                'weight': 1.2
            },
            'docs': {
                'emoji': '📚',
                'keywords': ['readme', 'documentation', 'comment', 'doc', 'guide', 'tutorial', 'example'],
                'weight': 0.8
            },
            'style': {
                'emoji': '💅',
                'keywords': ['format', 'style', 'lint', 'prettier', 'whitespace', 'semicolon', 'indent'],
                'weight': 0.6
            },
            'refactor': {
                'emoji': '♻️',
                'keywords': ['refactor', 'restructure', 'reorganize', 'rename', 'move', 'extract', 'split'],
                'weight': 0.9
            },
            'perf': {
                'emoji': '⚡',
                'keywords': ['performance', 'optimize', 'speed', 'faster', 'cache', 'memory', 'efficient'],
                'weight': 1.1
            },
            'test': {
                'emoji': '🧪',
                'keywords': ['test', 'spec', 'unittest', 'testing', 'mock', 'fixture', 'assert'],
                'weight': 0.9
            },
            'chore': {
                'emoji': '🔧',
                'keywords': ['config', 'build', 'deps', 'dependency', 'package', 'setup', 'tool'],
                'weight': 0.7
            },
            'security': {
                'emoji': '🔒',
                'keywords': ['security', 'auth', 'permission', 'vulnerability', 'sanitize', 'encrypt'],
                'weight': 1.3
            },
            'update': {
                'emoji': '🔄',
                'keywords': ['update', 'upgrade', 'bump', 'change', 'modify', 'version', 'migrate'],
                'weight': 0.8
            },
            'remove': {
                'emoji': '🗑️',
                'keywords': ['remove', 'delete', 'clean', 'unused', 'deprecated', 'obsolete'],
                'weight': 0.8
            },
            'init': {
                'emoji': '🎉',
                'keywords': ['initial', 'first', 'setup', 'scaffold', 'bootstrap', 'initialize'],
                'weight': 1.0
            },
            'hotfix': {
                'emoji': '🚑',
                'keywords': ['hotfix', 'critical', 'urgent', 'emergency', 'production'],
                'weight': 1.5
            },
            'ci': {
                'emoji': '👷',
                'keywords': ['ci', 'pipeline', 'workflow', 'action', 'deploy', 'build'],
                'weight': 0.7
            }
        }

    def _load_context_templates(self) -> Dict[str, str]:

        return {
            'feat': "ajoute {feature} pour {purpose}",
            'fix': "corrige {issue} dans {component}",
            'refactor': "restructure {component} pour améliorer {aspect}",
            'perf': "optimise {component} en {method}",
            'security': "sécurise {component} contre {threat}",
            'test': "teste {functionality} avec {method}",
            'docs': "documente {feature} avec {details}",
            'update': "met à jour {component} vers {version}",
            'remove': "supprime {component} car {reason}",
            'style': "formate {files} selon {standard}",
            'chore': "configure {tool} pour {purpose}"
        }

    def _load_language_patterns(self) -> Dict[str, Dict]:

        return {
            'python': {
                'extensions': ['.py', '.pyx', '.pyi'],
                'patterns': {
                    'class': r'class\s+(\w+)',
                    'function': r'def\s+(\w+)',
                    'import': r'(?:from\s+\w+\s+)?import\s+([\w\.,\s]+)',
                    'decorator': r'@(\w+)',
                }
            },
            'javascript': {
                'extensions': ['.js', '.ts', '.jsx', '.tsx'],
                'patterns': {
                    'function': r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?(?:function|\()|(?:async\s+)?(\w+)\s*\()',
                    'class': r'class\s+(\w+)',
                    'import': r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"][^\'"]+[\'"]',
                    'export': r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)',
                }
            },
            'general': {
                'extensions': [],
                'patterns': {}
            }
        }

    @functools.lru_cache(maxsize=100)
    def _get_file_language(self, filename: str) -> str:

        ext = os.path.splitext(filename)[1].lower()
        for lang, config in self.language_patterns.items():
            if ext in config['extensions']:
                return lang
        return 'general'

    def _analyze_file_content(self, file_path: str, diff_content: str) -> FileAnalysis:

        language = self._get_file_language(file_path)
        patterns = self.language_patterns[language]['patterns']

        analysis = FileAnalysis(
            imports_added=[],
            functions_added=[],
            classes_added=[],
            lines_complexity=0,
            file_types={language},
            language=language,
            patterns=[]
        )

        added_lines = [line[1:] for line in diff_content.split('\n') if line.startswith('+')]
        added_content = '\n'.join(added_lines)

        for pattern_type, pattern in patterns.items():
            matches = re.findall(pattern, added_content, re.MULTILINE)
            if matches:
                if pattern_type == 'function':
                    functions = [match if isinstance(match, str) else next((m for m in match if m), '')
                                 for match in matches]
                    analysis.functions_added.extend([f for f in functions if f])
                elif pattern_type == 'class':
                    analysis.classes_added.extend(matches)
                elif pattern_type == 'import':
                    analysis.imports_added.extend(matches)

        analysis.lines_complexity = len([line for line in added_lines if line.strip()])

        analysis.patterns = self._detect_code_patterns(added_content, language)

        return analysis

    def _detect_code_patterns(self, content: str, language: str) -> List[str]:
        patterns = []
        content_lower = content.lower()

        pattern_keywords = {
            'middleware': ['middleware', 'decorator', '@app.', '@route'],
            'api_endpoint': ['@app.route', 'def get_', 'def post_', 'def put_', 'def delete_', 'api'],
            'database': ['select', 'insert', 'create table', 'migration', 'query', 'model'],
            'validation': ['validate', 'schema', 'required', 'optional', 'check'],
            'error_handling': ['try:', 'except:', 'raise', 'error', 'exception'],
            'logging': ['logger', 'log.', 'print(', 'debug', 'info', 'warning', 'error'],
            'testing': ['assert', 'test_', 'mock', 'fixture', 'should', 'expect'],
            'authentication': ['auth', 'login', 'token', 'jwt', 'session', 'password'],
            'async': ['async', 'await', 'promise', 'callback'],
            'configuration': ['config', 'settings', 'env', 'constant', 'parameter']
        }

        for pattern_name, keywords in pattern_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                patterns.append(pattern_name)

        return patterns

    def _analyze_diff_content_enhanced(self, diff_content: str, files: List[str]) -> Tuple[str, float]:
        if not diff_content:
            return 'chore', 0.3

        diff_lower = diff_content.lower()
        added_lines = diff_content.count('\n+')
        removed_lines = diff_content.count('\n-')

        scores = {commit_type: 0.0 for commit_type in self.commit_patterns.keys()}

        file_analyses = []
        for file_path in files:
            if os.path.exists(file_path):
                try:
                    file_analysis = self._analyze_file_content(file_path, diff_content)
                    file_analyses.append(file_analysis)
                except Exception as e:
                    logger.warning(f"Could not analyze file {file_path}: {e}")

        # Score basé sur les mots-clés
        for commit_type, config in self.commit_patterns.items():
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in diff_lower)
            scores[commit_type] += keyword_matches * config['weight'] * 0.3

        all_patterns = []
        for analysis in file_analyses:
            all_patterns.extend(analysis.patterns)

        pattern_scores = {
            'api_endpoint': ['feat', 'update'],
            'database': ['feat', 'update', 'fix'],
            'error_handling': ['fix', 'refactor'],
            'testing': ['test'],
            'authentication': ['feat', 'security'],
            'configuration': ['chore', 'update'],
            'middleware': ['feat', 'refactor'],
            'validation': ['feat', 'fix']
        }

        for pattern in all_patterns:
            if pattern in pattern_scores:
                for commit_type in pattern_scores[pattern]:
                    scores[commit_type] += 0.4

        if removed_lines > added_lines * 1.5:
            scores['remove'] += 0.5
        elif added_lines > removed_lines * 2 and added_lines > 5:
            scores['feat'] += 0.3
        elif added_lines > 0 and removed_lines > 0:
            scores['refactor'] += 0.2

        # Score basé sur les types de fichiers
        for analysis in file_analyses:
            if 'test' in analysis.language or any('test' in f for f in files):
                scores['test'] += 0.6
            if any(f.endswith(('.md', '.txt', '.rst')) for f in files):
                scores['docs'] += 0.7
            if any('config' in f.lower() or f.endswith(('.json', '.yml', '.yaml', '.toml')) for f in files):
                scores['chore'] += 0.5

        # Déterminer le meilleur score
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type], 1.0)

        return best_type, confidence

    def _detect_breaking_changes(self, diff_content: str, file_analyses: List[FileAnalysis]) -> bool:
        """Détecte les breaking changes."""
        breaking_indicators = [
            'breaking change', 'removed function', 'deleted class',
            'changed signature', 'deprecated', 'renamed class',
            'removed parameter', 'changed return type'
        ]

        content_lower = diff_content.lower()

        # Vérifier les indicateurs textuels
        if any(indicator in content_lower for indicator in breaking_indicators):
            return True

        # Vérifier si des fonctions/classes importantes ont été supprimées
        removed_lines = [line[1:] for line in diff_content.split('\n') if line.startswith('-')]
        removed_content = '\n'.join(removed_lines)

        # Détecter suppression de fonctions publiques
        public_function_patterns = [
            r'-\s*def\s+(?!_)(\w+)',  # Fonctions publiques Python
            r'-\s*export\s+(?:function|class)\s+(\w+)',  # Exports JavaScript
            r'-\s*public\s+\w+\s+(\w+)'  # Méthodes publiques
        ]

        for pattern in public_function_patterns:
            if re.search(pattern, removed_content, re.MULTILINE):
                return True

        return False

    def _calculate_confidence_score(self, analysis: Dict, file_analyses: List[FileAnalysis]) -> float:
        """Calcule un score de confiance pour la détection."""
        base_confidence = analysis.get('base_confidence', 0.5)

        # Bonus pour cohérence avec les fichiers
        file_bonus = 0.0
        commit_type = analysis['commit_type']

        if commit_type == 'test' and any('test' in f for f in analysis['files_modified']):
            file_bonus += 0.3
        elif commit_type == 'docs' and any(f.endswith(('.md', '.txt')) for f in analysis['files_modified']):
            file_bonus += 0.3
        elif commit_type == 'feat' and any(fa.functions_added or fa.classes_added for fa in file_analyses):
            file_bonus += 0.2

        # Bonus pour patterns détectés
        pattern_bonus = len(set().union(*[fa.patterns for fa in file_analyses])) * 0.1

        # Bonus pour cohérence des mots-clés
        keyword_bonus = 0.0
        if any(kw in analysis['diff_content'].lower()
               for kw in self.commit_patterns[commit_type]['keywords']):
            keyword_bonus = 0.2

        final_confidence = min(base_confidence + file_bonus + pattern_bonus + keyword_bonus, 1.0)
        return final_confidence

    def analyze_changes(self, repo) -> Dict:
        """Analyse améliorée des changements."""
        try:
            # Obtenir les informations de base
            diff = repo.git.diff('HEAD')
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            new_files = repo.untracked_files
            all_files = staged_files + new_files

            # Analyser le contenu
            file_analyses = []
            for file_path in all_files[:10]:  # Limiter à 10 fichiers pour les performances
                try:
                    file_analysis = self._analyze_file_content(file_path, diff)
                    file_analyses.append(file_analysis)
                except Exception as e:
                    logger.warning(f"Could not analyze {file_path}: {e}")

            # Déterminer le type de commit avec confiance
            commit_type, base_confidence = self._analyze_diff_content_enhanced(diff, all_files)

            # Détecter les breaking changes
            breaking_change = self._detect_breaking_changes(diff, file_analyses)

            # Déterminer le scope
            scope = self._determine_scope(all_files, file_analyses)

            # Construire l'analyse finale
            analysis = {
                'files_modified': staged_files,
                'files_added': new_files,
                'commit_type': commit_type,
                'scope': scope,
                'breaking_change': breaking_change,
                'diff_content': diff,
                'file_analyses': file_analyses,
                'base_confidence': base_confidence,
                'patterns_detected': list(set().union(*[fa.patterns for fa in file_analyses])),
                'languages_involved': list(set(fa.language for fa in file_analyses)),
                'complexity_score': sum(fa.lines_complexity for fa in file_analyses)
            }

            # Calculer le score de confiance final
            analysis['confidence'] = self._calculate_confidence_score(analysis, file_analyses)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing changes: {e}")
            return {
                'commit_type': 'chore',
                'scope': '',
                'breaking_change': False,
                'diff_content': '',
                'confidence': 0.3,
                'file_analyses': [],
                'patterns_detected': [],
                'languages_involved': ['general'],
                'complexity_score': 0
            }

    def _determine_scope(self, files: List[str], file_analyses: List[FileAnalysis]) -> str:
        """Détermine le scope du commit de manière intelligente."""
        if not files:
            return ''

        # Essayer de trouver un dossier commun
        try:
            dirs = [os.path.dirname(f) for f in files if f and os.path.dirname(f)]
            if dirs:
                common_path = os.path.commonpath(dirs)
                if common_path and common_path != '.':
                    scope_name = os.path.basename(common_path)
                    return f"({scope_name})"
        except ValueError:
            pass

        # Scope basé sur les patterns détectés
        all_patterns = set().union(*[fa.patterns for fa in file_analyses])
        if 'api_endpoint' in all_patterns:
            return '(api)'
        elif 'database' in all_patterns:
            return '(db)'
        elif 'authentication' in all_patterns:
            return '(auth)'
        elif 'testing' in all_patterns:
            return '(tests)'
        elif 'configuration' in all_patterns:
            return '(config)'

        # Scope basé sur les types de fichiers
        languages = set(fa.language for fa in file_analyses)
        if len(languages) == 1:
            lang = list(languages)[0]
            if lang != 'general':
                return f"({lang})"

        return ''

    def _build_enhanced_prompt(self, analysis: Dict) -> str:
        """Construit un prompt avancé pour l'IA."""
        file_analyses = analysis.get('file_analyses', [])

        # Extraire les informations clés
        functions_added = []
        classes_added = []
        imports_added = []

        for fa in file_analyses:
            functions_added.extend(fa.functions_added[:2])  # Limiter pour éviter des prompts trop longs
            classes_added.extend(fa.classes_added[:2])
            imports_added.extend(fa.imports_added[:3])

        commit_type = analysis['commit_type']
        emoji = self.commit_patterns[commit_type]['emoji']
        confidence = analysis.get('confidence', 0.5)
        patterns = analysis.get('patterns_detected', [])

        prompt = f"""Tu es un expert Git qui génère des messages de commit précis et professionnels.

CONTEXTE TECHNIQUE:
- Type détecté: {commit_type} (confiance: {confidence:.1%})
- Scope: {analysis['scope']}
- Complexité: {analysis.get('complexity_score', 0)} lignes modifiées
- Langages: {', '.join(analysis.get('languages_involved', ['general']))}
- Breaking change: {'Oui' if analysis['breaking_change'] else 'Non'}

ANALYSE SÉMANTIQUE:
- Patterns détectés: {', '.join(patterns[:3]) if patterns else 'aucun'}
- Nouvelles fonctions: {', '.join(functions_added[:3]) if functions_added else 'aucune'}
- Nouvelles classes: {', '.join(classes_added[:2]) if classes_added else 'aucune'}
- Nouveaux imports: {', '.join(imports_added[:3]) if imports_added else 'aucun'}

FICHIERS MODIFIÉS:
- Modifiés: {', '.join(analysis['files_modified'][:3])}
- Ajoutés: {', '.join(analysis['files_added'][:3])}

DIFF CRITIQUE (800 premiers caractères):
{analysis['diff_content'][:800]}

CONTRAINTES STRICTES:
1. Format EXACT: {emoji} {commit_type}{analysis['scope']}: description
2. Maximum 72 caractères TOTAL
3. Langue: {self.config.get('language', 'français')}
4. Verbe à l'impératif présent
5. Sois TRÈS spécifique sur l'action réalisée
6. Utilise le vocabulaire technique approprié

EXEMPLES EXCELLENTS par type:
- ✨ feat(auth): implement JWT token validation middleware
- 🐛 fix(api): resolve null pointer in user service  
- ♻️ refactor(db): extract query builder to separate class
- ⚡ perf(cache): optimize Redis connection pooling
- 🧪 test(user): add unit tests for registration flow

INSTRUCTIONS FINALES:
- Concentre-toi sur l'impact métier ou technique principal
- Évite les mots génériques comme "modifications", "updates"
- Privilégie l'action concrète réalisée
- Si plusieurs actions, choisis la plus importante

Génère UN SEUL message de commit optimal:"""

        return prompt

    def _generate_with_ai(self, analysis: Dict, model: str) -> str:
        """Génère le message avec l'IA."""
        headers = {
            "Authorization": f"Bearer {self.config['openrouter_api_key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.get('site_url', ''),
            "X-Title": self.config.get('site_name', ''),
        }

        prompt = self._build_enhanced_prompt(analysis)
        commit_type = analysis['commit_type']
        emoji = self.commit_patterns[commit_type]['emoji']

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": f"Tu es un expert Git. Utilise TOUJOURS le type '{commit_type}' avec l'emoji '{emoji}'. Respecte le format exact et la limite de 72 caractères."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.1,  # Plus bas pour plus de cohérence
            "top_p": 0.9
        }

        start_time = datetime.now()
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=15
        )
        generation_time = (datetime.now() - start_time).total_seconds()

        response.raise_for_status()
        commit_message = response.json()["choices"][0]["message"]["content"].strip()

        # Nettoyage et validation du message
        commit_message = self._clean_and_validate_message(commit_message, analysis)

        # Enregistrer les métriques
        self._track_generation_metrics(analysis, commit_message, model, generation_time, True)

        return commit_message

    def _clean_and_validate_message(self, message: str, analysis: Dict) -> str:
        """Nettoie et valide le message généré."""
        commit_type = analysis['commit_type']
        emoji = self.commit_patterns[commit_type]['emoji']
        scope = analysis['scope']

        # Nettoyage de base
        message = message.replace('Commit message:', '').strip()
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]

        # Vérifier le format
        expected_start = f"{emoji} {commit_type}{scope}:"
        if not message.startswith(emoji):
            # Reconstruire le message avec le bon format
            if ':' in message:
                description = message.split(':', 1)[-1].strip()
            else:
                description = message.strip()
            message = f"{expected_start} {description}"

        # Vérifier la longueur
        if len(message) > 72:
            # Tronquer intelligemment
            max_desc_length = 72 - len(expected_start) - 1
            if ':' in message:
                prefix, description = message.split(':', 1)
                description = description.strip()[:max_desc_length].strip()
                message = f"{prefix}: {description}"
            else:
                message = message[:72]

        return message

    def _generate_rule_based_message(self, analysis: Dict) -> str:
        """Génère un message basé sur des règles (fallback)."""
        commit_type = analysis['commit_type']
        emoji = self.commit_patterns[commit_type]['emoji']
        scope = analysis['scope']

        # Messages par défaut intelligents
        default_messages = {
            'feat': 'add new functionality',
            'fix': 'resolve issue',
            'refactor': 'improve code structure',
            'docs': 'update documentation',
            'test': 'add tests',
            'chore': 'update configuration',
            'perf': 'improve performance',
            'security': 'enhance security',
            'update': 'update dependencies',
            'remove': 'remove unused code'
        }

        # Essayer d'être plus spécifique selon les fichiers
        files = analysis.get('files_modified', []) + analysis.get('files_added', [])
        if files:
            file_types = set(os.path.splitext(f)[1] for f in files[:3])
            if '.py' in file_types:
                default_messages[commit_type] += ' in Python modules'
            elif '.js' in file_types or '.ts' in file_types:
                default_messages[commit_type] += ' in JavaScript components'
            elif '.md' in file_types:
                default_messages[commit_type] = 'update documentation files'

        base_message = default_messages.get(commit_type, 'make changes')
        message = f"{emoji} {commit_type}{scope}: {base_message}"

        return message[:72]

    def _track_generation_metrics(self, analysis: Dict, message: str, model: str,
                                  generation_time: float, success: bool):
        """Enregistre les métriques de génération."""
        try:
            metrics = CommitMetrics(
                timestamp=datetime.now(),
                commit_type=analysis['commit_type'],
                confidence=analysis.get('confidence', 0.0),
                message_length=len(message),
                files_count=len(analysis.get('files_modified', [])) + len(analysis.get('files_added', [])),
                success=success,
                model_used=model,
                generation_time=generation_time
            )

            # Sauvegarder dans un fichier de métriques
            metrics_data = {
                'timestamp': metrics.timestamp.isoformat(),
                'commit_type': metrics.commit_type,
                'confidence': metrics.confidence,
                'message_length': metrics.message_length,
                'files_count': metrics.files_count,
                'success': metrics.success,
                'model_used': metrics.model_used,
                'generation_time': metrics.generation_time
            }

            self.file_utils.append_to_metrics_file(metrics_data)

        except Exception as e:
            logger.warning(f"Could not track metrics: {e}")

    def generate_smart_commit_message(self, analysis: Dict) -> str:
        """Version robuste avec fallbacks multiples et cache."""
        start_time = datetime.now()

        # Créer une clé de cache basée sur le contenu
        cache_key = hashlib.md5(
            f"{analysis['commit_type']}{analysis['diff_content'][:500]}".encode()
        ).hexdigest()[:12]

        # Vérifier le cache
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if datetime.now() - cache_entry['timestamp'] < self._cache_expiry:
                logger.info("Using cached commit message")
                return cache_entry['message']

        # Modèles à essayer par ordre de préférence
        models_to_try = [
            self.config.get('model', 'openai/gpt-4o'),
            'openai/gpt-4o-mini',
            'openai/gpt-3.5-turbo',
            'anthropic/claude-3-haiku'
        ]

        # Tentatives avec différents modèles
        for i, model in enumerate(models_to_try):
            try:
                logger.info(f"Attempting generation with model: {model}")
                message = self._generate_with_ai(analysis, model)

                # Validation du message
                if self._validate_commit_message(message, analysis):
                    # Mettre en cache
                    self._cache[cache_key] = {
                        'message': message,
                        'timestamp': datetime.now()
                    }
                    return message
                else:
                    logger.warning(f"Generated message failed validation: {message}")
                    continue

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout with model {model}")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed with model {model}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Generation failed with model {model}: {e}")
                continue

        # Si tous les modèles ont échoué, utiliser les règles
        logger.info("All AI models failed, using rule-based generation")
        message = self._generate_rule_based_message(analysis)

        # Enregistrer l'échec dans les métriques
        generation_time = (datetime.now() - start_time).total_seconds()
        self._track_generation_metrics(analysis, message, 'rule-based', generation_time, False)

        return message

    def _validate_commit_message(self, message: str, analysis: Dict) -> bool:
        """Valide le message généré."""
        if not message or len(message) < 10:
            return False

        commit_type = analysis['commit_type']
        emoji = self.commit_patterns[commit_type]['emoji']

        # Vérifier la présence de l'emoji et du type
        if not message.startswith(emoji):
            return False

        if commit_type not in message:
            return False

        # Vérifier la longueur
        if len(message) > 72:
            return False

        # Vérifier la présence des deux points
        if ':' not in message:
            return False

        return True

    def get_generation_stats(self) -> Dict:
        """Retourne les statistiques de génération."""
        try:
            stats = self.file_utils.load_metrics_stats()
            return {
                'total_generations': stats.get('total', 0),
                'success_rate': stats.get('success_rate', 0.0),
                'avg_confidence': stats.get('avg_confidence', 0.0),
                'most_common_types': stats.get('common_types', []),
                'avg_generation_time': stats.get('avg_time', 0.0)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def optimize_for_project(self, repo) -> Dict:
        """Optimise l'analyseur pour un projet spécifique."""
        try:
            # Analyser l'historique des commits du projet
            commit_history = list(repo.iter_commits(max_count=100))

            # Extraire les patterns de commits existants
            project_patterns = {
                'common_types': Counter(),
                'common_scopes': Counter(),
                'avg_length': 0,
                'emoji_usage': False
            }

            total_length = 0
            for commit in commit_history:
                message = commit.message.strip().split('\n')[0]
                total_length += len(message)

                # Détecter l'utilisation d'emojis
                if any(emoji in message for emoji in [p['emoji'] for p in self.commit_patterns.values()]):
                    project_patterns['emoji_usage'] = True

                # Extraire le type de commit
                for commit_type in self.commit_patterns.keys():
                    if message.startswith(commit_type) or commit_type in message.lower():
                        project_patterns['common_types'][commit_type] += 1
                        break

                # Extraire le scope s'il existe
                scope_match = re.search(r'\(([^)]+)\)', message)
                if scope_match:
                    project_patterns['common_scopes'][scope_match.group(1)] += 1

            if commit_history:
                project_patterns['avg_length'] = total_length // len(commit_history)

            # Ajuster la configuration
            optimization_suggestions = {
                'detected_patterns': project_patterns,
                'suggestions': []
            }

            if not project_patterns['emoji_usage']:
                optimization_suggestions['suggestions'].append('Consider enabling emoji usage')

            most_common_type = project_patterns['common_types'].most_common(1)
            if most_common_type:
                optimization_suggestions['suggestions'].append(
                    f"Most used commit type: {most_common_type[0][0]}"
                )

            return optimization_suggestions

        except Exception as e:
            logger.error(f"Error optimizing for project: {e}")
            return {'error': str(e)}

    def generate_commit_suggestions(self, analysis: Dict, count: int = 3) -> List[str]:
        """Génère plusieurs suggestions de messages de commit."""
        suggestions = []

        # Première suggestion (principale)
        main_suggestion = self.generate_smart_commit_message(analysis)
        suggestions.append(main_suggestion)

        if count > 1:
            # Variations avec différents niveaux de détail
            commit_type = analysis['commit_type']
            emoji = self.commit_patterns[commit_type]['emoji']
            scope = analysis['scope']

            # Version courte
            short_version = f"{emoji} {commit_type}{scope}: quick changes"
            if len(analysis.get('files_modified', [])) == 1:
                filename = os.path.basename(analysis['files_modified'][0])
                short_version = f"{emoji} {commit_type}{scope}: update {filename}"
            suggestions.append(short_version)

            if count > 2:
                # Version détaillée (si place)
                patterns = analysis.get('patterns_detected', [])
                if patterns:
                    detail = patterns[0].replace('_', ' ')
                    detailed_version = f"{emoji} {commit_type}{scope}: improve {detail} handling"
                    suggestions.append(detailed_version[:72])
                else:
                    # Version alternative
                    alt_keywords = self.commit_patterns[commit_type]['keywords']
                    if len(alt_keywords) > 1:
                        alt_action = alt_keywords[1]
                        alt_version = f"{emoji} {commit_type}{scope}: {alt_action} functionality"
                        suggestions.append(alt_version[:72])

        return suggestions[:count]

    def explain_analysis(self, analysis: Dict) -> str:
        """Explique le raisonnement derrière l'analyse."""
        explanation = []

        commit_type = analysis['commit_type']
        confidence = analysis.get('confidence', 0.0)

        explanation.append(f"🔍 Analyse du commit:")
        explanation.append(f"   Type détecté: {commit_type} (confiance: {confidence:.1%})")

        if analysis.get('scope'):
            explanation.append(f"   Scope: {analysis['scope']}")

        if analysis.get('breaking_change'):
            explanation.append("   ⚠️  Breaking change détecté")

        patterns = analysis.get('patterns_detected', [])
        if patterns:
            explanation.append(f"   Patterns: {', '.join(patterns[:3])}")

        complexity = analysis.get('complexity_score', 0)
        if complexity:
            explanation.append(f"   Complexité: {complexity} lignes modifiées")

        files_count = len(analysis.get('files_modified', [])) + len(analysis.get('files_added', []))
        explanation.append(f"   Fichiers affectés: {files_count}")

        # Explication du choix du type
        explanation.append(f"\n💡 Pourquoi '{commit_type}' ?")

        reasons = []
        if patterns:
            if 'api_endpoint' in patterns:
                reasons.append("Détection d'endpoints API")
            if 'testing' in patterns:
                reasons.append("Code de test détecté")
            if 'error_handling' in patterns and commit_type == 'fix':
                reasons.append("Gestion d'erreur améliorée")

        # Analyser les mots-clés dans le diff
        diff_content = analysis.get('diff_content', '').lower()
        matching_keywords = []
        for keyword in self.commit_patterns[commit_type]['keywords']:
            if keyword in diff_content:
                matching_keywords.append(keyword)

        if matching_keywords:
            reasons.append(f"Mots-clés trouvés: {', '.join(matching_keywords[:3])}")

        if reasons:
            explanation.extend([f"   - {reason}" for reason in reasons])
        else:
            explanation.append("   - Analyse heuristique basée sur les fichiers modifiés")

        return '\n'.join(explanation)

    def clear_cache(self):
        """Vide le cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict:
        """Retourne les statistiques du cache."""
        active_entries = 0
        expired_entries = 0

        current_time = datetime.now()
        for entry in self._cache.values():
            if current_time - entry['timestamp'] < self._cache_expiry:
                active_entries += 1
            else:
                expired_entries += 1

        return {
            'total_entries': len(self._cache),
            'active_entries': active_entries,
            'expired_entries': expired_entries,
            'cache_hit_potential': active_entries / max(len(self._cache), 1)
        }