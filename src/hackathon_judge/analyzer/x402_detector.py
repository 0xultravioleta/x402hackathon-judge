"""X402 protocol detector and evaluator."""

import re
from pathlib import Path
from typing import Optional

from hackathon_judge.models import X402Result, Project
from hackathon_judge.fetcher import GitHubAPI


class X402Detector:
    """Detect and evaluate X402 protocol integration."""

    # Patterns indicating X402 usage
    X402_PATTERNS = [
        r'x402',
        r'X402',
        r'status\s*[=:]\s*402',
        r'402\s*Payment',
        r'Payment\s*Required',
        r'X-Payment',
        r'@coinbase/x402',
        r'payment.*protocol',
        r'micropayment',
    ]

    # Patterns for wallet integration
    WALLET_PATTERNS = [
        r'metamask',
        r'walletconnect',
        r'wallet.*adapter',
        r'connect.*wallet',
        r'@solana/wallet',
        r'ethers',
        r'web3',
    ]

    # Patterns for payment verification
    VERIFICATION_PATTERNS = [
        r'verify.*payment',
        r'check.*transaction',
        r'confirm.*transfer',
        r'on.?chain.*verify',
        r'payment.*verified',
    ]

    # Common X402 use case patterns
    USE_CASE_PATTERNS = {
        'api_monetization': [r'pay.*per.*call', r'api.*payment', r'pay.*per.*request'],
        'content_paywall': [r'paywall', r'pay.*to.*access', r'premium.*content'],
        'micropayments': [r'micropayment', r'micro.*transaction', r'small.*payment'],
        'm2m_payments': [r'machine.*to.*machine', r'm2m', r'automated.*payment'],
        'streaming': [r'streaming.*payment', r'pay.*per.*byte', r'pay.*per.*stream'],
    }

    def __init__(self, github_api: GitHubAPI):
        self.api = github_api

    def analyze(self, project_id: str, project: Project,
                local_path: Optional[Path] = None) -> X402Result:
        """Analyze X402 integration in a project."""
        result = X402Result(project_id=project_id)

        try:
            # Use description for initial signals
            if project.description:
                self._analyze_description(result, project.description)

            if local_path and local_path.exists():
                return self._analyze_local(result, local_path, project)
            else:
                return self._analyze_remote(result, project)
        except Exception as e:
            result.error = str(e)
            return result

    def _analyze_description(self, result: X402Result, description: str):
        """Analyze project description for X402 signals."""
        desc_lower = description.lower()

        # Check for X402 mention
        if 'x402' in desc_lower or '402' in desc_lower:
            result.uses_x402 = True

        # Detect use case from description
        for use_case, patterns in self.USE_CASE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, desc_lower):
                    result.use_case = use_case.replace('_', ' ')
                    break

    def _analyze_local(self, result: X402Result, path: Path, project: Project) -> X402Result:
        """Analyze local repository for X402 integration."""
        # Search for X402 patterns in source files
        source_extensions = ['.js', '.ts', '.jsx', '.tsx', '.py', '.rs', '.go', '.sol']
        x402_files = []
        wallet_files = []
        verification_files = []

        for ext in source_extensions:
            for file_path in path.rglob(f'*{ext}'):
                if any(skip in str(file_path) for skip in ['node_modules', '.git', 'dist', 'build']):
                    continue

                try:
                    content = file_path.read_text(errors='replace')
                    content_lower = content.lower()

                    # Check X402 patterns
                    for pattern in self.X402_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            x402_files.append(str(file_path.relative_to(path)))
                            break

                    # Check wallet patterns
                    for pattern in self.WALLET_PATTERNS:
                        if re.search(pattern, content_lower):
                            wallet_files.append(str(file_path.relative_to(path)))
                            break

                    # Check verification patterns
                    for pattern in self.VERIFICATION_PATTERNS:
                        if re.search(pattern, content_lower):
                            verification_files.append(str(file_path.relative_to(path)))
                            break

                except Exception:
                    continue

        # Also check package.json for X402 SDK
        pkg_path = path / 'package.json'
        if pkg_path.exists():
            try:
                content = pkg_path.read_text()
                if '@coinbase/x402' in content or 'x402' in content.lower():
                    result.uses_x402 = True
                    result.creative_elements.append("Uses official X402 SDK")
            except:
                pass

        # Update result based on findings
        result.uses_x402 = len(x402_files) > 0 or result.uses_x402
        result.has_402_handling = '402' in str(x402_files) or any('402' in f for f in x402_files)
        result.has_wallet_integration = len(wallet_files) > 0

        # Determine payment verification type
        if verification_files:
            if any('chain' in f.lower() for f in verification_files):
                result.payment_verification = "onchain"
            else:
                result.payment_verification = "offchain"
        elif result.uses_x402:
            result.payment_verification = "basic"

        # Evaluate integration quality
        result = self._evaluate_integration(result, x402_files, wallet_files, verification_files)

        # Determine use case if not already set
        if not result.use_case:
            result.use_case = self._detect_use_case(path)

        # Assess novelty and innovation
        result = self._assess_innovation(result, path, project)

        return result

    def _analyze_remote(self, result: X402Result, project: Project) -> X402Result:
        """Analyze via GitHub API."""
        import re
        match = re.search(r'github\.com/([^/]+)/([^/\s]+)', project.github_url)
        if not match:
            result.error = f"Could not parse URL: {project.github_url}"
            return result

        owner = match.group(1)
        repo = match.group(2).rstrip('/').replace('.git', '')

        # Check README for X402 mentions
        readme_content = self.api.get_file_content(owner, repo, 'README.md')
        if readme_content:
            for pattern in self.X402_PATTERNS:
                if re.search(pattern, readme_content, re.IGNORECASE):
                    result.uses_x402 = True
                    break

            # Check for use cases
            readme_lower = readme_content.lower()
            for use_case, patterns in self.USE_CASE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, readme_lower):
                        result.use_case = use_case.replace('_', ' ')
                        break

        # Check package.json for X402 SDK
        pkg_content = self.api.get_file_content(owner, repo, 'package.json')
        if pkg_content:
            if '@coinbase/x402' in pkg_content or 'x402' in pkg_content.lower():
                result.uses_x402 = True
                result.creative_elements.append("Uses X402 SDK")

        # Score based on signals
        if result.uses_x402:
            result.integration_score = 5  # Base score for having X402
            if result.use_case:
                result.integration_score += 2
            if '@coinbase/x402' in (pkg_content or ''):
                result.integration_score += 2

            result.payment_necessity = "useful"
            result.economic_viability = "viable"
            result.novelty_score = 5
        else:
            result.integration_score = 0
            result.novelty_score = 0

        return result

    def _evaluate_integration(self, result: X402Result, x402_files: list,
                              wallet_files: list, verification_files: list) -> X402Result:
        """Evaluate the quality of X402 integration."""
        score = 0

        # Basic X402 usage
        if result.uses_x402:
            score += 3

        # Has 402 status handling
        if result.has_402_handling:
            score += 2

        # Has wallet integration
        if result.has_wallet_integration:
            score += 2

        # Has payment verification
        if result.payment_verification == "onchain":
            score += 3
        elif result.payment_verification == "offchain":
            score += 2
        elif result.payment_verification == "basic":
            score += 1

        result.integration_score = min(score, 10)

        # Assess necessity
        if result.use_case in ['api monetization', 'micropayments', 'm2m payments']:
            result.payment_necessity = "essential"
        elif result.use_case in ['content paywall', 'streaming']:
            result.payment_necessity = "useful"
        else:
            result.payment_necessity = "unknown"

        # Economic viability
        if result.has_wallet_integration and result.payment_verification != "missing":
            result.economic_viability = "viable"
        elif result.uses_x402:
            result.economic_viability = "questionable"
        else:
            result.economic_viability = "not_viable"

        return result

    def _detect_use_case(self, path: Path) -> str:
        """Detect the primary use case from code patterns."""
        # Look for API patterns
        api_indicators = ['api', 'endpoint', 'route', 'handler']
        content_indicators = ['article', 'content', 'media', 'paywall']
        payment_indicators = ['pay', 'price', 'cost', 'charge']

        api_count = 0
        content_count = 0

        for ext in ['.js', '.ts', '.py']:
            for f in list(path.rglob(f'*{ext}'))[:20]:
                if 'node_modules' in str(f):
                    continue
                try:
                    content = f.read_text(errors='replace').lower()
                    for ind in api_indicators:
                        api_count += content.count(ind)
                    for ind in content_indicators:
                        content_count += content.count(ind)
                except:
                    pass

        if api_count > content_count * 2:
            return "api monetization"
        elif content_count > api_count:
            return "content paywall"
        else:
            return "general payments"

    def _assess_innovation(self, result: X402Result, path: Path, project: Project) -> X402Result:
        """Assess innovation and novelty."""
        novelty = 3  # Base score

        # Check for innovative elements
        innovative_patterns = [
            (r'streaming.*payment', "Streaming payments"),
            (r'dynamic.*pric', "Dynamic pricing"),
            (r'multi.*party', "Multi-party payments"),
            (r'privacy', "Privacy features"),
            (r'cross.*chain', "Cross-chain support"),
            (r'subscription', "Subscription model"),
            (r'oracle', "Oracle integration"),
            (r'vrf|random', "Verifiable randomness"),
        ]

        # Search in key files
        search_files = [
            path / 'README.md',
            path / 'package.json',
        ]
        search_files.extend(list(path.rglob('*.ts'))[:10])
        search_files.extend(list(path.rglob('*.js'))[:10])

        for f in search_files:
            if not f.exists():
                continue
            try:
                content = f.read_text(errors='replace').lower()
                for pattern, label in innovative_patterns:
                    if re.search(pattern, content):
                        if label not in result.creative_elements:
                            result.creative_elements.append(label)
                            novelty += 1
            except:
                pass

        # Cap novelty score
        result.novelty_score = min(novelty, 10)

        # Add concerns if no real innovation
        if result.novelty_score < 4:
            result.concerns.append("Basic implementation without significant innovation")

        if not result.uses_x402:
            result.concerns.append("No clear X402 protocol integration found")

        return result
