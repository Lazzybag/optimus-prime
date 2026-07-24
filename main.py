#!/usr/bin/env python3
"""
Liquid Staking Protocol Discovery Bot
Research Tool for Analyzing Liquid Staking Protocol Architecture

Objective: Extract and categorize contract addresses from liquid staking
protocol adapters by directly querying the DefiLlama-Adapters GitHub repository.

Data Source: DefiLlama-Adapters GitHub Repository (/projects directory)
Author: Lazzybag
Version: 2.2.0
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

# Headers for GitHub API authentication
HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

# Liquid Staking Keywords for Protocol Identification
LIQUID_STAKING_KEYWORDS = [
    'lido', 'steth', 'reth', 'rocket', 'stakewise', 'frxeth', 'frax',
    'sfrxeth', 'eigen', 'eigenlayer', 'puffer', 'mellow', 'instadapp',
    'symbiotic', 'karak', 'restake', 'pendle', 'aave', 'morpho',
    'yearn', 'convex', 'stake', 'liquid', 'lsp', 'kelp', 'lst',
    'liquid-staking', 'liquid_staking', 'lsd', 'derivative', 'eth2',
    'beacon', 'consensus', 'wrapped', 'beacon-chain', 'restaking'
]

# Contract categorization keywords
CONTRACT_CATEGORIES = {
    'reward': [
        'reward', 'claim', 'distribute', 'emission', 'incentive',
        'staking_reward', 'yield', 'earning', 'apy', 'interest', 'fee'
    ],
    'withdrawal': [
        'withdraw', 'redeem', 'unstake', 'exit', 'claim_withdraw',
        'burn', 'unwrap', 'exchange', 'swap'
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
        'staking', 'stake', 'deposit', 'validator', 'node', 'lsp'
    ]
}


class DualOutput:
    """Outputs to both console and file"""
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.file = open(log_file, 'w', encoding='utf-8')
        self.console = sys.stdout

    def write(self, message: str):
        """Write to both console and file"""
        self.console.write(message)
        self.console.flush()
        self.file.write(message)
        self.file.flush()

    def flush(self):
        """Flush both outputs"""
        self.console.flush()
        self.file.flush()

    def close(self):
        """Close file"""
        self.file.close()


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
    index_file_url: str
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
        self.limit = 5000

    def update(self, headers: Dict):
        """Update rate limit info from response headers"""
        self.remaining = int(headers.get('X-RateLimit-Remaining', 5000))
        self.limit = int(headers.get('X-RateLimit-Limit', 5000))
        self.reset_time = int(headers.get('X-RateLimit-Reset', 0))
        self.total_requests += 1

    def display(self):
        """Display current rate limit status"""
        if self.reset_time:
            reset_dt = datetime.fromtimestamp(self.reset_time)
            print(f"\n📊 Rate Limit Status:")
            print(f"   Remaining Requests: {self.remaining}/{self.limit}")
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
        self.rate_limiter = RateLimitTracker()
        self.protocols: List[ProtocolAnalysis] = []
        self._check_rate_limit()

    def _check_rate_limit(self):
        """Check initial rate limit"""
        try:
            url = f"{GITHUB_API_BASE}/rate_limit"
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                self.rate_limiter.update(response.headers)
                print(f"📊 Initial Rate Limit: {self.rate_limiter.remaining}/{self.rate_limiter.limit}")
        except Exception as e:
            print(f"⚠️  Could not check rate limit: {str(e)}")

    def discover_protocols(self) -> List[Dict]:
        """Discover all protocols in /projects directory"""
        print("\n🔍 Fetching all protocol adapters from /projects directory...")

        url = f"{GITHUB_API_BASE}/repos/{DEFILLLAMA_ADAPTERS_REPO}/contents/{PROJECTS_DIR}"
        print(f"   Requesting: {url}")

        try:
            response = requests.get(url, headers=HEADERS)
            self.rate_limiter.update(response.headers)

            if response.status_code == 404:
                print(f"❌ 404 Error: /projects directory not found")
                return []

            if response.status_code == 401:
                print(f"❌ 401 Error: Authentication failed - check your GITHUB_PAT")
                return []

            response.raise_for_status()

            adapters = response.json()

            # Filter only directories (protocols)
            protocol_dirs = [item for item in adapters if item["type"] == "dir"]

            print(f"✅ Found {len(protocol_dirs)} protocol directories")

            return protocol_dirs

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching adapters: {e}")
            return []

    def is_liquid_staking_protocol(self, protocol_name: str) -> bool:
        """Check if protocol name matches liquid staking keywords"""
        name_lower = protocol_name.lower()
        return any(keyword in name_lower for keyword in LIQUID_STAKING_KEYWORDS)

    def fetch_adapter_file(self, protocol_name: str) -> Optional[Tuple[str, str, str]]:
        """Fetch adapter file from a protocol's directory"""
        try:
            index_url = f"{GITHUB_API_BASE}/repos/{DEFILLLAMA_ADAPTERS_REPO}/contents/{PROJECTS_DIR}/{protocol_name}/index.js"

            response = requests.get(index_url, headers=HEADERS)
            self.rate_limiter.update(response.headers)

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                return None

            file_data = response.json()

            # Get raw content from download_url
            raw_response = requests.get(file_data["download_url"])
            raw_response.raise_for_status()
            raw_content = raw_response.text

            return file_data["html_url"], raw_content, file_data["download_url"]

        except requests.exceptions.RequestException:
            return None

    def extract_contract_addresses(self, code: str) -> Dict[str, List[str]]:
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
        address_pattern = r'0x[a-fA-F0-9]{40}'
        matches = list(re.finditer(address_pattern, code))

        # Track unique addresses
        seen_addresses = set()

        # Split code into lines for context analysis
        lines = code.split('\n')

        for match in matches:
            address = match.group(0)

            # Skip if already seen
            if address in seen_addresses:
                continue
            seen_addresses.add(address)

            # Get surrounding context
            start_line = max(0, match.start() - 200)
            end_line = min(len(code), match.end() + 200)
            context = code[start_line:end_line].lower()

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
            'ethereum': [r'ethereum', r'eth:', r'\'ethereum\'', r'"ethereum"', r'0x[a-f0-9]{40}'],
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

    def analyze_protocol(self, protocol_dir: Dict) -> Optional[ProtocolAnalysis]:
        """Analyze a single protocol"""
        protocol_name = protocol_dir["name"]

        # Fetch adapter file
        adapter_result = self.fetch_adapter_file(protocol_name)
        if not adapter_result:
            return None

        index_file_url, adapter_code, download_url = adapter_result

        # Extract chains
        chains = self.extract_chains(adapter_code)

        # Extract contracts
        contracts = self.extract_contract_addresses(adapter_code)

        # Build adapter URL
        adapter_url = f"https://github.com/{DEFILLLAMA_ADAPTERS_REPO}/tree/main/{PROJECTS_DIR}/{protocol_name}"

        # Create analysis
        analysis = ProtocolAnalysis(
            protocol_name=protocol_name,
            protocol_slug=protocol_name.lower(),
            chains=chains,
            reward_addresses=list(set(contracts['reward'])),
            withdrawal_addresses=list(set(contracts['withdrawal'])),
            treasury_addresses=list(set(contracts['treasury'])),
            governance_addresses=list(set(contracts['governance'])),
            staking_addresses=list(set(contracts['staking'])),
            total_addresses=sum(len(set(v)) for v in contracts.values()),
            adapter_url=adapter_url,
            index_file_url=index_file_url,
            extraction_timestamp=datetime.now().isoformat(),
            code_length=len(adapter_code),
            notes=f"Source: {PROJECTS_DIR}/{protocol_name}"
        )

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
                    'Code Length', 'Adapter URL', 'Index File URL', 'Extraction Timestamp'
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
                        'Index File URL': protocol.index_file_url,
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

    def display_results(self):
        """Display extracted protocol information"""
        print("\n" + "="*80)
        print("LIQUID STAKING PROTOCOLS - CONTRACT ADDRESSES")
        print("="*80 + "\n")

        if not self.protocols:
            print("⚠️  No liquid staking protocols found!")
            return

        for idx, protocol in enumerate(self.protocols, 1):
            print(f"{idx}. 📌 {protocol.protocol_name}")
            print(f"   GitHub: {protocol.adapter_url}")
            print(f"   Index: {protocol.index_file_url}")
            print(f"   Total Contracts: {protocol.total_addresses}")

            if protocol.staking_addresses:
                print(f"   🔒 Staking: {', '.join(protocol.staking_addresses[:2])}")
            if protocol.reward_addresses:
                print(f"   💰 Rewards: {', '.join(protocol.reward_addresses[:2])}")
            if protocol.withdrawal_addresses:
                print(f"   🚀 Withdrawal: {', '.join(protocol.withdrawal_addresses[:2])}")

            print()

    def run(self, limit: Optional[int] = None):
        """Run the complete discovery and analysis process"""
        print("\n" + "="*80)
        print("🚀 LIQUID STAKING PROTOCOL DISCOVERY BOT v2.2")
        print("="*80)
        print("Research Objective: Academic analysis of liquid staking protocols")
        print("Data Source: DefiLlama-Adapters GitHub Repository")
        print("Method: Direct GitHub API (no external subscriptions required)")
        print("="*80)

        # Discover protocols
        all_protocols = self.discover_protocols()
        if not all_protocols:
            print("❌ No protocols found. Exiting.")
            return

        print(f"\n📋 Scanning {len(all_protocols)} protocols for liquid staking...")

        # Filter for liquid staking protocols
        liquid_staking_protocols = [
            p for p in all_protocols
            if self.is_liquid_staking_protocol(p["name"])
        ]

        print(f"✅ Found {len(liquid_staking_protocols)} liquid staking protocols")

        # Limit analysis if specified
        if limit:
            protocols_to_analyze = liquid_staking_protocols[:limit]
            print(f"⚙️  Limiting analysis to {limit} protocols\n")
        else:
            protocols_to_analyze = liquid_staking_protocols

        # Analyze each protocol
        analyzed = 0
        skipped = 0

        for i, protocol in enumerate(protocols_to_analyze, 1):
            if not self.rate_limiter.check_limit():
                print("\n⚠️  Rate limit reached. Pausing analysis.")
                break

            protocol_name = protocol["name"]
            print(f"  [{i}/{len(protocols_to_analyze)}] 📋 {protocol_name}...", end=" ", flush=True)

            analysis = self.analyze_protocol(protocol)
            if analysis:
                self.protocols.append(analysis)
                print(f"✓ ({analysis.total_addresses} contracts)")
                analyzed += 1
            else:
                print("✗")
                skipped += 1

            # Be respectful with API calls
            time.sleep(0.1)

        # Export results
        print("\n" + "="*80)
        print("📤 EXPORTING RESULTS")
        print("="*80)
        self.export_to_csv()
        self.export_to_json()

        # Display summary
        print("\n" + "="*80)
        print("📊 ANALYSIS SUMMARY")
        print("="*80)
        print(f"Total Protocols Discovered: {len(all_protocols)}")
        print(f"Liquid Staking Protocols Found: {len(liquid_staking_protocols)}")
        print(f"Protocols Analyzed: {analyzed}")
        print(f"Protocols Skipped: {skipped}")
        print(f"Total Contract Addresses Found: {sum(p.total_addresses for p in self.protocols)}")
        if self.protocols:
            avg_addresses = sum(p.total_addresses for p in self.protocols) / len(self.protocols)
            print(f"Average Addresses per Protocol: {avg_addresses:.1f}")

        # Display detailed results
        self.display_results()

        self.rate_limiter.display()
        print("\n✅ Analysis complete!\n")


def main():
    """Main entry point"""
    try:
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"liquid_staking_discovery_{timestamp}.log"

        # Redirect stdout to both console and file
        dual_output = DualOutput(log_filename)
        original_stdout = sys.stdout
        sys.stdout = dual_output

        print("\n" + "="*80)
        print("DEFILLAMA LIQUID STAKING ADAPTERS FETCHER")
        print("="*80)
        print(f"📝 Log file: {log_filename}\n")

        if not GITHUB_PAT:
            print("❌ Error: GITHUB_PAT not found in .env file")
            print("   Add to .env: GITHUB_PAT=your_token_here")
            dual_output.close()
            sys.stdout = original_stdout
            return

        bot = LiquidStakingDiscoveryBot()
        bot.run(limit=None)

        # Close the dual output and restore stdout
        dual_output.close()
        sys.stdout = original_stdout

        print(f"\n✅ Log file saved: {log_filename}")

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
