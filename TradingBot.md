# Ethereum/USDC Trading Bot Specification

## Overview
- **Project**: AI-driven crypto trading bot for ETH/USDC on Uniswap
- **Purpose**: Autonomous agent that analyzes market data, generates trading ideas, and manages positions
- **Mode**: CLI-based, run regularly to check for opportunities
- **Capital**: ~$1000 USD equivalent

## Trading Pair
- **Base**: ETH (Ethereum)
- **Quote**: USDC
- **DEX**: Uniswap V3 (Ethereum Mainnet)

## Infrastructure
- **RPC**: Public Ethereum RPC (e.g., Cloudflare or Alchemy public endpoint)
- **Wallet**: Configured externally, bot interacts via wallet address
- **Storage**: Markdown files for state persistence

## Strategy: AI-Driven Analysis with Web Research

The agent performs analysis on each run:
1. Fetch current ETH/USDC price from CoinGecko
2. Read price history and open positions from markdown files
3. **Do its own web research**: Search for Ethereum news, market sentiment, price drivers
4. Generate trading idea with rationale based on BOTH data AND web research
5. Check existing open positions from previous runs
6. Decide: enter new trade, stay in position, or close position

### AI Research Tasks
When analyzing, the agent is instructed to:
- Search for current Ethereum news and developments
- Check crypto market sentiment today
- Find any major ETH price drivers (upgrades, institutional news, regulations)
- Check Bitcoin and overall crypto market direction

### Decision Logic
- **Entry Signal**: Agent identifies favorable conditions based on:
  - Price momentum (trend direction)
  - Support/resistance levels
  - Recent volatility patterns
  - Current news and market sentiment
- **Exit Signal**:
  - Stop-loss: 5% from entry price
  - Take-profit: 10% from entry price
  - Or agent decides to close based on new analysis/news

## Position Sizing
- Max 5% of portfolio per trade (~$50 with $1000 capital)
- Max 1 open position at a time (simplified)

## State Management

### Files (all in `~/Documents/Projects/CryptoTrading/data/`)
```
data/
├── current_price.md    # Latest price data
├── price_history.md    # Historical prices for analysis
├── trading_idea.md     # Current trading idea & rationale
├── open_position.md    # Active trade details (if any)
├── trade_history.md    # Closed trades log
└── config.md           # Bot configuration
```

### Trading Idea Format (trading_idea.md)
```markdown
# Trading Idea

## Current Analysis
- Timestamp: YYYY-MM-DD HH:MM
- Current Price: $XXX.XX
- Price Change 24h: X.XX%
- Signal: BULLISH/BEARISH/NEUTRAL
- Confidence: XX%

## Reasoning
[Agent's analysis of market conditions]

## Decision
- Action: ENTER_LONG / EXIT / HOLD / NO_POSITION
- Entry Price: $XXX.XX (if applicable)
- Stop Loss: $XXX.XX
- Take Profit: $XXX.XX
```

### Open Position Format (open_position.md)
```markdown
# Open Position

## Entry
- Entry Price: $XXX.XX
- Entry Time: YYYY-MM-DD HH:MM
- Position Size: X.XXX ETH
- Position Value: $XXX.XX

## Targets
- Stop Loss: $XXX.XX (5% below entry)
- Take Profit: $XXX.XX (10% above entry)

## Current Status
- P&L: +X.XX% / -X.XX%
- Current Price: $XXX.XX
```

## Bot Commands (CLI Mode)
```
python bot.py analyze      # Analyze market, generate idea
python bot.py trade        # Execute trade if signal
python bot.py status       # Show current position & idea
python bot.py close        # Close current position
python bot.py history      # Show trade history
```

## Risk Management
- Max position: 5% of portfolio
- Stop-loss: 5% below entry
- Take-profit: 10% above entry
- One position at a time

## Technical Notes
- Uses CoinGecko API for price data
- ETH/USDC pool: 0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8 (Uniswap V3)

## Opencode CLI Integration

### Running with Opencode

Opencode CLI mode accepts prompts directly. The agent reads the markdown data files to understand context from previous runs.

