import os
import time
import base64
import hmac
import json
import difflib
from urllib.parse import urlencode
import requests
from fuzzywuzzy import fuzz
from typing import Optional, List, Dict
import time
import os
env=os.listdir
# --- Global configuration (set via environment or override as needed) ---
env.API_KEY
OKX_API_KEY = env.API_KEY
OKX_SECRET_KEY = env.SECRET_KEY
OKX_PASSPHRASE = env.PASSPHRASE
OKX_PROJECT_ID = env.PROJECT_ID


if not all([OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE]):
    raise ValueError("OKX API keys not set in environment")

CHAIN_INDEX = 196  # Set to your default chain (e.g., "1" for Ethereum)
CHAIN_NAME = "xlayer"
CHAINS = 196

OKX_BASE_URL = "https://web3.okx.com" 

# --- Helper: OKX request/signature ---
def make_okx_headers(method, path, params=None, body=None):
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if method.upper() == "GET" and params:
        request_path = path + "?" + urlencode(params)
        body_str = ""
    else:
        request_path = path
        body_str = json.dumps(body) if body and method in ("POST", "PUT") else ""

    message = timestamp + method.upper() + request_path + body_str

    signature = base64.b64encode(
        hmac.new(OKX_SECRET_KEY.encode(), message.encode(), "sha256").digest()
    ).decode()

    return {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "Content-Type": "application/json",
    }


def okx_request(method, path, params=None, body=None):
    headers = make_okx_headers(method, path, params, body)
    url = f"{OKX_BASE_URL}{path}"
    if params and method == "GET":
        url += "?" + urlencode(params)
        response = requests.get(url, headers=headers)
    elif method == "GET":
        response = requests.get(url, headers=headers)
    else:
        response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()

# --- Helper: Token symbol/name → address resolution ---
def fuzzy_find_token_address(chain_name:str, query: str, threshold: int = 80) -> Optional[str]:
    tokens=get_tokens_by_chain(chain_name)
    query = query.lower().replace(" ", "").strip()
    best_score = 0
    best_match = None

    for token in tokens:
        name = token.get("name", "").lower().replace(" ", "").strip()
        symbol = token.get("symbol", "").lower().strip()

        score_name = fuzz.ratio(query, name)
        score_symbol = fuzz.ratio(query, symbol)

        if score_name > best_score and score_name >= threshold:
            best_score = score_name
            best_match = token

        if score_symbol > best_score and score_symbol >= threshold:
            best_score = score_symbol
            best_match = token

    if best_match:
        return best_match["address"]
    return None

def get_tokens_by_chain(chain_name:str)->str:
    chain_index=search_chain(chain_name)
    """Fetch all token metadata (symbol, name, address, decimals) for a chain."""
    tokens = okx_request("GET", "/api/v5/dex/aggregator/all-tokens", {"chainIndex": chain_index, "chainId": chain_index})
    return [
        {
            "symbol": t["tokenSymbol"],
            "name": t.get("tokenName", t["tokenSymbol"]),
            "address": t["tokenContractAddress"],
            "decimals": int(t.get("decimals", "0")),
            "chainIndex": chain_index,
        }
        for t in tokens.get("data", [])
    ]

def resolve_token_address(chain_name:str, token_name_or_symbol:str)->str:
    """
    Resolve a token's contract address by symbol or name.
    First checks NATIVE_TOKEN_ADDRESS_MAP, then fuzzy-matches against OKX token list.
    Raises ValueError if not found.
    """
    CHAIN_NAME=chain_name
    # Check hardcoded native tokens


    # Fetch all tokens on this chain
    tokens = get_tokens_by_chain(CHAIN_NAME)
    token_names = [t["symbol"].lower() for t in tokens] + [t["name"].lower() for t in tokens]

    # Fuzzy match against symbol or name
    best_match = difflib.get_close_matches(token_name_or_symbol.lower(), token_names, n=1, cutoff=0.6)
    if best_match:
        for t in tokens:
            if t["symbol"].lower() == best_match[0] or t["name"].lower() == best_match[0]:
                return t["address"]

    raise ValueError(f"Token '{token_name_or_symbol}' not found on chain {CHAIN_INDEX}")

