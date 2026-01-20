
import yfinance as yf
import json
import sys

def debug_yahoo(symbol):
    print(f"Fetching data for {symbol}...")
    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info
    except Exception as e:
        print(f"Error fetching info: {e}")
        return

    keys_to_check = [
        'trailingPE', 'priceToBook', 'priceToSalesTrailing12Months', 
        'trailingEps', 'bookValue', 'dividendYield',
        'forwardEps', 'forwardPE', 'marketCap'
    ]
    
    print("\n--- Targeted Keys ---")
    for k in keys_to_check:
        val = info.get(k)
        print(f"{k}: {val} (Type: {type(val)})")
        
    print("\n--- saving raw info to debug_goog_info.json ---")
    with open("debug_goog_info.json", "w") as f:
        json.dump(info, f, indent=4)

if __name__ == "__main__":
    debug_yahoo("GOOG")
