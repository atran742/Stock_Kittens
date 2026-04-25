import yfinance as yf
from datetime import datetime
from sklearn.linear_model import LinearRegression

def get_price_history(ticker: str, period: str = "1mo", interval: str = "1d") -> list[dict]:
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)

    if hist.empty: return []

    rows = []
    for date, row in hist.iterrows():
        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })

    return rows

def get_news_headlines(ticker: str, limit: int = 3) -> list[str]:
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news

        if not news_items:
            return []

        headlines = []

        for story in news_items[:limit]:
            if isinstance(story, dict):
                content = story.get("content", {})
                title = content.get("title")
                if title:
                    headlines.append(title)

        return headlines

    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []
    
def LR_predict_future_price(ticker: str, future_date: str, training_period: str = "6mo", interval: str = "1d") -> float | None:
    prices = get_price_history(ticker, period=training_period, interval=interval)
    
    if len(prices) < 2: return None

    dates = [datetime.strptime(p["date"], "%Y-%m-%d") for p in prices]
    closes = [p["close"] for p in prices]

    first_date = dates[0]

    X = [ [ (d - first_date).days ] for d in dates ]

    model = LinearRegression().fit(X, closes)

    target_date = datetime.strptime(future_date, "%Y-%m-%d")
    target_days = (target_date - first_date).days

    return float( model.predict( [[target_days]] )[0] )

def get_trending_stocks() -> list[dict]:
    """
    Fetches the most actively traded / trending stocks on Yahoo Finance.
    Returns price, change, and volume for each.
    """
    try:
        # Yahoo Finance trending tickers
        trending = yf.screen("most_actives", size=10)
        results = []

        for quote in trending.get("quotes", []):
            ticker = quote.get("symbol", "")
            name   = quote.get("shortName", ticker)
            price  = quote.get("regularMarketPrice", 0)
            change = quote.get("regularMarketChange", 0)
            pct    = quote.get("regularMarketChangePercent", 0)
            volume = quote.get("regularMarketVolume", 0)

            results.append({
                "ticker": ticker,
                "name":   name,
                "price":  round(price, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
                "volume": volume,
            })

        return results

    except Exception as e:
        print(f"Error fetching trending stocks: {e}")
        return []