def search_chain(chain_name: str, threshold: int = 80) -> Optional[str]:
    chains = get_supported_chains()["data"]
    chain_name = chain_name.lower().replace(" ", "").strip()

    best_score = 0
    best_match = None

    for chain in chains:
        full_name = chain['name'].lower().replace(" ", "").strip()
        short_name = chain['shortName'].lower().strip()

        score_full = fuzz.ratio(chain_name, full_name)
        score_short = fuzz.ratio(chain_name, short_name)

        if score_full > best_score and score_full >= threshold:
            best_score = score_full
            best_match = chain

        if score_short > best_score and score_short >= threshold:
            best_score = score_short
            best_match = chain

    if best_match:
        return best_match['chainIndex']
    return None
# --- Core DEX/aggregator functions (use global CHAIN_INDEX and CHAINS) ---
def get_supported_chains()->str:
    """Returns all supported chains on OKX DEX."""
    return okx_request("GET", "/api/v5/dex/balance/supported/chain")

def get_supported_tokens()->str:
    """Returns supported DEX tokens for the globally configured chain."""
    return get_tokens_by_chain(CHAIN_NAME)

def get_token_price(token_name:str)->str:
    """Returns the current price for a token (by name/symbol) on the global chain."""
    address = resolve_token_address(CHAIN_NAME, token_name)
    return okx_request("POST", "/api/v5/dex/market/price", None, [{"chainIndex": CHAIN_INDEX, "tokenContractAddress": address}])

def get_candle_price(token_name:str)->str:
    """Returns the latest candle (OHLC) price for a token by name/symbol."""
    address = resolve_token_address(CHAIN_NAME, token_name)
    return okx_request("GET", "/api/v5/dex/market/candles", {"chainIndex": CHAIN_INDEX, "tokenContractAddress": address})

def get_historical_candles(token_name:str)->str:
    """Returns historical candle (OHLC) data for a token by name/symbol."""
    address = resolve_token_address(CHAIN_NAME, token_name)
    return okx_request("GET", "/api/v5/dex/market/historical-candles", {"chainIndex": CHAIN_INDEX, "tokenContractAddress": address})

def get_market_trades(token_name:str)->str:
    """Returns recent trades for a token by name/symbol."""
    address = resolve_token_address(CHAIN_NAME, token_name)
    return okx_request("GET", "/api/v5/dex/market/trades", {"chainIndex": CHAIN_INDEX, "tokenContractAddress": address})


def get_swap_quote(token_from_name:str, token_to_name:str, amount:str, slippage:str="0.01")->str:
    """Get a swap quote (by token name/symbol) for the global chain."""
    time.sleep(1) 
    from_address = resolve_token_address(CHAIN_NAME, token_from_name)
    time.sleep(1) 
    to_address = resolve_token_address(CHAIN_NAME, token_to_name)
    params = {
        "chainId": CHAIN_INDEX,
        "fromTokenAddress": from_address,
        "toTokenAddress": to_address,
        "amount": int(amount),
        "slippage": float(slippage),
    }
    return okx_request("GET", "/api/v5/dex/aggregator/quote", params)

def get_swap_instructions(
    token_from_name:str,
    token_to_name:str,
    amount:str,
    slippage:str,
    user_wallet_address:str,
    fee_percent:str="1",
    price_tolerance:str="0",
    auto_slippage:str="false",
    path_num:str="3",
)->str:
    """Get Solana swap instructions (by token name/symbol) for the global chain."""
    time.sleep(1)
    from_address = resolve_token_address(CHAIN_NAME, token_from_name)
    time.sleep(1)
    to_address = resolve_token_address(CHAIN_NAME, token_to_name)
    params = {
        "chainId": CHAIN_INDEX,
        "fromTokenAddress": from_address,
        "toTokenAddress": to_address,
        "amount": int(amount),
        "slippage": float(slippage),
        "userWalletAddress": user_wallet_address,
        "feePercent": fee_percent,
        "priceTolerance": price_tolerance,
        "autoSlippage": auto_slippage,
        "pathNum": path_num,
    }
    return okx_request("GET", "/api/v5/dex/aggregator/swap-instruction", params)

