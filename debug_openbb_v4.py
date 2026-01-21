try:
    from openbb import obb
    print("OPENBB IMPORTED SUCCESSFULLY")
    
    # Minimal test of equity module which caused the crash
    print("Testing equity.profile...")
    try:
        res = obb.equity.profile(symbol="AAPL", provider="yfinance")
        print("Profile fetch success")
    except Exception as e:
        print(f"Profile fetch failed: {e}")

except Exception as e:
    print(f"FATAL IMPORT ERROR: {e}")
