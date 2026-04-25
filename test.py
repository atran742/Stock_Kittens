from tools import get_news_headlines

def test_get_news_headlines():
    # Test with a valid ticker
    headlines = get_news_headlines("AAPL", limit=3)
    print("Headlines for AAPL:")
    for headline in headlines:
        print(f"- {headline}")
    
    # Test with invalid ticker
    headlines_invalid = get_news_headlines("INVALID", limit=3)
    print("Headlines for INVALID:")
    for headline in headlines_invalid:
        print(f"- {headline}")

if __name__ == "__main__":
    test_get_news_headlines()