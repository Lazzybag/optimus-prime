#!/usr/bin/env python3
"""
Liquid Staking Protocol Discovery Bot
Research Tool for Analyzing Liquid Staking Protocol Architecture

Objective: Extract and categorize contract addresses from liquid staking
protocol adapters to identify genuine protocols with proper reward distribution
and withdrawal mechanisms.

Data Source: DefiLlama-Adapters GitHub Repository (via GitHub API)
Author: Lazzybag
Version: 1.0.0
"""

import os
import sys
import json
import csv
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_PAT = os.getenv('GITHUB_PAT')
DEFILLAMA_API_BASE = "https://api.llama.fi"
GITHUB_API_BASE = "https://api.github.com"
DEFILLAMA_ADAPTERS_REPO = "DefiLlama/DefiLlama-Adapters"
PROJECTS_DIR = "projects"

# TVL Filtering Parameters
TVL_MIN = 5_000_000  # $5M
TVL_MAX = 500_000_000  # $500M

# Regex patterns for contract address extraction
ADDRESS_PATTERNS = {
    'ethereum': r'0x[a-fA-F0-9]{40}',  # Ethereum addresses
    'solana': r'[1-9A-HJ-NP-Z]{43,44}',  # Solana addresses
    'generic': r'0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Z]{43,44}'  # Both
}

