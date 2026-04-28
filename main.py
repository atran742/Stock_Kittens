from datetime import datetime, timedelta
import re
from langchain_ollama import OllamaLLM

from tools import get_price_history, get_news_headlines, LR_predict_future_price, get_politician_signal
from memory import StockChatMemory

llm = OllamaLLM(model="llama3.2")


def get_tickers_from_input(user_input: str) -> list[str]:
    """
    Extract one or more tickers from user input.
    Returns a list so comparison requests ("analyze X and Y") work correctly.
    """
    prompt = f"""Extract all stock tickers from this request: "{user_input}"
    
Rules:
- Return ONLY ticker symbols separated by commas (e.g. AAPL, MSFT)
- If only one company is mentioned, return one ticker
- Map company names to their correct ticker (Apple→AAPL, Microsoft→MSFT, Google→GOOGL, etc.)
- Return UNKNOWN if no valid stock can be identified
- No explanation, no punctuation other than commas between tickers"""

    response = llm.invoke(prompt).strip().upper()
    matches = re.findall(r'\b[A-Z]{1,5}\b', response)
    
    # Massively expanded noise word filter
    noise_words = {
        "I", "A", "THE", "AND", "OR", "FOR", "TO", "IN", "OF", "IF", "IT", "MY", "NO",
        "IS", "ARE", "WAS", "BE", "AT", "BY", "AN", "AS", "ON", "UP", "DO", "GO",
        "ALL", "ANY", "CAN", "DID", "GET", "GOT", "HAS", "HAD", "HIM", "HIS", "HOW",
        "ITS", "LET", "MAY", "NOT", "NOW", "OUR", "OUT", "OWN", "SAY", "SHE", "SO",
        "TOO", "TWO", "USE", "WAS", "WAY", "WE", "WHO", "WHY", "WILL", "WITH", "YES",
        "YOU", "YOUR", "THAT", "THIS", "THEY", "FROM", "HAVE", "BEEN", "WERE", "SAID",
        "EACH", "WHEN", "WHAT", "SOME", "THAN", "THEN", "THEM", "ALSO", "INTO", "OVER",
        "AFTER", "BACK", "GOOD", "LIST", "STOCK", "STOCKS", "APPLE", "THERE", "WHICH",
        "ABOUT", "WOULD", "COULD", "THEIR", "THESE", "OTHER", "BEING", "WHERE", "WHILE",
        "SHOULD", "BEFORE", "TICKER", "SYMBOL", "COMPANY", "MARKET", "TRADE", "PRICE"
    }
    
    candidates = [m for m in matches if m not in noise_words]
    
    if not candidates:
        return ["UNKNOWN"]
    
    # Validate each candidate by actually checking if Yahoo Finance has data for it
    # This is the key fix — if we can't get price data, it's not a real ticker
    valid_tickers = []
    for candidate in candidates:
        prices = get_price_history(candidate, period="5d", interval="1d")
        if prices:
            valid_tickers.append(candidate)
        else:
            print(f"[!] Rejected '{candidate}' — no market data found, skipping.")
    
    return valid_tickers if valid_tickers else ["UNKNOWN"]


def build_analysis_prompt(
    ticker: str,
    current_price: float,
    predicted_price: float | None,
    future_date: str,
    recent_prices: list[dict],
    headlines: list[str],
    days_ahead: int = 14,
    training_period: str = "6mo",
    political_signal: str = "HOLD"
) -> str:
    predicted_price_text = "Unknown"
    price_change_text = "Unknown"
    percent_change_text = "Unknown"

    if predicted_price is not None and current_price != 0:
        predicted_price_text = f"{predicted_price:.2f}"
        change = predicted_price - current_price
        pct_change = (change / current_price) * 100
        price_change_text = f"{change:+.2f}"
        percent_change_text = f"{pct_change:+.2f}%"

    if recent_prices:
        start_price = recent_prices[0]['close']
        end_price = recent_prices[-1]['close']
        start_date = recent_prices[0]['date']
        end_date = recent_prices[-1]['date']
        overall_change = ((end_price - start_price) / start_price) * 100
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        months_diff = max(1, round((end_dt - start_dt).days / 30.0))
        period_text = f"{months_diff} month{'s' if months_diff != 1 else ''}"
        price_summary = (
            f"${start_price:.2f} → ${end_price:.2f} over {period_text} "
            f"({overall_change:+.2f}%)"
        )
        if len(recent_prices) > 1:
            mid = len(recent_prices) // 2
            avg_first = sum(p['close'] for p in recent_prices[:mid]) / mid
            avg_second = sum(p['close'] for p in recent_prices[mid:]) / (len(recent_prices) - mid)
            trend = "upward" if avg_second > avg_first else "downward" if avg_second < avg_first else "sideways"
            price_summary += f", recent trend: {trend}"
    else:
        price_summary = "No price data available"

    if headlines:
        headline_list = "\n".join(f'  - "{h}"' for h in headlines[:5])
    else:
        headline_list = "  - No recent headlines found"

    # Sanitize political signal in case of upstream errors
    safe_pol_signal = political_signal if "error" not in str(political_signal).lower() and "not defined" not in str(political_signal).lower() else "DATA UNAVAILABLE"

    return f"""[ANALYSIS DATA: {ticker}]
Current Price:   ${current_price:.2f}
Predicted Price: ${predicted_price_text} by {future_date} ({price_change_text} / {percent_change_text})
Political Signal: {safe_pol_signal}
Price History:   {price_summary}
Headlines:
{headline_list}"""


