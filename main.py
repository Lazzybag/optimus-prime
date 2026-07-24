#!/usr/bin/env python3
"""
Liquid Staking Protocol Discovery Bot
Research Tool for Analyzing Liquid Staking Protocol Architecture

Objective: Extract and categorize contract addresses from liquid staking
protocol adapters by directly querying the DefiLlama-Adapters GitHub repository.
This approach bypasses API limitations by using GitHub API directly.

Data Source: DefiLlama-Adapters GitHub Repository (/projects directory)
Author: Lazzybag
Version: 2.0.0
"""

import os
import sys
import json
import csv
import re
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_PAT = os.getenv('GITHUB_PAT')
GITHUB_API_BASE = "https://api.github.com"
DEFILLLAMA_ADAPTERS_REPO = "DefiLlama/DefiLlama-Adapters"
PROJECTS_DIR = "projects"

# Liquid Staking Keywords for Protocol Identification
LIQUID_STAKING_KEYWORDS = [
    'liquid', 'stake', 'staking', 'liquid-staking', 'lstake',
    'lsd', 'derivative', 'eth2', 'beacon', 'consensus',
    'wrapped', 'beacon-chain', 'restake', 'restaking'
]

# Regex patterns for contract address extraction
ADDRESS_PATTERNS = {
    'ethereum': r'0x[a-fA-F0-9]{40}',  # Ethereum addresses
    'solana': r'[1-9A-HJ-NP-Z]{43,44}',  # Solana addresses
}

# Contract categorization keywords
CONTRACT_CATEGORIES = {
    'reward': [
        'reward', 'claim', 'distribute', 'emission', 'incentive',
        'staking_reward', 'yield', 'earning', 'apy', 'interest'
    ],
    'withdrawal': [
        'withdraw', 'redeem', 'unstake', 'exit', 'claim_withdraw',
        'burn', 'unwrap', 'exchange', 'swap', 'exit'
    ],
    'treasury': [
        'treasury', 'admin', 'operations', 'operational', 'vault',
        'reserve', 'fund', 'multisig', 'dao_treasury', 'pool'
    ],
    'governance': [
        'governance', 'voting', 'vote', 'proposal', 'dao', 'token',
        'delegate', 'snapshot', 'voting_escrow'
    ],
    'staking': [
        'staking', 'stake', 'deposit', 'validator', 'node'
    ]
}


@dataclass
class ContractAddress:
    """Represents an extracted contract address with metadata"""
    address: str
    chain: str
    category: Optional[str] = None
    context: Optional[str] = None
    confidence: float = 0.5

    def to_dict(self):
        return asdict(self)


@dataclass
class ProtocolAnalysis:
    """Represents the complete analysis of a protocol"""
    protocol_name: str
    protocol_slug: str
    chains: List[str]
    reward_addresses: List[str]
    withdrawal_addresses: List[str]
    treasury_addresses: List[str]
    governance_addresses: List[str]
    staking_addresses: List[str]
    total_addresses: int
    adapter_url: str
    extraction_timestamp: str
    code_length: int
    notes: str = ""

    def to_dict(self):
        return asdict(self)


class RateLimitTracker:
    """Tracks GitHub API rate limits"""
    def __init__(self):
        self.remaining = 5000
        self.reset_time = None
        self.total_requests = 0

    def update(self, headers: Dict):
        """Update rate limit info from response headers"""
        self.remaining = int(headers.get('X-RateLimit-Remaining', 5000))
        self.reset_time = int(headers.get('X-RateLimit-Reset', 0))
        self.total_requests += 1

    def display(self):
        """Display current rate limit status"""
        if self.reset_time:
            reset_dt = datetime.fromtimestamp(self.reset_time)
            print(f"\n📊 Rate Limit Status:")
            print(f"   Remaining Requests: {self.remaining}")
            print(f"   Total Requests Made: {self.total_requests}")
            print(f"   Reset Time: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n📊 Total Requests Made: {self.total_requests}")

    def check_limit(self):
        """Check if rate limit is critically low"""
        if self.remaining < 100:
            print(f"⚠️  WARNING: Only {self.remaining} API requests remaining!")
            return False
        return True


