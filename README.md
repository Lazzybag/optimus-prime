# Liquid Staking Protocol Discovery Bot

## Overview

An **academic research tool** for analyzing liquid staking protocols by extracting and categorizing contract addresses from the DefiLlama-Adapters GitHub repository. This bot helps identify genuine protocols with properly implemented reward distribution and withdrawal mechanisms.

**No external API subscriptions required** - uses direct GitHub API queries via your Personal Access Token (PAT).

### Key Features

✅ **974+ Protocol Discovery** - Scans all protocols in DefiLlama-Adapters `/projects` directory
✅ **Smart Filtering** - Identifies liquid staking protocols using keyword matching
✅ **Contract Extraction** - Finds and categorizes contract addresses from adapter code
✅ **Multi-Chain Support** - Detects protocols deployed on Ethereum, Polygon, Arbitrum, Optimism, BSC, Avalanche, Fantom, Solana, and more
✅ **5 Contract Categories**:
  - 🔒 Staking contracts
  - 💰 Reward contracts
  - 🚀 Withdrawal contracts
  - 🏛️ Governance contracts
  - 💼 Treasury contracts

✅ **Three Export Formats**:
  - CSV spreadsheet (`liquid_staking_analysis.csv`)
  - JSON structured data (`liquid_staking_analysis.json`)
  - Log file with complete output (`liquid_staking_discovery_YYYYMMDD_HHMMSS.log`)

✅ **Rate Limit Tracking** - Monitors GitHub API quota in real-time
✅ **Zero Dependencies** - Only requires `requests` and `python-dotenv`

---

## Quick Start

### 1️⃣ Prerequisites

- Python 3.7+
- GitHub Personal Access Token (PAT)

### 2️⃣ Generate GitHub PAT

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Set scopes:
   - ✅ `repo:status`
   - ✅ `public_repo`
   - ✅ `read:repo_hook`
4. Copy the token (you won't see it again)

### 3️⃣ Automated Setup

**Unix/Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4️⃣ Add Your GitHub PAT

Edit `.env` file:
```env
GITHUB_PAT=your_github_pat_token_here
```

### 5️⃣ Run the Bot

```bash
python main.py
```

---

## File Structure

```
optimus-prime/
├── main.py                              # 🤖 Main bot script
├── .env                                 # 🔐 Environment variables (YOUR PAT HERE)
├── .gitignore                           # 🚫 Git ignore rules
├── requirements.txt                     # 📦 Python dependencies
├── setup.sh                             # ⚡ Automated setup script
├── README.md                            # 📖 This file
├── RESEARCH_TEMPLATE.md                 # 📋 Research guidelines
│
├── venv/                                # 🔧 Virtual environment (auto-created)
│
└── Output Files (generated on each run):
    ├── liquid_staking_analysis.csv      # 📊 Spreadsheet format
    ├── liquid_staking_analysis.json     # 📋 JSON format
    └── liquid_staking_discovery_*.log   # 📝 Console output log
```

---

## Usage

### Basic Run
```bash
python main.py
```

### What It Does

1. **Initializes** - Checks GitHub PAT and rate limits
2. **Discovers** - Fetches 974+ protocol directories from `/projects`
3. **Filters** - Identifies 31+ liquid staking protocols
4. **Analyzes** - Extracts contracts from adapter code
5. **Categorizes** - Groups addresses by function (staking, rewards, etc.)
6. **Exports** - Saves results in 3 formats
7. **Logs** - Creates timestamped output log

### Output Example

```
================================================================================
🚀 LIQUID STAKING PROTOCOL DISCOVERY BOT v2.2
================================================================================
Research Objective: Academic analysis of liquid staking protocols
Data Source: DefiLlama-Adapters GitHub Repository
Method: Direct GitHub API (no external subscriptions required)
================================================================================

🔍 Fetching all protocol adapters from /projects directory...
✅ Found 974 protocol directories

📋 Scanning 974 protocols for liquid staking...
✅ Found 31 liquid staking protocols

[1/31] 📋 LiquidOps... ✓ (0 contracts)
[2/31] 📋 MellowProtocol... ✓ (3 contracts)
...
```

---

## Data Export Formats

### CSV Export
```csv
Protocol Name,Protocol Slug,Chains,Reward Addresses,Withdrawal Addresses,...
Lido,lido,ethereum; polygon,0x1234...; 0x5678...,0xabcd...,...
```

### JSON Export
```json
{
  "metadata": {
    "title": "Liquid Staking Protocol Analysis",
    "extracted_at": "2026-07-24T23:03:00",
    "total_protocols_analyzed": 31,
    "total_contract_addresses_found": 129
  },
  "protocols": [
    {
      "protocol_name": "Lido",
      "reward_addresses": ["0x1234..."],
      ...
    }
  ]
}
```

### Log File
```
📋 Analyzing: Lido
   ✅ Found 15 contract addresses
   💰 Rewards: 3
   🚀 Withdrawal: 2
   🔒 Staking: 4
```

---

## Troubleshooting

### ❌ 401 Authentication Error
**Problem:** `401 Error: Authentication failed`
- **Solution:** Check your GitHub PAT in `.env` - ensure it's valid and has required scopes

### ❌ Module Not Found
**Problem:** `ModuleNotFoundError: No module named 'requests'`
- **Solution:** Run `pip install -r requirements.txt`

### ❌ Rate Limit Reached
**Problem:** `WARNING: Only 50 API requests remaining!`
- **Solution:** The bot will pause. Wait until rate limit reset (shown in output)

### ❌ Permission Denied on setup.sh
**Problem:** `Permission denied: ./setup.sh`
- **Solution:** Run `chmod +x setup.sh` first

---

## API Rate Limits

- **Authenticated (with PAT):** 5,000 requests/hour
- **Unauthenticated:** 60 requests/hour
- **Current bot usage:** ~33 requests per full scan (30+ protocols)

---

## Research Methodology

This tool follows strict academic research principles:

✅ **No Contract Interaction** - Read-only analysis
✅ **Transparent Data Source** - All from public DefiLlama-Adapters repo
✅ **Reproducible** - Same data for every run
✅ **Verifiable** - All contract links provided for manual verification
✅ **Non-invasive** - No network calls to protocols themselves

See `RESEARCH_TEMPLATE.md` for detailed research guidelines.

---

## Repository Details

- **Source:** DefiLlama-Adapters GitHub Repository
- **URL:** https://github.com/DefiLlama/DefiLlama-Adapters
- **Protocols:** 974+ DeFi protocols
- **Liquid Staking:** 31+ protocols identified

---

## Advanced Usage

### Limit Analysis to First N Protocols

Edit `main.py` line 556:
```python
bot.run(limit=10)  # Analyze only first 10 liquid staking protocols
```

### Custom Export Filenames

Edit export function calls:
```python
self.export_to_csv('my_custom_filename.csv')
self.export_to_json('my_custom_filename.json')
```

---

## Version History

- **v2.2** - Add dual output (console + log file)
- **v2.1** - Fix authentication with GitHub API
- **v2.0** - Remove DefiLlama API dependency, direct GitHub queries
- **v1.0** - Initial release

---

## License

MIT License - Use freely for academic and commercial purposes

---

## Support

For issues:
1. Check `RESEARCH_TEMPLATE.md` for research guidelines
2. Review Troubleshooting section above
3. Check GitHub PAT permissions
4. Verify internet connection

---

## Author

**Lazzybag** - Crypto Research & DeFi Analysis

Built for comprehensive analysis of liquid staking protocols before investment decisions.
