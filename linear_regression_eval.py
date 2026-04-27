from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sys

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LinearRegression

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit(
        "This script requires yfinance. Install it with: pip install yfinance"
    ) from exc


TICKERS = ["NVDA", "AMD", "AAPL"]
TRAINING_MONTHS = 6
MIN_TRAINING_ROWS = 20
TEST_POINTS = 30


@dataclass
class RollingPrediction:
    date: str
    actual_close: float
    predicted_close: float
    abs_error: float
    pct_error: float


@dataclass
class LREvalResult:
    ticker: str
    rows_total: int
    predictions_made: int
    test_window_days: int
    mean_abs_error: float
    mean_pct_error: float
    rmse: float
    predictions: list[RollingPrediction]


def fetch_history(ticker: str) -> pd.DataFrame:
    hist = yf.Ticker(ticker).history(period="18mo", interval="1d", auto_adjust=False)
    if hist.empty or len(hist) < 120:
        raise ValueError(f"Not enough price history returned for {ticker}")

    hist = hist.reset_index()
    hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
    hist = hist[["Date", "Close"]].dropna().sort_values("Date").reset_index(drop=True)
    return hist


def predict_for_date(history: pd.DataFrame, target_idx: int) -> RollingPrediction:
    target_row = history.iloc[target_idx]
    target_date = target_row["Date"]
    training_start = target_date - pd.DateOffset(months=TRAINING_MONTHS)

    train = history[(history["Date"] >= training_start) & (history["Date"] < target_date)].copy()
    if len(train) < MIN_TRAINING_ROWS:
        raise ValueError("Not enough training data for rolling prediction")

    first_date = train.iloc[0]["Date"]
    X_train = (train["Date"] - first_date).dt.days.to_numpy().reshape(-1, 1)
    y_train = train["Close"].to_numpy()

    model = LinearRegression()
    model.fit(X_train, y_train)

    target_days = int((target_date - first_date).days)
    predicted = float(model.predict([[target_days]])[0])
    actual = float(target_row["Close"])
    abs_error = abs(predicted - actual)
    pct_error = abs_error / actual * 100 if actual else float("nan")

    return RollingPrediction(
        date=target_date.strftime("%Y-%m-%d"),
        actual_close=round(actual, 4),
        predicted_close=round(predicted, 4),
        abs_error=round(abs_error, 4),
        pct_error=round(pct_error, 4),
    )


def evaluate_ticker(ticker: str) -> tuple[LREvalResult, pd.DataFrame]:
    history = fetch_history(ticker)

    start_idx = max(len(history) - TEST_POINTS, 0)
    rolling_predictions: list[RollingPrediction] = []

    for idx in range(start_idx, len(history)):
        target_date = history.iloc[idx]["Date"]
        training_start = target_date - pd.DateOffset(months=TRAINING_MONTHS)
        train = history[(history["Date"] >= training_start) & (history["Date"] < target_date)]
        if len(train) < MIN_TRAINING_ROWS:
            continue
        rolling_predictions.append(predict_for_date(history, idx))

    if not rolling_predictions:
        raise ValueError(f"No rolling predictions could be created for {ticker}")

    abs_errors = [p.abs_error for p in rolling_predictions]
    pct_errors = [p.pct_error for p in rolling_predictions]
    rmse = (sum(err * err for err in abs_errors) / len(abs_errors)) ** 0.5

    result = LREvalResult(
        ticker=ticker,
        rows_total=int(len(history)),
        predictions_made=len(rolling_predictions),
        test_window_days=TEST_POINTS,
        mean_abs_error=round(sum(abs_errors) / len(abs_errors), 4),
        mean_pct_error=round(sum(pct_errors) / len(pct_errors), 4),
        rmse=round(rmse, 4),
        predictions=rolling_predictions,
    )
    return result, history


def plot_recent_window_chart(ticker: str, history: pd.DataFrame, result: LREvalResult) -> None:
    pred_df = pd.DataFrame([asdict(p) for p in result.predictions])
    pred_df["date"] = pd.to_datetime(pred_df["date"])

    window_start = pred_df["date"].min() - pd.Timedelta(days=7)
    recent_history = history[history["Date"] >= window_start].copy()

    plt.figure(figsize=(11, 6))
    plt.plot(recent_history["Date"], recent_history["Close"], linewidth=1.8, label="Actual close")
    plt.plot(pred_df["date"], pred_df["predicted_close"], marker="o", linewidth=1.5, label="Predicted close")
    plt.plot(pred_df["date"], pred_df["actual_close"], marker="x", linewidth=1.5, label="Actual close (test window)")
    plt.title(f"{ticker} Rolling 6-Month Backtest - Recent Window")
    plt.xlabel("Date")
    plt.ylabel("Close Price")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    plt.close()



def plot_predicted_vs_actual_only(ticker: str, result: LREvalResult) -> None:
    pred_df = pd.DataFrame([asdict(p) for p in result.predictions])
    pred_df["date"] = pd.to_datetime(pred_df["date"])

    plt.figure(figsize=(11, 6))
    plt.plot(pred_df["date"], pred_df["actual_close"], marker="x", linewidth=1.8, label="Actual close")
    plt.plot(pred_df["date"], pred_df["predicted_close"], marker="o", linewidth=1.8, label="Predicted close")
    plt.title(f"{ticker} Predicted vs Actual - Test Window Only")
    plt.xlabel("Date")
    plt.ylabel("Close Price")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    plt.close()



def plot_error_chart(results: list[LREvalResult]) -> None:
    tickers = [r.ticker for r in results]
    mae_values = [r.mean_abs_error for r in results]
    rmse_values = [r.rmse for r in results]

    x = range(len(tickers))
    width = 0.35

    plt.figure(figsize=(9, 6))
    plt.bar([i - width / 2 for i in x], mae_values, width=width, label="Mean Abs Error")
    plt.bar([i + width / 2 for i in x], rmse_values, width=width, label="RMSE")
    plt.title("Linear Regression Rolling Backtest Error Summary")
    plt.xlabel("Ticker")
    plt.ylabel("Error")
    plt.xticks(list(x), tickers)
    plt.legend()
    plt.tight_layout()
    plt.show()
    plt.close()



def main() -> None:
    results: list[LREvalResult] = []

    for ticker in TICKERS:
        result, history = evaluate_ticker(ticker)
        results.append(result)
        plot_recent_window_chart(ticker, history, result)
        plot_predicted_vs_actual_only(ticker, result)

    average_metrics = {
        "mean_abs_error": round(sum(r.mean_abs_error for r in results) / len(results), 4),
        "mean_pct_error": round(sum(r.mean_pct_error for r in results) / len(results), 4),
        "rmse": round(sum(r.rmse for r in results) / len(results), 4),
    }
    plot_error_chart(results)

    payload = {
        "model": "LinearRegression",
        "evaluation": "Rolling backtest: for each ticker, use the prior 6 months of daily closes to predict each of the last 30 trading days.",
        "tickers": TICKERS,
        "per_ticker": [asdict(r) for r in results],
        "average_metrics": average_metrics,
    }

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        raise