def run_single_analysis(ticker: str, days_ahead: int = 14, training_period: str = "6mo", interval: str = "1d") -> tuple[str, str]:
    """
    Runs a full analysis for one ticker.
    Returns (ticker, analysis_data_string) or (ticker, error_message).
    """
    future_date = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    prices = get_price_history(ticker, period=training_period, interval=interval)

    if not prices:
        return ticker, f"No price data found for {ticker} — it may be delisted or misspelled."

    headlines = get_news_headlines(ticker)
    predicted_price = LR_predict_future_price(
        ticker=ticker,
        future_date=future_date,
        training_period=training_period,
        interval=interval,
    )
    current_price = prices[-1]["close"]

    try:
        pol_signal = get_politician_signal(ticker, future_date)
    except Exception:
        pol_signal = "DATA UNAVAILABLE"

    analysis_data = build_analysis_prompt(
        ticker=ticker,
        current_price=current_price,
        predicted_price=predicted_price,
        future_date=future_date,
        recent_prices=prices,
        headlines=headlines,
        days_ahead=days_ahead,
        training_period=training_period,
        political_signal=pol_signal,
    )
    return ticker, analysis_data


def process_user_message(user_input: str, session_id: str) -> str:
    db = StockChatMemory()
    past_messages = db.get_history(session_id, limit=4)
    context_string = "\n".join([f"{role}: {msg}" for role, msg in past_messages])

    is_analysis_request = "analyze" in user_input.lower()

    if is_analysis_request:
        tickers = get_tickers_from_input(user_input)

        if tickers == ["UNKNOWN"]:
            final_response = (
                "I couldn't identify which stock(s) you want to analyze. "
                "Try using the ticker directly, e.g. 'analyze AAPL' or 'analyze Apple and Microsoft'."
            )
        else:
            # Run analysis for each ticker found
            all_analysis_blocks = []
            failed = []

            for ticker in tickers:
                print(f"[*] Analyzing {ticker}...")
                t, result = run_single_analysis(ticker)
                if result.startswith("No price data"):
                    failed.append(f"{t}: {result}")
                else:
                    all_analysis_blocks.append(result)

            if not all_analysis_blocks:
                final_response = "\n".join(failed)
            else:
                combined_data = "\n\n".join(all_analysis_blocks)
                is_comparison = len(all_analysis_blocks) > 1

                comparison_instruction = (
                    "\nAfter giving individual verdicts for each ticker, "
                    "add a brief COMPARISON section stating which has better predicted growth and why."
                    if is_comparison else ""
                )

                # Build the list of tickers actually analyzed this turn
                analyzed_tickers = [block.split("\n")[0].replace("[ANALYSIS DATA: ", "").replace("]", "") 
                                for block in all_analysis_blocks]
                tickers_this_turn = ", ".join(analyzed_tickers)

                final_prompt = f"""You are a direct, expert Stock Analyst.
                Using the analysis data below, respond to the user's request.

                STRICT RULES — violations will confuse the user:
                - Only give verdicts for these exact tickers: {tickers_this_turn}
                - NEVER mention or compare any ticker not present in the Analysis Data below
                - NEVER invent price figures, percentages, or trends not present in the Analysis Data below
                - All numbers you cite MUST come directly from the Analysis Data section
                - Always give a clear BUY, HOLD, or SELL verdict. Default to HOLD if uncertain.
                - Never say "I cannot provide financial advice."
                - Be concise and structured.{comparison_instruction}

                Conversation History (for follow-up context only — do NOT pull stock data from here):
                {context_string}

                User Request: {user_input}

                Analysis Data (your ONLY source of truth for this response):
                {combined_data}
                """
                final_response = llm.invoke(final_prompt)

                if failed:
                    final_response += "\n\n" + "\n".join(failed)

    else:
        # For follow-up questions, tell the LLM to prioritize the MOST RECENT analysis in history
        general_prompt = f"""You are a knowledgeable financial assistant and stock analyst.

Rules:
- Use the conversation history below to answer follow-up questions accurately.
- When the user says "that verdict" or "that stock", they mean the MOST RECENTLY analyzed ticker in history.
- Cite the specific headline or data point from the most recent analysis when asked to justify a verdict.
- If asked for stock recommendations without a ticker, suggest they ask you to "analyze [company name]".
- Be concise and direct.

Conversation History (most recent is at the bottom):
{context_string}

User: {user_input}
Assistant:"""
        final_response = llm.invoke(general_prompt)

    db.save_message(session_id, "User", user_input)
    db.save_message(session_id, "Assistant", str(final_response))
    return str(final_response)


def format_response(response: str) -> str:
    if not response:
        return response
    # Only strip trailing Note: sections, preserve full structured responses
    cleaned = re.split(r"\n+Note:\s", response, maxsplit=1)[0].strip()
    return cleaned


def main() -> None:
    session_id = "user_1"
    print("--- AI Stock Analyst ---")
    
    db = StockChatMemory()
    existing_count = db.get_session_message_count(session_id)
    
    if existing_count > 0:
        print(f"\n[Memory] Found {existing_count} messages from a previous session.")
        choice = input("Start fresh? (y/n): ").strip().lower()
        if choice == "y":
            db.clear_session(session_id)
            print("[Memory] Session cleared. Starting fresh.\n")
        else:
            print("[Memory] Resuming previous session.\n")

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            break

        response = process_user_message(user_input, session_id)
        print(f"\nAgent: {format_response(response)}")


def analyze_stock_for_api(user_input: str, session_id: str = "web_user") -> str:
    response = process_user_message(user_input, session_id)
    return format_response(response)


if __name__ == "__main__":
    main()