```bash
# Full analysis with Opencode decision
opencode run --model opencode/big-pickle --agent build "Read ~/Documents/Projects/CryptoTrading/data/trading_idea.md, ~/Documents/Projects/CryptoTrading/data/open_position.md, and ~/Documents/Projects/CryptoTrading/data/price_history.md. Analyze ETH/USDC market conditions and decide: ENTER_LONG, HOLD, EXIT, or NO_POSITION. Then execute: python3 ~/Documents/Projects/CryptoTrading/bot.py analyze"
```

### Alternative: Run bot first, then Opencode decides

```bash
# 1. Run analysis to get fresh data
python3 ~/Documents/Projects/CryptoTrading/bot.py analyze

# 2. Let Opencode make the trading decision
opencode run --model opencode/big-pickle --agent build "Read ~/Documents/Projects/CryptoTrading/data/trading_idea.md and ~/Documents/Projects/CryptoTrading/data/open_position.md. Should we execute a trade? Answer with action: ENTER_LONG, HOLD, EXIT, or NO_POSITION. If ENTER_LONG, run: python3 ~/Documents/Projects/CryptoTrading/bot.py trade"
```

### Cron Job Examples

The `analyze` command already uses AI for research and analysis. It will:
1. Fetch current ETH price
2. Launch Opencode to do web research + analysis
3. Write trading idea to `data/trading_idea.md`

```bash
# Run every hour - AI analyzes market and does web research
0 * * * * cd ~/Documents/Projects/CryptoTrading && python3 bot.py analyze

# Run every 4 hours - analyze then execute trade if signal
0 */4 * * * cd ~/Documents/Projects/CryptoTrading && python3 bot.py analyze && python3 bot.py trade

# Run daily at 8am - full analysis
0 8 * * * cd ~/Documents/Projects/CryptoTrading && python3 bot.py analyze

# Alternative: Let Opencode handle everything (includes web research)
# Note: This uses subprocess to call opencode, may timeout on some systems
0 * * * * cd ~/Documents/Projects/CryptoTrading && python3 bot.py analyze
```

### How Context is Preserved

1. **Bot saves state** → Writes to markdown files in `data/`
2. **Opencode runs** → Reads markdown files as context
3. **Agent decides** → Makes trading decision based on historical context
4. **Action executed** → Bot updates markdown files

This ensures continuity between Opencode sessions without needing a database.

## Real Trading Implementation

### Currently: Paper Trading Only
The bot currently documents trading ideas in markdown files but does NOT execute real trades on the blockchain.

### Steps to Enable Real Trading

#### 1. Set Up Wallet
- Create a new wallet for trading (recommended) or use existing
- Fund with ~$1000 USDC for trading capital
- Keep private key secure (never commit to git)

#### 2. Add Private Key Configuration
Create `.env` file in project root:
```bash
# .env (add to .gitignore!)
WALLET_PRIVATE_KEY=your_private_key_here
```

#### 3. Update Config
Edit `data/config.md`:
```markdown
- Wallet Address: <YOUR_WALLET_ADDRESS>
- Trading Mode: LIVE
```

#### 4. Required Python Functions to Add
- `swap_usdc_to_eth(amount_usdc)` - Buy ETH with USDC
- `swap_eth_to_usdc(amount_eth)` - Sell ETH for USDC  
- `approve_token(token, spender)` - Approve token spending
- `check_stop_loss()` - Monitor and execute stop-loss
- `check_take_profit()` - Monitor and execute take-profit

#### 5. Uniswap V3 Swap Process
Real swaps require:
1. Approve USDC/ETH spending on the router contract
2. Build exactInputSingle transaction
3. Sign and send transaction
4. Wait for confirmation

#### 6. Safety Features
- [ ] Transaction confirmation wait
- [ ] Slippage protection (e.g., 0.5% slippage tolerance)
- [ ] Gas price estimation
- [ ] Transaction failure handling
- [ ] Emergency stop (kill switch)

### Required Dependencies
```bash
pip install web3 python-dotenv
```

### Risk Warning
⚠️ **Real trading involves financial risk**
- Always test with paper trading first
- Start with small amounts
- Monitor positions closely
- Set up alerts for position changes
