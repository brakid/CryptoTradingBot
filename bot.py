import os
import json
import sys
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    from web3 import Web3
    from eth_account import Account
except ImportError:
    print("Installing web3...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "web3>=6.0.0", "eth-account"])
    from web3 import Web3
    from eth_account import Account

DATA_DIR = Path.home() / "Documents" / "Projects" / "CryptoTrading" / "data"
CONFIG_FILE = DATA_DIR / "config.md"
CURRENT_PRICE_FILE = DATA_DIR / "current_price.md"
PRICE_HISTORY_FILE = DATA_DIR / "price_history.md"
TRADING_IDEA_FILE = DATA_DIR / "trading_idea.md"
OPEN_POSITION_FILE = DATA_DIR / "open_position.md"
TRADE_HISTORY_FILE = DATA_DIR / "trade_history.md"

PROJECT_DIR = Path.home() / "Documents" / "Projects" / "CryptoTrading"
ENV_FILE = PROJECT_DIR / ".env"

UNISWAP_V3_POOL = "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
FEE_TIER = 3000

TRADING_MODE = "PAPER"
PRIVATE_KEY = None
WALLET_ADDRESS = None
w3 = None

RPC_URLS = [
    "https://eth.llamarpc.com",
    "https://ethereum-rpc.publicnode.com",
    "https://rpc.ankr.com/eth",
]

def load_config():
    global TRADING_MODE, PRIVATE_KEY, WALLET_ADDRESS, w3
    
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().split("\n"):
            if line.startswith("TRADING_MODE="):
                TRADING_MODE = line.split("=")[1].strip()
            elif line.startswith("WALLET_PRIVATE_KEY="):
                PRIVATE_KEY = line.split("=")[1].strip()
            elif line.startswith("WALLET_ADDRESS="):
                WALLET_ADDRESS = line.split("=")[1].strip()
    
    if TRADING_MODE == "LIVE" and PRIVATE_KEY:
        for url in RPC_URLS:
            try:
                w3 = Web3(Web3.HTTPProvider(url))
                if w3.is_connected():
                    break
            except:
                continue

def get_web3():
    for url in RPC_URLS:
        try:
            w3 = Web3(Web3.HTTPProvider(url))
            if w3.is_connected():
                return w3
        except:
            continue
    raise Exception("Could not connect to any Ethereum RPC")

ROUTER_ABI = [
    {
        "inputs": [
            {"name": "params", "type": "tuple",
             "components": [
                 {"name": "tokenIn", "type": "address"},
                 {"name": "tokenOut", "type": "address"},
                 {"name": "fee", "type": "uint24"},
                 {"name": "recipient", "type": "address"},
                 {"name": "deadline", "type": "uint256"},
                 {"name": "amountIn", "type": "uint256"},
                 {"name": "amountOutMinimum", "type": "uint256"},
                 {"name": "sqrtPriceLimitX96", "type": "uint160"}
             ]}
        ],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def load_markdown_value(filepath, key):
    if not filepath.exists():
        return None
    content = filepath.read_text()
    for line in content.split("\n"):
        if line.startswith(f"- {key}:"):
            return line.split(":", 1)[1].strip()
    return None

def save_markdown(filepath, content):
    filepath.write_text(content)

def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return float(data["ethereum"]["usd"])
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def update_price():
    price = get_eth_price()
    if price:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content = f"""# Current Price

## ETH/USDC
- Price: ${price:,.2f}
- Last Updated: {now}

## Source
- Uniswap V3 Pool: {UNISWAP_V3_POOL}
"""
        save_markdown(CURRENT_PRICE_FILE, content)
        
        history_content = PRICE_HISTORY_FILE.read_text() if PRICE_HISTORY_FILE.exists() else "# Price History\n\n## ETH/USDC\n\n"
        entry = f"- {now}: ${price:,.2f}\n"
        
        if "No historical data" in history_content:
            history_content = "# Price History\n\n## ETH/USDC\n\n" + entry
        else:
            history_content += entry
        
        save_markdown(PRICE_HISTORY_FILE, history_content)
        
        print(f"ETH price updated: ${price:,.2f}")
        return price
    return None

def get_position():
    if not OPEN_POSITION_FILE.exists():
        return None
    content = OPEN_POSITION_FILE.read_text()
    if "No open position" in content:
        return None
    
    entry_price = load_markdown_value(OPEN_POSITION_FILE, "Entry Price")
    entry_time = load_markdown_value(OPEN_POSITION_FILE, "Entry Time")
    position_size = load_markdown_value(OPEN_POSITION_FILE, "Position Size")
    stop_loss = load_markdown_value(OPEN_POSITION_FILE, "Stop Loss")
    take_profit = load_markdown_value(OPEN_POSITION_FILE, "Take Profit")
    
    if entry_price and entry_price != "-":
        def extract_price(val):
            if not val:
                return 0
            import re
            match = re.search(r'\$?([\d,]+\.?\d*)', str(val))
            if match:
                return float(match.group(1).replace(",", ""))
            return 0
        
        return {
            "entry_price": extract_price(entry_price),
            "entry_time": entry_time,
            "position_size": float(position_size.replace(" ETH", "")) if position_size else 0,
            "stop_loss": extract_price(stop_loss),
            "take_profit": extract_price(take_profit)
        }
    return None

def analyze():
    print("\n=== MARKET ANALYSIS ===\n")
    
    price = update_price()
    if not price:
        print("Failed to get price")
        return
    
    position = get_position()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    history = PRICE_HISTORY_FILE.read_text()
    price_points = []
    for line in history.split("\n"):
        if "$" in line and ":" in line:
            try:
                parts = line.split(":")
                if len(parts) >= 2:
                    price_val = parts[1].replace("$", "").replace(",", "").strip()
                    price_points.append(float(price_val))
            except:
                pass
    
    change_24h = 0
    if len(price_points) >= 3:
        change_24h = ((price_points[-1] - price_points[-3]) / price_points[-3]) * 100
    
    position_info = ""
    if position:
        current_pnl = ((price - position["entry_price"]) / position["entry_price"]) * 100
        position_info = f"""
## Current Open Position (from previous session)
- Entry Price: ${position['entry_price']:,.2f}
- Entry Time: {position['entry_time']}
- Position Size: {position['position_size']:.6f} ETH
- Stop Loss: ${position['stop_loss']:,.2f}
- Take Profit: ${position['take_profit']:,.2f}
- Current P&L: {current_pnl:+.2f}%
"""
    
    analysis_prompt = f"""You are a crypto trading analyst. Analyze ETH/USDC and create a trading idea.

## Read These Files First
Before making any decision, read these files:
1. ~/Documents/Projects/CryptoTrading/data/current_price.md
2. ~/Documents/Projects/CryptoTrading/data/price_history.md
3. ~/Documents/Projects/CryptoTrading/data/open_position.md
4. ~/Documents/Projects/CryptoTrading/data/trading_idea.md (previous analysis)
5. ~/Documents/Projects/CryptoTrading/data/trade_journal.md (learn from past trades)
6. ~/Documents/Projects/CryptoTrading/data/AGENT_INSTRUCTIONS.md (your instructions)

## Current Market Data
- Current Price: ${price:,.2f}
- Price Change (from previous check): {change_24h:+.2f}%
- Price History (recent checks): {price_points[-10:] if len(price_points) >= 10 else price_points}

{position_info}

## Your Task
Analyze the market and decide what action to take. You MUST do your own research first:

### Step 1: Research
Use web search to find:
1. Current Ethereum news and developments
2. Crypto market sentiment today
3. Any major ETH price drivers (upcoming upgrades, institutional news, regulatory updates)
4. Bitcoin and overall crypto market direction

### Step 2: Check Trade Journal
Read data/trade_journal.md to learn from past winning/losing trades. Try to replicate successful patterns.

### Step 3: Technical Analysis
Consider:
1. Price momentum and trend from the data above
2. Support/resistance levels
3. If there's an open position, should we hold, exit (take profit/stop loss), or continue holding?
4. If no position, should we enter a new trade?

### Step 4: Decision
Write your trading idea to: ~/Documents/Projects/CryptoTrading/data/trading_idea.md

The file must contain:
- Timestamp: {now}
- Current Price: ${price:,.2f}
- Signal: BULLISH, BEARISH, or NEUTRAL
- Confidence: XX% (your confidence level)
- Reasoning: Your detailed analysis citing BOTH the data above AND your web research
- Decision: Action (ENTER_LONG, HOLD, EXIT, or NO_POSITION)
- Entry Price: $XXXX.XX (if ENTER_LONG) or -
- Stop Loss: $XXXX.XX (5% below entry) or -
- Take Profit: $XXXX.XX (10% above entry) or -

### Step 5: Update Instructions if Needed
If these instructions are unclear or you want to improve them, UPDATE: ~/Documents/Projects/CryptoTrading/data/AGENT_INSTRUCTIONS.md

### Step 6: Record Trade
After closing a trade (win or loss), record it in: ~/Documents/Projects/CryptoTrading/data/trade_journal.md

IMPORTANT: Do your own web research first, then make your decision. Cite specific news or market conditions in your reasoning.
"""

    print("Delegating analysis to AI agent...\n")
    print(f"Current Price: ${price:,.2f}")
    print(f"Price Change: {change_24h:+.2f}%")
    if position:
        current_pnl = ((price - position["entry_price"]) / position["entry_price"]) * 100
        print(f"Open Position P&L: {current_pnl:+.2f}%")
    print("\nRunning AI analysis...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["opencode", "run", "--model", "opencode/big-pickle", analysis_prompt],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(PROJECT_DIR)
        )
        print("\nAI Analysis complete!")
        if result.stdout:
            print(result.stdout[:500])
        if result.stderr:
            print("Notes:", result.stderr[:200])
    except subprocess.TimeoutExpired:
        print("AI analysis timed out")
    except FileNotFoundError:
        print("Opencode not found. Please ensure opencode is installed.")
        print("Falling back to basic analysis...")
        
        basic_analysis(price, position, price_points, change_24h, now)

def basic_analysis(price, position, price_points, change_24h, now):
    """Fallback basic analysis if Opencode is not available"""
    signal = "NEUTRAL"
    confidence = 50
    reasoning = "Basic analysis fallback"
    action = "NO_POSITION"
    
    if len(price_points) >= 2:
        current = price_points[-1]
        previous = price_points[-2]
        change_pct = ((current - previous) / previous) * 100
        
        if position:
            entry = position["entry_price"]
            pnl_pct = ((current - entry) / entry) * 100
            
            if current <= position["stop_loss"]:
                action = "EXIT"
                reasoning = f"Stop loss triggered"
                confidence = 95
            elif current >= position["take_profit"]:
                action = "EXIT"
                reasoning = f"Take profit target reached"
                confidence = 95
            else:
                action = "HOLD"
                reasoning = f"Position P&L: {pnl_pct:+.2f}%"
                confidence = 60
        else:
            if change_pct > 2:
                signal = "BULLISH"
                confidence = 65
                action = "ENTER_LONG"
            elif change_pct < -2:
                signal = "BEARISH"
                confidence = 60
                action = "NO_POSITION"
    
    entry_price_str = f"${price:.2f}" if action == "ENTER_LONG" else "-"
    stop_loss_str = f"${price * 0.95:.2f}" if action == "ENTER_LONG" else "-"
    take_profit_str = f"${price * 1.10:.2f}" if action == "ENTER_LONG" else "-"
    
    idea_content = f"""# Trading Idea

## Current Analysis
- Timestamp: {now}
- Current Price: ${price:,.2f}
- Price Change 24h: {change_24h:+.2f}%
- Signal: {signal}
- Confidence: {confidence}%

## Reasoning
{reasoning}

## Decision
- Action: {action}
- Entry Price: {entry_price_str}
- Stop Loss: {stop_loss_str}
- Take Profit: {take_profit_str}
"""
    
    save_markdown(TRADING_IDEA_FILE, idea_content)
    print(f"Signal: {signal} (Confidence: {confidence}%)")
    print(f"Action: {action}")

def show_status():
    print("\n=== BOT STATUS ===\n")
    
    if CURRENT_PRICE_FILE.exists():
        price = load_markdown_value(CURRENT_PRICE_FILE, "Price")
        print(f"Current ETH Price: {price}")
    
    position = get_position()
    if position:
        current_price = get_eth_price() or position["entry_price"]
        pnl_pct = ((current_price - position["entry_price"]) / position["entry_price"]) * 100
        print(f"\nOpen Position:")
        print(f"  Entry: ${position['entry_price']:,.2f}")
        print(f"  Stop Loss: ${position['stop_loss']:,.2f}")
        print(f"  Take Profit: ${position['take_profit']:,.2f}")
        print(f"  P&L: {pnl_pct:+.2f}%")
    else:
        print("\nNo open position")
    
    print(f"\nTrading Idea: {TRADING_IDEA_FILE}")
    print(f"Price History: {PRICE_HISTORY_FILE}")

def close_position():
    position = get_position()
    if not position:
        print("No open position to close")
        return
    
    current_price = get_eth_price()
    if current_price:
        pnl_pct = ((current_price - position["entry_price"]) / position["entry_price"]) * 100
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        history = TRADE_HISTORY_FILE.read_text() if TRADE_HISTORY_FILE.exists() else "# Trade History\n\n## Closed Trades\n\n"
        
        trade_entry = f"""- **Trade {now}**:
  - Entry: ${position['entry_price']:,.2f}
  - Exit: ${current_price:,.2f}
  - P&L: {pnl_pct:+.2f}%
  - Reason: Manual close / Signal exit
"""
        
        if "No completed trades" in history:
            history = "# Trade History\n\n## Closed Trades\n\n" + trade_entry
        else:
            history += trade_entry
        
        save_markdown(TRADE_HISTORY_FILE, history)
        
        save_markdown(OPEN_POSITION_FILE, """# Open Position

No open position.
""")
        
        print(f"Position closed. P&L: {pnl_pct:+.2f}%")
    else:
        print("Could not get current price")

def show_history():
    if TRADE_HISTORY_FILE.exists():
        print(TRADE_HISTORY_FILE.read_text())
    else:
        print("No trade history")

def approve_token(token_address, spender, amount):
    if not w3 or not PRIVATE_KEY:
        print("Error: LIVE mode requires wallet configuration")
        return None
    
    token = w3.eth.contract(Web3.to_checksum_address(token_address), abi=ERC20_ABI)
    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    
    tx = token.functions.approve(
        spender,
        amount
    ).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Approved token. Tx: {tx_hash.hex()}")
    return receipt

def swap_usdc_to_eth(amount_usdc):
    if not w3 or not PRIVATE_KEY:
        print("Error: LIVE mode requires wallet configuration")
        return None
    
    print(f"Executing LIVE trade: Swap ${amount_usdc} USDC -> ETH")
    
    amount_in = int(amount_usdc * 1e6)
    amount_out_min = int((amount_usdc * 0.995) * 1e6)
    
    router = w3.eth.contract(Web3.to_checksum_address(UNISWAP_V3_ROUTER), abi=ROUTER_ABI)
    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    
    deadline = int(datetime.now().timestamp()) + 600
    
    params = (
        USDC,
        WETH,
        FEE_TIER,
        WALLET_ADDRESS,
        deadline,
        amount_in,
        amount_out_min,
        0
    )
    
    tx = router.functions.exactInputSingle(params).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'value': 0
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Swap executed. Tx: {tx_hash.hex()}")
    return receipt

def swap_eth_to_usdc(amount_eth):
    if not w3 or not PRIVATE_KEY:
        print("Error: LIVE mode requires wallet configuration")
        return None
    
    print(f"Executing LIVE trade: Swap {amount_eth} ETH -> USDC")
    
    amount_in = w3.to_wei(amount_eth, "ether")
    amount_out_min = int((amount_eth * get_eth_price() * 0.995) * 1e6)
    
    router = w3.eth.contract(Web3.to_checksum_address(UNISWAP_V3_ROUTER), abi=ROUTER_ABI)
    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    
    deadline = int(datetime.now().timestamp()) + 600
    
    params = (
        WETH,
        USDC,
        FEE_TIER,
        WALLET_ADDRESS,
        deadline,
        amount_in,
        amount_out_min,
        0
    )
    
    tx = router.functions.exactInputSingle(params).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'value': amount_in
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print(f"Swap executed. Tx: {tx_hash.hex()}")
    return receipt

def check_live_position():
    if not w3 or not WALLET_ADDRESS:
        return None
    
    weth_contract = w3.eth.contract(Web3.to_checksum_address(WETH), abi=ERC20_ABI)
    eth_balance = weth_contract.functions.balanceOf(WALLET_ADDRESS).call()
    
    if eth_balance > w3.to_wei(0.001, "ether"):
        return {
            "has_eth": True,
            "eth_amount": w3.from_wei(eth_balance, "ether")
        }
    return None

def trade():
    load_config()
    
    print(f"\n=== TRADING MODE: {TRADING_MODE} ===\n")
    
    if not TRADING_IDEA_FILE.exists():
        print("No trading idea. Run analyze first.")
        return
    
    action = load_markdown_value(TRADING_IDEA_FILE, "Action")
    
    if action == "ENTER_LONG":
        entry_price = load_markdown_value(TRADING_IDEA_FILE, "Entry Price")
        stop_loss = load_markdown_value(TRADING_IDEA_FILE, "Stop Loss")
        take_profit = load_markdown_value(TRADING_IDEA_FILE, "Take Profit")
        
        if entry_price and entry_price != "-":
            entry_price = float(entry_price.replace("$", "").replace(",", ""))
            stop_loss = float(stop_loss.replace("$", "").replace(",", ""))
            take_profit = float(take_profit.replace("$", "").replace(",", ""))
            
            position_size_eth = 50 / entry_price
            trade_value = 50
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            tx_hash = None
            if TRADING_MODE == "LIVE":
                if not w3 or not PRIVATE_KEY:
                    print("Error: LIVE mode requires wallet configuration in .env file")
                    return
                
                approve_token(USDC, UNISWAP_V3_ROUTER, int(trade_value * 1e6))
                receipt = swap_usdc_to_eth(trade_value)
                if receipt:
                    tx_hash = receipt.transactionHash.hex()
            
            position_content = f"""# Open Position

## Entry
- Entry Price: ${entry_price:,.2f}
- Entry Time: {now}
- Position Size: {position_size_eth:.6f} ETH
- Position Value: ${trade_value:.2f}
- Trading Mode: {TRADING_MODE}
- Transaction Hash: {tx_hash or "N/A"}

## Targets
- Stop Loss: ${stop_loss:,.2f} (5% below entry)
- Take Profit: ${take_profit:,.2f} (10% above entry)

## Current Status
- P&L: 0.00%
- Current Price: ${entry_price:,.2f}
"""
            save_markdown(OPEN_POSITION_FILE, position_content)
            
            mode_str = f"[{TRADING_MODE}]" if TRADING_MODE == "LIVE" else ""
            print(f"Position opened {mode_str}: {position_size_eth:.6f} ETH @ ${entry_price:,.2f}")
            print(f"Stop Loss: ${stop_loss:,.2f}")
            print(f"Take Profit: ${take_profit:,.2f}")
            if tx_hash:
                print(f"Transaction: https://etherscan.io/tx/{tx_hash}")
                
    elif action == "EXIT":
        position = get_position()
        
        tx_hash = None
        if TRADING_MODE == "LIVE" and position:
            live_pos = check_live_position()
            if live_pos and live_pos["has_eth"]:
                swap_eth_to_usdc(float(live_pos["eth_amount"]))
        
        close_position()
        
    else:
        print(f"No trade to execute. Current action: {action}")

def main():
    load_config()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"=== CRYPTO TRADING BOT ===")
    print(f"Trading Mode: {TRADING_MODE}")
    if TRADING_MODE == "LIVE" and WALLET_ADDRESS:
        print(f"Wallet: {WALLET_ADDRESS[:6]}...{WALLET_ADDRESS[-4:]}")
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python bot.py <command>")
        print("Commands:")
        print("  analyze  - Analyze market and generate trading idea")
        print("  trade    - Execute trade based on current idea")
        print("  status   - Show current position and idea")
        print("  close    - Close current position")
        print("  history  - Show trade history")
        print("  price    - Just fetch current price")
        print()
        print("Configuration:")
        print(f"  Mode: {TRADING_MODE}")
        print(f"  Paper trading: No real transactions")
        print(f"  Live trading: Executes real swaps on Uniswap")
        return
    
    command = sys.argv[1]
    
    if command == "analyze":
        analyze()
    elif command == "trade":
        trade()
    elif command == "status":
        show_status()
    elif command == "close":
        close_position()
    elif command == "history":
        show_history()
    elif command == "price":
        update_price()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
