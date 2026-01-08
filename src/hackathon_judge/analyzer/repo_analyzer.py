"""Repository structure and quality analyzer."""

import os
import re
from pathlib import Path
from typing import Optional

from hackathon_judge.models import AnalysisResult, RepoMetadata
from hackathon_judge.fetcher import GitHubAPI


class RepoAnalyzer:
    """Analyze repository structure, tech stack, and quality signals."""

    # File patterns for detection
    FRAMEWORK_PATTERNS = {
        'react': [r'react', r'"react":', r"'react':"],
        'nextjs': [r'next', r'"next":', r"'next':"],
        'vue': [r'vue', r'"vue":', r"'vue':"],
        'angular': [r'@angular', r'"@angular/'],
        'express': [r'express', r'"express":'],
        'fastapi': [r'fastapi', r'from fastapi'],
        'django': [r'django', r'from django'],
        'flask': [r'flask', r'from flask'],
        'solana': [r'@solana', r'solana-web3', r'anchor'],
        'ethereum': [r'ethers', r'web3', r'hardhat', r'foundry'],
    }

    LANGUAGE_FILES = {
        'javascript': ['package.json', '.js', '.jsx'],
        'typescript': ['tsconfig.json', '.ts', '.tsx'],
        'python': ['requirements.txt', 'pyproject.toml', 'setup.py', '.py'],
        'rust': ['Cargo.toml', '.rs'],
        'go': ['go.mod', '.go'],
        'solidity': ['.sol'],
        'kotlin': ['.kt', 'build.gradle.kts'],
        'java': ['.java', 'pom.xml', 'build.gradle'],
    }

    DEPLOYMENT_CONFIGS = {
        'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
        'vercel': ['vercel.json', '.vercel'],
        'netlify': ['netlify.toml'],
        'kubernetes': ['k8s/', 'kubernetes/', '.yaml'],
        'railway': ['railway.toml'],
        'render': ['render.yaml'],
    }

    def __init__(self, github_api: GitHubAPI):
        self.api = github_api

    def analyze(self, project_id: str, github_url: str,
                metadata: Optional[RepoMetadata] = None,
                local_path: Optional[Path] = None) -> AnalysisResult:
        """Analyze a repository."""
        result = AnalysisResult(project_id=project_id)

        try:
            if local_path and local_path.exists():
                return self._analyze_local(result, local_path, metadata)
            else:
                return self._analyze_remote(result, github_url, metadata)
        except Exception as e:
            result.error = str(e)
            return result

    def _analyze_local(self, result: AnalysisResult, path: Path,
                       metadata: Optional[RepoMetadata]) -> AnalysisResult:
        """Analyze a locally cloned repository."""
        # Detect languages
        result.languages = self._detect_languages_local(path)

        # Detect frameworks from package files
        result.frameworks = self._detect_frameworks_local(path)

        # Check README
        readme_path = self._find_readme(path)
        if readme_path:
            result.has_readme = True
            result.readme_quality = self._evaluate_readme(readme_path)
        else:
            result.readme_quality = 0

        # Check for tests
        result.has_tests, result.test_coverage_estimate = self._detect_tests_local(path)

        # Check for demo URL in README
        if readme_path:
            demo_url = self._extract_demo_url(readme_path)
            if demo_url:
                result.has_demo = True
                result.demo_url = demo_url

        # Check deployment config
        result.has_deployment_config, result.deployment_target = self._detect_deployment_local(path)

        # Evaluate code quality signals
        result.code_quality_signals = self._evaluate_quality_signals_local(path)

        # Determine architecture
        result.architecture = self._detect_architecture_local(path)

        # Add notable findings
        result.notable_findings = self._gather_findings(result)

        return result

    def _analyze_remote(self, result: AnalysisResult, github_url: str,
                        metadata: Optional[RepoMetadata]) -> AnalysisResult:
        """Analyze via GitHub API (without cloning)."""
        if metadata and not metadata.is_accessible:
            result.error = metadata.error
            return result

        # Parse URL
        import re
        match = re.search(r'github\.com/([^/]+)/([^/\s]+)', github_url)
        if not match:
            result.error = f"Could not parse URL: {github_url}"
            return result

        owner = match.group(1)
        repo = match.group(2).rstrip('/').replace('.git', '')

        # Get languages
        languages = self.api.get_languages(owner, repo)
        result.languages = list(languages.keys())

        # Get root contents
        contents = self.api.get_repo_contents(owner, repo)
        if not contents:
            result.error = "Could not fetch repository contents"
            return result

        file_names = [item.get('name', '') for item in contents if isinstance(item, dict)]

        # Check README
        for name in file_names:
            if name.lower().startswith('readme'):
                result.has_readme = True
                readme_content = self.api.get_file_content(owner, repo, name)
                if readme_content:
                    result.readme_quality = self._evaluate_readme_content(readme_content)
                    demo_url = self._extract_demo_url_from_content(readme_content)
                    if demo_url:
                        result.has_demo = True
                        result.demo_url = demo_url
                break

        # Detect frameworks from package.json
        if 'package.json' in file_names:
            pkg_content = self.api.get_file_content(owner, repo, 'package.json')
            if pkg_content:
                result.frameworks = self._detect_frameworks_from_content(pkg_content)

        # Check for tests
        test_dirs = ['test', 'tests', '__tests__', 'spec']
        for name in file_names:
            if name.lower() in test_dirs:
                result.has_tests = True
                result.test_coverage_estimate = "low"
                break

        # Check deployment config
        for target, patterns in self.DEPLOYMENT_CONFIGS.items():
            for pattern in patterns:
                if pattern in file_names:
                    result.has_deployment_config = True
                    result.deployment_target = target
                    break

        # Basic quality signals
        result.code_quality_signals = {
            'linting': any(f in file_names for f in ['.eslintrc', '.eslintrc.js', '.eslintrc.json', 'eslint.config.js']),
            'formatting': any(f in file_names for f in ['.prettierrc', '.prettierrc.js', 'prettier.config.js']),
            'error_handling': 'adequate',
            'documentation': 'adequate' if result.readme_quality >= 5 else 'poor',
        }

        result.architecture = self._guess_architecture(file_names, result.frameworks)
        result.notable_findings = self._gather_findings(result)

        return result

    def _detect_languages_local(self, path: Path) -> list[str]:
        """Detect languages from local files."""
        languages = set()

        for lang, patterns in self.LANGUAGE_FILES.items():
            for pattern in patterns:
                if pattern.startswith('.'):
                    # File extension
                    if list(path.rglob(f'*{pattern}'))[:1]:
                        languages.add(lang)
                else:
                    # Specific file
                    if (path / pattern).exists():
                        languages.add(lang)

        return list(languages)

    def _detect_frameworks_local(self, path: Path) -> list[str]:
        """Detect frameworks from local package files."""
        frameworks = set()

        # Check package.json
        pkg_path = path / 'package.json'
        if pkg_path.exists():
            try:
                content = pkg_path.read_text()
                frameworks.update(self._detect_frameworks_from_content(content))
            except:
                pass

        # Check requirements.txt
        req_path = path / 'requirements.txt'
        if req_path.exists():
            try:
                content = req_path.read_text().lower()
                if 'fastapi' in content:
                    frameworks.add('fastapi')
                if 'django' in content:
                    frameworks.add('django')
                if 'flask' in content:
                    frameworks.add('flask')
            except:
                pass

        # Check Cargo.toml for Rust frameworks
        cargo_path = path / 'Cargo.toml'
        if cargo_path.exists():
            try:
                content = cargo_path.read_text().lower()
                if 'actix' in content:
                    frameworks.add('actix')
                if 'anchor' in content:
                    frameworks.add('anchor')
            except:
                pass

        return list(frameworks)

    def _detect_frameworks_from_content(self, content: str) -> list[str]:
        """Detect frameworks from package.json content."""
        frameworks = set()
        content_lower = content.lower()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    frameworks.add(framework)
                    break

        return list(frameworks)

    def _find_readme(self, path: Path) -> Optional[Path]:
        """Find README file in repository."""
        for name in ['README.md', 'README.MD', 'readme.md', 'README', 'Readme.md']:
            readme = path / name
            if readme.exists():
                return readme
        return None

    def _evaluate_readme(self, readme_path: Path) -> int:
        """Evaluate README quality (1-10)."""
        try:
            content = readme_path.read_text()
            return self._evaluate_readme_content(content)
        except:
            return 0

    def _evaluate_readme_content(self, content: str) -> int:
        """Evaluate README content quality."""
        score = 0

        # Length check
        if len(content) > 500:
            score += 2
        elif len(content) > 200:
            score += 1

        # Has headings
        if re.search(r'^#+\s', content, re.MULTILINE):
            score += 1

        # Has code blocks
        if '```' in content:
            score += 1

        # Has installation/setup instructions
        if re.search(r'(install|setup|getting started|quick start)', content, re.IGNORECASE):
            score += 1

        # Has screenshots/images
        if re.search(r'!\[.*\]\(.*\)', content):
            score += 1

        # Has links
        if re.search(r'\[.*\]\(http', content):
            score += 1

        # Has description section
        if re.search(r'(description|about|overview|what is)', content, re.IGNORECASE):
            score += 1

        # Has usage examples
        if re.search(r'(usage|example|how to)', content, re.IGNORECASE):
            score += 1

        # Has license mention
        if re.search(r'license', content, re.IGNORECASE):
            score += 1

        return min(score, 10)

    def _extract_demo_url(self, readme_path: Path) -> Optional[str]:
        """Extract demo URL from README."""
        try:
            content = readme_path.read_text()
            return self._extract_demo_url_from_content(content)
        except:
            return None

    def _extract_demo_url_from_content(self, content: str) -> Optional[str]:
        """Extract demo URL from README content."""
        # Look for demo patterns
        patterns = [
            r'demo[:\s]+\[?([^\]\s]+)\]?\s*\(?([^\)]+)\)?',
            r'live[:\s]+\[?([^\]\s]+)\]?\s*\(?([^\)]+)\)?',
            r'deployed at[:\s]+\[?([^\]\s]+)\]?\s*\(?([^\)]+)\)?',
            r'\[demo\]\((https?://[^\)]+)\)',
            r'\[live\]\((https?://[^\)]+)\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Return the URL (last group typically has the actual URL)
                groups = match.groups()
                for g in reversed(groups):
                    if g and g.startswith('http'):
                        return g
                return groups[-1] if groups else None

        return None

    def _detect_tests_local(self, path: Path) -> tuple[bool, str]:
        """Detect tests and estimate coverage."""
        test_dirs = ['test', 'tests', '__tests__', 'spec']
        test_files = list(path.rglob('*test*.py')) + list(path.rglob('*.test.js')) + \
                     list(path.rglob('*.spec.js')) + list(path.rglob('*test*.ts'))

        has_tests = False
        coverage = "none"

        for td in test_dirs:
            if (path / td).exists():
                has_tests = True
                break

        if test_files:
            has_tests = True
            if len(test_files) > 10:
                coverage = "high"
            elif len(test_files) > 5:
                coverage = "medium"
            else:
                coverage = "low"

        return has_tests, coverage

    def _detect_deployment_local(self, path: Path) -> tuple[bool, Optional[str]]:
        """Detect deployment configuration."""
        for target, patterns in self.DEPLOYMENT_CONFIGS.items():
            for pattern in patterns:
                if '/' in pattern:
                    if (path / pattern.rstrip('/')).is_dir():
                        return True, target
                else:
                    if (path / pattern).exists():
                        return True, target

        return False, None

    def _evaluate_quality_signals_local(self, path: Path) -> dict:
        """Evaluate code quality signals."""
        signals = {
            'linting': False,
            'formatting': False,
            'error_handling': 'poor',
            'documentation': 'poor',
        }

        # Check for linting config
        lint_files = ['.eslintrc', '.eslintrc.js', '.eslintrc.json', 'eslint.config.js', '.pylintrc', 'ruff.toml']
        for lf in lint_files:
            if (path / lf).exists():
                signals['linting'] = True
                break

        # Check for formatting config
        format_files = ['.prettierrc', '.prettierrc.js', 'prettier.config.js', 'pyproject.toml', '.editorconfig']
        for ff in format_files:
            if (path / ff).exists():
                signals['formatting'] = True
                break

        # Error handling - check for try/catch patterns
        try:
            sample_files = list(path.rglob('*.py'))[:5] + list(path.rglob('*.js'))[:5] + list(path.rglob('*.ts'))[:5]
            error_patterns = 0
            for sf in sample_files:
                try:
                    content = sf.read_text()
                    if 'try' in content and ('catch' in content or 'except' in content):
                        error_patterns += 1
                except:
                    pass
            if error_patterns >= 3:
                signals['error_handling'] = 'good'
            elif error_patterns >= 1:
                signals['error_handling'] = 'adequate'
        except:
            pass

        # Documentation check
        readme = self._find_readme(path)
        if readme:
            quality = self._evaluate_readme(readme)
            if quality >= 7:
                signals['documentation'] = 'good'
            elif quality >= 4:
                signals['documentation'] = 'adequate'

        return signals

    def _detect_architecture_local(self, path: Path) -> str:
        """Detect project architecture."""
        dirs = [d.name for d in path.iterdir() if d.is_dir() and not d.name.startswith('.')]

        if 'frontend' in dirs and 'backend' in dirs:
            return 'frontend/backend split'
        if 'client' in dirs and 'server' in dirs:
            return 'client/server split'
        if 'src' in dirs:
            if (path / 'src' / 'components').exists():
                return 'frontend SPA'
            return 'monolith'
        if 'packages' in dirs or 'apps' in dirs:
            return 'monorepo'
        if 'services' in dirs:
            return 'microservices'

        return 'monolith'

    def _guess_architecture(self, file_names: list[str], frameworks: list[str]) -> str:
        """Guess architecture from file names and frameworks."""
        if 'frontend' in file_names and 'backend' in file_names:
            return 'frontend/backend split'
        if 'client' in file_names and 'server' in file_names:
            return 'client/server split'
        if 'packages' in file_names or 'apps' in file_names:
            return 'monorepo'
        if 'nextjs' in frameworks or 'react' in frameworks:
            return 'frontend SPA'

        return 'monolith'

    def _gather_findings(self, result: AnalysisResult) -> list[str]:
        """Gather notable findings."""
        findings = []

        if result.has_demo and result.demo_url:
            findings.append(f"Live demo available at {result.demo_url}")

        if result.has_deployment_config:
            findings.append(f"Has deployment config for {result.deployment_target}")

        if 'solana' in result.frameworks or 'anchor' in result.frameworks:
            findings.append("Uses Solana/Anchor for blockchain")

        if 'ethereum' in result.frameworks:
            findings.append("Uses Ethereum/Web3")

        if result.has_tests and result.test_coverage_estimate in ['medium', 'high']:
            findings.append(f"Good test coverage ({result.test_coverage_estimate})")

        if result.code_quality_signals.get('linting') and result.code_quality_signals.get('formatting'):
            findings.append("Well-configured with linting and formatting")

        return findings