# Contract categorization keywords
CONTRACT_CATEGORIES = {
    'reward': [
        'reward', 'claim', 'distribute', 'emission', 'incentive',
        'staking_reward', 'yield', 'earning', 'apy'
    ],
    'withdrawal': [
        'withdraw', 'redeem', 'unstake', 'exit', 'claim_withdraw',
        'burn', 'unwrap', 'exchange'
    ],
    'treasury': [
        'treasury', 'admin', 'operations', 'operational', 'vault',
        'reserve', 'fund', 'multisig', 'dao_treasury'
    ],
    'governance': [
        'governance', 'voting', 'vote', 'proposal', 'dao', 'token',
        'delegate', 'snapshot'
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
    tvl: float
    chains: List[str]
    reward_addresses: List[str]
    withdrawal_addresses: List[str]
    treasury_addresses: List[str]
    governance_addresses: List[str]
    total_addresses: int
    adapter_url: str
    extraction_timestamp: str
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

    def _create_session(self) -> requests.Session:
        """Create a requests session with authentication"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3.raw+json',
            'User-Agent': 'LiquidStakingDiscoveryBot/1.0'
        })
        return session

    def _make_request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, timeout=timeout)
            self.rate_limiter.update(response.headers)

            if response.status_code == 404:
                print(f"   ❌ Not found: {url}")
                return None
            elif response.status_code == 403:
                print(f"   ❌ Access denied (rate limit?): {url}")
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

    def fetch_liquid_staking_protocols(self) -> List[Dict]:
        """Fetch liquid staking protocols from DefiLlama API"""
        print("\n🔄 Fetching liquid staking protocols from DefiLlama...")
        url = f"{DEFILLLAMA_API_BASE}/protocols"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            protocols = response.json()

            # Filter for liquid staking protocols with TVL in range
            liquid_staking = [
                p for p in protocols
                if p.get('category') == 'Liquid Staking'
                and TVL_MIN <= p.get('tvl', 0) <= TVL_MAX
            ]

            print(f"✅ Found {len(liquid_staking)} liquid staking protocols in TVL range")
            return liquid_staking
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch protocols: {str(e)}")
            return []

    def find_adapter_file(self, protocol_slug: str) -> Optional[Tuple[str, str]]:
        """Find adapter file in DefiLlama-Adapters repository"""
        # Try different possible paths
        possible_paths = [
            f"projects/{protocol_slug}/index.js",
            f"projects/{protocol_slug}/index.ts",
            f"projects/{protocol_slug.lower()}/index.js",
            f"projects/{protocol_slug.lower()}/index.ts",
        ]

        for path in possible_paths:
            url = f"{GITHUB_API_BASE}/repos/{DEFILLLAMA_ADAPTERS_REPO}/contents/{path}"
            response = self._make_request(url)

            if response and response.status_code == 200:
                return path, response.text

        return None

    def extract_contract_addresses(self, code: str, chain: str) -> List[ContractAddress]:
        """Extract contract addresses from adapter code"""
        addresses = []
        pattern = ADDRESS_PATTERNS.get('ethereum', ADDRESS_PATTERNS['generic'])

        # Find all matches in code
        matches = re.finditer(pattern, code)

        for match in matches:
            address = match.group(0)

            # Get surrounding context for categorization
            start = max(0, match.start() - 150)
            end = min(len(code), match.end() + 150)
            context = code[start:end].lower()

            # Categorize address
            category = self._categorize_address(context)
            confidence = self._calculate_confidence(context, category)

            contract = ContractAddress(
                address=address,
                chain=chain,
                category=category,
                context=context.strip(),
                confidence=confidence
            )
            addresses.append(contract)

        return addresses

    def _categorize_address(self, context: str) -> Optional[str]:
        """Categorize address based on surrounding context"""
        for category, keywords in CONTRACT_CATEGORIES.items():
            if any(keyword in context for keyword in keywords):
                return category
        return None

    def _calculate_confidence(self, context: str, category: Optional[str]) -> float:
        """Calculate confidence score for categorization"""
        if not category:
            return 0.3

        keywords = CONTRACT_CATEGORIES.get(category, [])
        matches = sum(1 for kw in keywords if kw in context)
        return min(0.95, 0.5 + (matches * 0.15))

    def analyze_protocol(self, protocol: Dict) -> Optional[ProtocolAnalysis]:
        """Analyze a single protocol"""
        protocol_name = protocol.get('name', 'Unknown')
        protocol_slug = protocol.get('symbol', '').lower()
        tvl = protocol.get('tvl', 0)

        print(f"\n📊 Analyzing: {protocol_name} (TVL: ${tvl:,.0f})")

        # Find adapter file
        adapter_result = self.find_adapter_file(protocol_slug)
        if not adapter_result:
            print(f"   ⚠️  No adapter found for {protocol_name}")
            return None

        adapter_path, adapter_code = adapter_result
        adapter_url = f"https://github.com/{DEFILLLAMA_ADAPTERS_REPO}/tree/main/{adapter_path}"

        # Extract contracts by chain
        reward_addrs = []
        withdrawal_addrs = []
        treasury_addrs = []
        governance_addrs = []

        chains = protocol.get('chains', [])
        if not chains:
            chains = ['Unknown']

        for chain in chains:
            contracts = self.extract_contract_addresses(adapter_code, chain)

            for contract in contracts:
                if contract.category == 'reward':
                    reward_addrs.append(contract.address)
                elif contract.category == 'withdrawal':
                    withdrawal_addrs.append(contract.address)
                elif contract.category == 'treasury':
                    treasury_addrs.append(contract.address)
                elif contract.category == 'governance':
                    governance_addrs.append(contract.address)

        total = len(reward_addrs) + len(withdrawal_addrs) + len(treasury_addrs) + len(governance_addrs)

        analysis = ProtocolAnalysis(
            protocol_name=protocol_name,
            protocol_slug=protocol_slug,
            tvl=tvl,
            chains=chains,
            reward_addresses=list(set(reward_addrs)),
            withdrawal_addresses=list(set(withdrawal_addrs)),
            treasury_addresses=list(set(treasury_addrs)),
            governance_addresses=list(set(governance_addrs)),
            total_addresses=total,
            adapter_url=adapter_url,
            extraction_timestamp=datetime.now().isoformat(),
            notes=f"Extracted from: {adapter_path}"
        )

        print(f"   ✅ Found {total} contract addresses")
        print(f"      - Reward: {len(analysis.reward_addresses)}")
        print(f"      - Withdrawal: {len(analysis.withdrawal_addresses)}")
        print(f"      - Treasury: {len(analysis.treasury_addresses)}")
        print(f"      - Governance: {len(analysis.governance_addresses)}")

        return analysis

    def export_to_csv(self, filename: str = 'liquid_staking_analysis.csv'):
        """Export analysis results to CSV"""
        if not self.protocols:
            print("❌ No protocols to export")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'Protocol Name', 'Protocol Slug', 'TVL', 'Chains',
                    'Reward Contract Addresses', 'Withdrawal Contract Addresses',
                    'Treasury/Operational Addresses', 'Governance Addresses',
                    'Total Contract Addresses Found', 'Adapter URL', 'Extraction Timestamp'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for protocol in self.protocols:
                    writer.writerow({
                        'Protocol Name': protocol.protocol_name,
                        'Protocol Slug': protocol.protocol_slug,
                        'TVL': f"${protocol.tvl:,.2f}",
                        'Chains': ', '.join(protocol.chains),
                        'Reward Contract Addresses': '; '.join(protocol.reward_addresses),
                        'Withdrawal Contract Addresses': '; '.join(protocol.withdrawal_addresses),
                        'Treasury/Operational Addresses': '; '.join(protocol.treasury_addresses),
                        'Governance Addresses': '; '.join(protocol.governance_addresses),
                        'Total Contract Addresses Found': protocol.total_addresses,
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
                    'extracted_at': datetime.now().isoformat(),
                    'total_protocols': len(self.protocols),
                    'tvl_range': {
                        'min': f"${TVL_MIN:,.0f}",
                        'max': f"${TVL_MAX:,.0f}"
                    },
                    'data_source': 'DefiLlama API + DefiLlama-Adapters GitHub Repository'
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
        print("🚀 LIQUID STAKING PROTOCOL DISCOVERY BOT")
        print("="*70)
        print(f"Research Objective: Academic analysis of liquid staking protocols")
        print(f"TVL Range: ${TVL_MIN:,.0f} - ${TVL_MAX:,.0f}")
        print(f"Data Source: DefiLlama + GitHub Adapters")

        # Fetch protocols
        protocols = self.fetch_liquid_staking_protocols()
        if not protocols:
            print("❌ No protocols found. Exiting.")
            return

        # Limit analysis if specified
        if limit:
            protocols = protocols[:limit]
            print(f"\n⚙️  Limiting analysis to {limit} protocols")

        # Analyze each protocol
        for i, protocol in enumerate(protocols, 1):
            if not self.rate_limiter.check_limit():
                print("\n⚠️  Rate limit reached. Pausing analysis.")
                break

            analysis = self.analyze_protocol(protocol)
            if analysis:
                self.protocols.append(analysis)

            # Be respectful with API calls
            time.sleep(0.5)

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
        print(f"Total Protocols Analyzed: {len(self.protocols)}")
        print(f"Total Contract Addresses Found: {sum(p.total_addresses for p in self.protocols)}")
        print(f"Average Addresses per Protocol: {sum(p.total_addresses for p in self.protocols) / len(self.protocols):.1f}")

        self.rate_limiter.display()
        print("\n✅ Analysis complete!\n")


def main():
    """Main entry point"""
    try:
        bot = LiquidStakingDiscoveryBot()
        # Run with optional limit (remove or change the limit parameter)
        bot.run(limit=None)  # Set to a number to limit analysis (e.g., limit=5)
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
