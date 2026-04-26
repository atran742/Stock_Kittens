from datetime import datetime, timedelta
import re
from langchain_ollama import OllamaLLM

from tools import get_price_history, get_news_headlines, LR_predict_future_price, get_politician_signal

from memory import StockChatMemory

llm = OllamaLLM(model="llama3.2")

#so users can type in the company name or the ticker name 
def get_ticker_from_input(user_input: str) -> str:
    """Uses the LLM to convert a company name or phrase into a stock ticker."""
    #strip the word 'analyze' to get just the subject
    subject = user_input.lower().replace("analyze", "").strip()
    
    prompt = f"""
    The user wants to analyze a company. Extract the official stock ticker symbol. If they give you a ticker, just respond back the ticker the user gave.
    User input: "{subject}"
    
    Respond with ONLY the ticker symbol (e.g., AAPL, TSLA, MSFT). 
    If you are unsure, respond with 'UNKNOWN'.
    """
    response = llm.invoke(prompt).strip().upper()
    #Remove any extra text or punctuation Llama might add
    return response.split()[0].replace(".", "")

def build_prompt(
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
    price_change_text = "Unknown"
    percent_change_text = "Unknown"

    predicted_price_text = "Unknown"
    if predicted_price is not None and current_price != 0:
        predicted_price_text = f"{predicted_price:.2f}"
        change = predicted_price - current_price
        pct_change = (change / current_price) * 100
        price_change_text = f"{change:.2f}"
        percent_change_text = f"{pct_change:.2f}%"

    # Summarize recent prices
    if recent_prices:
        start_date = recent_prices[0]['date']
        end_date = recent_prices[-1]['date']
        start_price = recent_prices[0]['close']
        end_price = recent_prices[-1]['close']
        overall_change = ((end_price - start_price) / start_price) * 100
        
        # Calculate period length in months from actual date range
        from datetime import datetime
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days_diff = (end_dt - start_dt).days
        months_diff = max(1, round(days_diff / 30.0))  # Use float division
        
        period_text = f"{months_diff} month{'s' if months_diff != 1 else ''}"
        
        price_summary = f"Price trend over the past {period_text}: ${start_price:.2f} to ${end_price:.2f} ({overall_change:+.2f}%). "
        
        if len(recent_prices) > 1:
            first_half = recent_prices[:len(recent_prices)//2]
            second_half = recent_prices[len(recent_prices)//2:]
            avg_first = sum(p['close'] for p in first_half) / len(first_half)
            avg_second = sum(p['close'] for p in second_half) / len(second_half)
            recent_trend = "upward" if avg_second > avg_first else "downward" if avg_second < avg_first else "sideways"
            price_summary += f"Recent trend: {recent_trend} (comparing first vs second half of period)."
    else:
        price_summary = "No recent price data available."

    # Summarize headlines
    if headlines:
        headline_summary = f"Recent news ({len(headlines)} articles): " + "; ".join(headlines[:5])  # Limit to 5 headlines
        if len(headlines) > 5:
            headline_summary += f" and {len(headlines) - 5} more."
    else:
        headline_summary = "No recent news headlines found."

    return f"""
You are a stock analysis assistant.

Your task is to provide a clear verdict followed by a brief justification BASED SOLELY ON THE PROVIDED DATA BELOW.

CRITICAL: You MUST analyze the actual price data, news, and prediction provided. Do NOT make up trends or data that contradict the information given.

Important rules:
- Start your response with ONLY the word BUY, HOLD, or SELL on the first line.
- Base your decision on the actual price trend shown (upward/downward/sideways).
- Consider the predicted price change.
- Be cautious and realistic.
- If the evidence is mixed, prefer HOLD.

You MUST reference the specific data provided:
- Mention the actual price change direction and percentage
- Reference the news headlines summary
- Consider the predicted change

Respond in exactly this format:

VERDICT: [BUY, HOLD, or SELL]
MY PREDICTED PRICE for {future_date} ({days_ahead} days from now): ${predicted_price_text}
REASON: [One short paragraph explaining why, citing the specific price trend and news. When mentioning predictions, always use "MY PREDICTED PRICE" (in all caps) and make it clear this is your own analysis.]





Stock: {ticker}
Current Price: {current_price:.2f}
Predicted Price in {days_ahead} days ({future_date}): {predicted_price_text} (trained on {training_period} of historical data)
Predicted Change: {price_change_text}
Predicted Percent Change: {percent_change_text}

Price History Summary: {price_summary}

News Headlines Summary: {headline_summary}

Politician Signal: {political_signal}
""".strip()





def process_user_message(user_input: str, session_id: str) -> str:
    """Process a user message and return the LLM response."""
    db = StockChatMemory()
    past_messages = db.get_history(session_id, limit=10)
    context_string = "\n".join([f"{m[0]}: {m[1]}" for m in past_messages])

    # Initial prompt that allows the AI to request stock analysis with parameters
    initial_prompt = f"""You are an AI stock analyst assistant. You can analyze stocks by requesting data.

Previous conversation:
{context_string}

Current user message: {user_input}

If you want to analyze a specific stock, respond with "ANALYZE_STOCK: TICKER" followed by optional parameters.
Available parameters:
- days_ahead=N (1-365, default 14): days to predict into the future
- training_period=X (1mo|3mo|6mo|12mo|2y|5y, default 6mo): historical data period to train on
- interval=X (1d|1wk|1mo, default 1d): data granularity

Examples:
- "ANALYZE_STOCK: AAPL"
- "ANALYZE_STOCK: TSLA, days_ahead=30"
- "ANALYZE_STOCK: MSFT, days_ahead=7, training_period=3mo, interval=1wk"

Otherwise, respond normally to the user's message.

Assistant:"""

    initial_response = llm.invoke(initial_prompt)

    # Check if the AI wants to analyze a stock
    if "ANALYZE_STOCK:" in initial_response:
        # Parse ticker and parameters
        try:
            # Extract the part after ANALYZE_STOCK:
            analyze_part = initial_response.split("ANALYZE_STOCK:")[1].strip()
            
            # Split by comma to get ticker and parameters
            parts = [p.strip() for p in analyze_part.split(',')]
            ticker = parts[0].upper().replace(".", "").replace(",", "")
            
            # Default parameters
            days_ahead = 14
            training_period = "6mo"
            interval = "1d"
            
            # Parse additional parameters with validation
            for part in parts[1:]:
                if part.startswith("days_ahead="):
                    try:
                        val = int(part.split("=")[1])
                        if 1 <= val <= 365:  # Reasonable range
                            days_ahead = val
                    except:
                        pass
                elif part.startswith("training_period="):
                    val = part.split("=")[1]
                    if val in ["1mo", "3mo", "6mo", "12mo", "2y", "5y"]:  # Valid periods
                        training_period = val
                elif part.startswith("interval="):
                    val = part.split("=")[1]
                    if val in ["1d", "1wk", "1mo"]:  # Valid intervals
                        interval = val
                    
        except:
            ticker = "UNKNOWN"
            days_ahead = 14
            training_period = "6mo"
            interval = "1d"

        if ticker == "UNKNOWN":
            final_response = "I wanted to analyze a stock but couldn't identify the ticker symbol."
        else:
            # Fetch data and build analysis with custom parameters
            try:
                future_date = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

                prices = get_price_history(ticker, period="3mo", interval="1d")  # Keep 3mo for summary, but use custom training for prediction
                if not prices:
                    final_response = f"I couldn't find price data for {ticker}."
                else:
                    headlines = get_news_headlines(ticker)
                    predicted_price = LR_predict_future_price(
                        ticker=ticker,
                        future_date=future_date,
                        training_period=training_period,
                        interval=interval,
                    )
                    current_price = prices[-1]["close"]

                    pol_signal = get_politician_signal(ticker, future_date)

                    analysis_data = build_prompt(
                        ticker, current_price, predicted_price,
                        future_date, prices, headlines, days_ahead, training_period, political_signal
                    )

                    # Final prompt with analysis data
                    final_prompt = f"""Based on the stock analysis data below, provide your final response to the user.

Previous conversation:
{context_string}

User: {user_input}

Analysis Data:
{analysis_data}

Provide a helpful response that includes the analysis verdict and reasoning:"""

                    final_response = llm.invoke(final_prompt)

            except Exception as e:
                final_response = f"Error analyzing {ticker}: {str(e)}"
    else:
        # Normal response without analysis
        final_response = initial_response

    # Save the conversation
    db.save_message(session_id, "User", user_input)
    db.save_message(session_id, "Assistant", final_response)

    return final_response


def format_response(response: str) -> str:
    """Clean the LLM response to remove trailing notes or meta comments."""
    if not response:
        return response

    # Remove any trailing Note: section or similar extra commentary
    cleaned = re.split(r"\nNote:|\n\nNote:|\nAs per your request|\nNote\s*:", response, maxsplit=1)[0].strip()

    # If there are extra blank-line-separated sections after the main content, keep only the first block.
    if "\n\n" in cleaned:
        cleaned = cleaned.split("\n\n", 1)[0].strip()

    return cleaned

def main() -> None:
    session_id = "user_1"

    print("--- AI Stock Analyst ---")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]: break

        response = process_user_message(user_input, session_id)
        formatted_response = format_response(response)

        print(f"\nAgent: {formatted_response}")

    
def analyze_stock_for_api(user_input: str, session_id: str = "web_user") -> str:
    """Called by FastAPI to process a chat message and return a response."""
    response = process_user_message(user_input, session_id)
    return format_response(response)

if __name__ == "__main__":
    main()