class LiquidStakingDiscoveryBot:
    """Main bot for discovering and analyzing liquid staking protocols"""

    def __init__(self):
        if not GITHUB_PAT:
            raise ValueError(
                "❌ GITHUB_PAT environment variable not set. "
                "Please add it to your .env file."
            )
        self.github_token = GITHUB_PAT
        self.session = self._create_session()
        self.rate_limiter = RateLimitTracker()
        self.protocols: List[ProtocolAnalysis] = []
        self.discovered_protocols: Set[str] = set()

    def _create_session(self) -> requests.Session:
        """Create a requests session with authentication"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'LiquidStakingDiscoveryBot/2.0'
        })
        return session

    def _make_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, timeout=timeout)
            self.rate_limiter.update(response.headers)

            if response.status_code == 404:
                return None
            elif response.status_code == 403:
                print(f"   ❌ Rate limit or access denied: {url}")
                return None
            elif response.status_code >= 400:
                print(f"   ❌ HTTP {response.status_code}: {url}")
                return None

            return response
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request error: {str(e)}")
            return None

    def discover_protocols(self) -> List[str]:
        """Discover all protocols in /projects directory"""
        print("\n🔍 Discovering protocols from DefiLlama-Adapters repository...")
        
        url = f"{GITHUB_API_BASE}/repos/{DEFILLLAMA_ADAPTERS_REPO}/contents/{PROJECTS_DIR}"
        response = self._make_request(url)
        
        if not response:
            print("❌ Failed to fetch projects directory")
            return []

        try:
            items = response.json()
            protocols = [
                item['name'] for item in items
                if item['type'] == 'dir' and not item['name'].startswith('.')
            ]
            print(f"✅ Found {len(protocols)} total projects in /projects directory")
            return sorted(protocols)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing response: {str(e)}")
            return []

    def is_liquid_staking_protocol(self, protocol_name: str, adapter_code: str) -> bool:
        """Determine if a protocol is liquid staking related"""
        protocol_lower = protocol_name.lower()
        code_lower = adapter_code.lower()
        
        # Check protocol name
        for keyword in LIQUID_STAKING_KEYWORDS:
            if keyword in protocol_lower:
                return True
        
        # Check adapter code content
        liquid_staking_indicators = [
            'liquid staking', 'lsd', 'lst', 'beacon', 'validator',
            'staking derivative', 'liquid stake', 'eth2', 'restaking'
        ]
        
        for indicator in liquid_staking_indicators:
            if indicator in code_lower:
                return True
        
        return False

    def fetch_adapter_file(self, protocol_slug: str) -> Optional[Tuple[str, str]]:
        """Fetch adapter file from a protocol's directory"""
        # Try different possible paths
        possible_paths = [
            f"{PROJECTS_DIR}/{protocol_slug}/index.js",
            f"{PROJECTS_DIR}/{protocol_slug}/index.ts",
            f"{PROJECTS_DIR}/{protocol_slug}/index.json",
        ]

        for path in possible_paths:
            url = f"{GITHUB_API_BASE}/repos/{DEFILLLAMA_ADAPTERS_REPO}/contents/{path}"
            response = self._make_request(url)

            if response and response.status_code == 200:
                try:
                    content_data = response.json()
                    # Handle base64 encoded content
                    if 'content' in content_data:
                        import base64
                        content = base64.b64decode(content_data['content']).decode('utf-8')
                        return path, content
                except Exception as e:
                    print(f"   ⚠️  Error decoding {path}: {str(e)}")
                    continue

        return None

    def extract_contract_addresses(self, code: str, protocol_name: str) -> Dict[str, List[str]]:
        """Extract contract addresses from adapter code"""
        addresses_by_category = {
            'reward': [],
            'withdrawal': [],
            'treasury': [],
            'governance': [],
            'staking': [],
            'other': []
        }

        # Extract all Ethereum addresses
        ethereum_pattern = ADDRESS_PATTERNS['ethereum']
        matches = list(re.finditer(ethereum_pattern, code))

        # Track unique addresses to avoid duplicates
        seen_addresses = set()

        for match in matches:
            address = match.group(0)
            
            # Skip if we've already categorized this address
            if address in seen_addresses:
                continue
            seen_addresses.add(address)

            # Get surrounding context
            start = max(0, match.start() - 200)
            end = min(len(code), match.end() + 200)
            context = code[start:end].lower()

            # Categorize address
            category = self._categorize_address(context)
            addresses_by_category[category].append(address)

        return addresses_by_category

    def _categorize_address(self, context: str) -> str:
        """Categorize address based on surrounding context"""
        for category, keywords in CONTRACT_CATEGORIES.items():
            if any(keyword in context for keyword in keywords):
                return category
        return 'other'

    def extract_chains(self, adapter_code: str) -> List[str]:
        """Extract chain names from adapter code"""
        chains = set()
        
        # Common chain identifiers in adapter code
        chain_patterns = {
            'ethereum': [r'ethereum', r'eth:', r'\'ethereum\'', r'"ethereum"'],
            'polygon': [r'polygon', r'matic', r'\'polygon\'', r'"polygon"'],
            'arbitrum': [r'arbitrum', r'arb:', r'\'arbitrum\''],
            'optimism': [r'optimism', r'op:', r'\'optimism\''],
            'bsc': [r'bsc', r'binance', r'\'bsc\'', r'"bsc"'],
            'avalanche': [r'avalanche', r'avax', r'\'avalanche\''],
            'fantom': [r'fantom', r'ftm', r'\'fantom\''],
            'solana': [r'solana', r'sol:', r'\'solana\''],
            'cosmos': [r'cosmos', r'atom:', r'\'cosmos\''],
        }
        
        code_lower = adapter_code.lower()
        for chain, patterns in chain_patterns.items():
            for pattern in patterns:
                if re.search(pattern, code_lower):
                    chains.add(chain)
                    break
        
        return sorted(list(chains)) if chains else ['unknown']

    def analyze_protocol(self, protocol_name: str) -> Optional[ProtocolAnalysis]:
        """Analyze a single protocol"""
        print(f"\n📋 Analyzing: {protocol_name}")

        # Fetch adapter file
        adapter_result = self.fetch_adapter_file(protocol_name)
        if not adapter_result:
            print(f"   ⚠️  No adapter file found")
            return None

        adapter_path, adapter_code = adapter_result

        # Check if it's a liquid staking protocol
        if not self.is_liquid_staking_protocol(protocol_name, adapter_code):
            print(f"   ⚠️  Not identified as liquid staking protocol")
            return None

        print(f"   ✅ Confirmed liquid staking protocol")

        # Extract chains
        chains = self.extract_chains(adapter_code)

        # Extract contracts
        contracts = self.extract_contract_addresses(adapter_code, protocol_name)

        # Build adapter URL
        adapter_url = f"https://github.com/{DEFILLLAMA_ADAPTERS_REPO}/tree/main/{adapter_path}"

        # Create analysis
        analysis = ProtocolAnalysis(
            protocol_name=protocol_name,
            protocol_slug=protocol_name.lower(),
            chains=chains,
            reward_addresses=contracts['reward'],
            withdrawal_addresses=contracts['withdrawal'],
            treasury_addresses=contracts['treasury'],
            governance_addresses=contracts['governance'],
            staking_addresses=contracts['staking'],
            total_addresses=sum(len(v) for v in contracts.values()),
            adapter_url=adapter_url,
            extraction_timestamp=datetime.now().isoformat(),
            code_length=len(adapter_code),
            notes=f"Source: {adapter_path}"
        )

        print(f"   📊 Found {analysis.total_addresses} contract addresses")
        print(f"      - Reward: {len(analysis.reward_addresses)}")
        print(f"      - Withdrawal: {len(analysis.withdrawal_addresses)}")
        print(f"      - Treasury: {len(analysis.treasury_addresses)}")
        print(f"      - Governance: {len(analysis.governance_addresses)}")
        print(f"      - Staking: {len(analysis.staking_addresses)}")
        print(f"   🌐 Chains: {', '.join(chains)}")

        return analysis

    def export_to_csv(self, filename: str = 'liquid_staking_analysis.csv'):
        """Export analysis results to CSV"""
        if not self.protocols:
            print("❌ No protocols to export")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'Protocol Name', 'Protocol Slug', 'Chains',
                    'Reward Addresses', 'Withdrawal Addresses',
                    'Treasury/Operational Addresses', 'Governance Addresses',
                    'Staking Addresses', 'Total Contract Addresses',
                    'Code Length', 'Adapter URL', 'Extraction Timestamp'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for protocol in self.protocols:
                    writer.writerow({
                        'Protocol Name': protocol.protocol_name,
                        'Protocol Slug': protocol.protocol_slug,
                        'Chains': ', '.join(protocol.chains),
                        'Reward Addresses': '; '.join(protocol.reward_addresses),
                        'Withdrawal Addresses': '; '.join(protocol.withdrawal_addresses),
                        'Treasury/Operational Addresses': '; '.join(protocol.treasury_addresses),
                        'Governance Addresses': '; '.join(protocol.governance_addresses),
                        'Staking Addresses': '; '.join(protocol.staking_addresses),
                        'Total Contract Addresses': protocol.total_addresses,
                        'Code Length': protocol.code_length,
                        'Adapter URL': protocol.adapter_url,
                        'Extraction Timestamp': protocol.extraction_timestamp
                    })
            print(f"✅ Results exported to {filename}")
        except IOError as e:
            print(f"❌ Failed to export CSV: {str(e)}")

    def export_to_json(self, filename: str = 'liquid_staking_analysis.json'):
        """Export analysis results to JSON"""
        if not self.protocols:
            print("❌ No protocols to export")
            return

        try:
            data = {
                'metadata': {
                    'title': 'Liquid Staking Protocol Analysis',
                    'description': 'Academic research on liquid staking protocols extracted from DefiLlama-Adapters',
                    'extracted_at': datetime.now().isoformat(),
                    'total_protocols_analyzed': len(self.protocols),
                    'data_source': 'DefiLlama-Adapters GitHub Repository (/projects directory)',
                    'extraction_method': 'Direct GitHub API queries (no external API subscriptions required)',
                    'total_contract_addresses_found': sum(p.total_addresses for p in self.protocols),
                },
                'protocols': [p.to_dict() for p in self.protocols]
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Results exported to {filename}")
        except IOError as e:
            print(f"❌ Failed to export JSON: {str(e)}")

    def run(self, limit: Optional[int] = None):
        """Run the complete discovery and analysis process"""
        print("\n" + "="*70)
        print("🚀 LIQUID STAKING PROTOCOL DISCOVERY BOT v2.0")
        print("="*70)
        print("Research Objective: Academic analysis of liquid staking protocols")
        print("Data Source: DefiLlama-Adapters GitHub Repository")
        print("Method: Direct GitHub API (no external subscriptions required)")
        print("="*70)

        # Discover protocols
        all_protocols = self.discover_protocols()
        if not all_protocols:
            print("❌ No protocols found. Exiting.")
            return

        # Limit analysis if specified
        if limit:
            protocols_to_analyze = all_protocols[:limit]
            print(f"\n⚙️  Limiting analysis to {limit} protocols")
        else:
            protocols_to_analyze = all_protocols

        # Analyze each protocol
        analyzed = 0
        skipped = 0

        for i, protocol in enumerate(protocols_to_analyze, 1):
            if not self.rate_limiter.check_limit():
                print("\n⚠️  Rate limit reached. Pausing analysis.")
                break

            analysis = self.analyze_protocol(protocol)
            if analysis:
                self.protocols.append(analysis)
                analyzed += 1
            else:
                skipped += 1

            # Be respectful with API calls
            time.sleep(0.3)

            # Show progress every 10 protocols
            if i % 10 == 0:
                print(f"\n   Progress: {i}/{len(protocols_to_analyze)} protocols processed")

        # Export results
        print("\n" + "="*70)
        print("📤 EXPORTING RESULTS")
        print("="*70)
        self.export_to_csv()
        self.export_to_json()

        # Display summary
        print("\n" + "="*70)
        print("📊 ANALYSIS SUMMARY")
        print("="*70)
        print(f"Total Protocols Discovered: {len(all_protocols)}")
        print(f"Protocols Analyzed: {analyzed}")
        print(f"Protocols Skipped (non-liquid-staking): {skipped}")
        print(f"Total Contract Addresses Found: {sum(p.total_addresses for p in self.protocols)}")
        if self.protocols:
            avg_addresses = sum(p.total_addresses for p in self.protocols) / len(self.protocols)
            print(f"Average Addresses per Protocol: {avg_addresses:.1f}")

        self.rate_limiter.display()
        print("\n✅ Analysis complete!\n")


def main():
    """Main entry point"""
    try:
        bot = LiquidStakingDiscoveryBot()
        # Run analysis (set limit to a number to test, e.g., limit=10)
        bot.run(limit=None)
    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