def get_all_token_balances(address:str, exclude_risk_token:Optional[str]=None)->str:
    """Returns balances for all tokens for an address on the global chain (or CHAINS if set)."""
    params = {
        "address": address,
        "chains": CHAINS,
    }
    if exclude_risk_token:
        params["excludeRiskToken"] = exclude_risk_token
    return okx_request("GET", "/api/v5/dex/balance/all-token-balances-by-address", params)

def get_transactions_by_address(address:str, token_name:Optional[str]=None, begin:Optional[str]=None, end:Optional[str]=None, cursor:Optional[str]=None, limit:Optional[str]=None)->str:
    """Returns transaction history for an address (optionally filtered by token name/symbol)."""
    address_param = resolve_token_address(CHAIN_INDEX, token_name) if token_name else None
    params = {
        "address": address,
        "chains": CHAINS,
    }
    if address_param:
        params["tokenContractAddress"] = address_param
    if begin:
        params["begin"] = begin
    if end:
        params["end"] = end
    if cursor:
        params["cursor"] = cursor
    if limit:
        params["limit"] = limit
    return okx_request("GET", "/api/v5/dex/post-transaction/transactions-by-address", params)


# --- Solana swap execution placeholder (replace with your Solana SDK in production) ---
def execute_swap(
    token_from_name:str,
    token_to_name:str,
    amount:str,
    user_wallet_address:Optional[str]=None,
    fee_percent:str="1",
    price_tolerance:str="0",
    auto_slippage:str="false",
    slippage:str="0.01",
    path_num:str="3",
):
    """
    Execute a swap by token name (not address), with private key signature.
    Automatically resolves token addresses, validates pair, gets quote, builds and sends transaction.
    Raises ValueError if token or pair is invalid, or if execution fails.
    This is a placeholder—replace with your Solana SDK integration.
    """
    time.sleep(1)
    from_address = resolve_token_address(CHAIN_NAME, token_from_name)
    time.sleep(1)
    to_address = resolve_token_address(CHAIN_NAME, token_to_name)
    time.sleep(1)

    quote = get_swap_quote(token_from_name, token_to_name, int(amount), float (slippage))
    if not quote.get("data"):
        raise ValueError("No valid quote received")
    time.sleep(1)
    instructions = get_swap_instructions(
        token_from_name, token_to_name, int(amount), float(slippage), user_wallet_address,
        int(fee_percent), int(price_tolerance), auto_slippage, int(path_num),
    )
    if not instructions.get("data"):
        raise ValueError("No swap instructions received")

    # Placeholder for Solana TX building/signing/submission
    # Replace with your preferred Solana SDK (e.g., solana-py, solders)
    return instructions

# --- Example usage ---
if __name__ == "__main__":
    # Example: Get supported chains
    # print("Supported chains:", get_supported_chains())
    # print(search_chain("xlayer"))
    
    # print(get_tokens_by_chain("xLayer"))
    # print(resolve_token_address("xlayer","okb"))
    # print(get_token_price("usdt"))
    print(get_all_token_balances("0xe26B62d6113659527c7cB3eDf4c1F660BE25dd70"))
    # print(get_token_price("okb"))
    # print(get_historical_candles("okb"))
    # print(get_supported_cross_chain_tokens("xLayer"))
    # print(get_bridge_token_pairs("xLayer"))
    # print(is_valid_bridge_pair("xlayer","sol","usdt","sol"))
    # print(get_swap_quote("usdt","okb",10))
    # print(get_transactions_by_address("0xe26B62d6113659527c7cB3eDf4c1F660BE25dd70"))
    # print(execute_solana_swap("usdt","okb",10,"0xe26B62d6113659527c7cB3eDf4c1F660BE25dd70"))
    pass