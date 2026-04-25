from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import sys
import os 
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import analyze_stock_for_api



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/market")
def get_market():
    try:
        result = yf.screen("most_actives", size=10)
        stocks = []
        for quote in result.get("quotes", []):
            stocks.append({
                "name":       quote.get("shortName", ""),
                "ticker":     quote.get("symbol", ""),
                "price":      round(quote.get("regularMarketPrice", 0), 2),
                "change":     round(quote.get("regularMarketChange", 0), 2),
                "change_pct": round(quote.get("regularMarketChangePercent", 0), 2),
            })
        return {"indices": stocks}
    except Exception as e:
        print(f"Error fetching trending stocks: {e}")
        return {"indices": [], "error": str(e)}

@app.post("/chat")
async def chat(body: dict):
    message  = body.get("message", "")
    response = analyze_stock_for_api(message)
    return {"response": response}


@app.get("/stats")
def get_stats():
    """Get combined stats for the frontend."""
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'transactions.csv')
    txn_stats = get_transaction_stats(csv_path)
    top_signal = get_top_signal()
    
    return {
        "trades_tracked": txn_stats["trades_tracked"],
        "trades_this_month": txn_stats["trades_this_month"],
        "active_politicians": txn_stats["active_politicians"],
        "politicians_last_month": txn_stats["politicians_last_month"],
        "top_signal": top_signal
    }


def get_transaction_stats(csv_path):
    """Get statistics from the transactions CSV."""
    try:
        df = pd.read_csv(csv_path)
        
        # Filter out rows where key fields are 'FAIL'
        valid_trades = df[df['Transaction Type'] != 'FAIL'].copy()  # Use .copy() to avoid warning
        
        # Total trades tracked
        trades_tracked = len(valid_trades)
        
        # Trades this month
        current_month = datetime.now().strftime('%Y-%m')
        valid_trades['Transaction Date'] = pd.to_datetime(valid_trades['Transaction Date'], errors='coerce')
        trades_this_month = len(valid_trades[valid_trades['Transaction Date'].dt.strftime('%Y-%m') == current_month])
        
        # Active politicians (unique members)
        active_politicians = valid_trades['Member'].nunique()
        
        # Politicians active in the last month
        last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
        politicians_last_month = valid_trades[valid_trades['Transaction Date'].dt.strftime('%Y-%m') >= last_month]['Member'].nunique()
        
        return {
            'trades_tracked': trades_tracked,
            'trades_this_month': trades_this_month,
            'active_politicians': active_politicians,
            'politicians_last_month': politicians_last_month
        }
    except Exception as e:
        print(f"Error reading transaction stats: {e}")
        return {
            'trades_tracked': 0,
            'trades_this_month': 0,
            'active_politicians': 0,
            'politicians_last_month': 0
        }


def get_top_signal():
    """Get the top trading signal based on recent transactions."""
    try:
        # For simplicity, let's pick a popular stock and get some basic info
        ticker = 'AAPL'  # Could be randomized or based on actual data
        
        # Get current price
        stock = yf.Ticker(ticker)
        current_price = stock.history(period='1d')['Close'].iloc[-1]
        
        # Simple prediction: assume 5% increase in 14 days
        predicted_price = current_price * 1.05
        predicted_change = 5.0
        days_ahead = 14
        future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        return {
            'signal': 'BUY',
            'ticker': ticker,
            'predicted_price': round(predicted_price, 2),
            'predicted_change': predicted_change,
            'current_price': round(current_price, 2),
            'days_ahead': days_ahead,
            'future_date': future_date
        }
    except Exception as e:
        print(f"Error getting top signal: {e}")
        return {
            'signal': 'HOLD',
            'ticker': 'UNKNOWN',
            'predicted_price': 0.0,
            'predicted_change': 0.0,
            'current_price': 0.0,
            'days_ahead': 14,
            'future_date': datetime.now().strftime('%Y-%m-%d')
        }