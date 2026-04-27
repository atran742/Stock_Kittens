from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder


CSV_PATH = "transactions.csv"
TICKERS = ["NVDA", "AMD", "AAPL"]
POSITIVE_LABEL = "P"
NEGATIVE_LABEL = "S"


@dataclass
class PoliticianEvalResult:
    ticker: str
    rows_used: int
    train_rows: int
    test_rows: int
    tp: int
    tn: int
    fp: int
    fn: int
    accuracy: float
    precision: float
    recall: float
    f1: float


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")
    df = df.dropna(subset=["Transaction Date", "Member", "Transaction Type"])
    df = df[df["Transaction Type"].isin([POSITIVE_LABEL, NEGATIVE_LABEL])].copy()
    df = df.sort_values("Transaction Date").reset_index(drop=True)

    df["month"] = df["Transaction Date"].dt.month
    df["day"] = df["Transaction Date"].dt.day

    le_member = LabelEncoder()
    df["member_encoded"] = le_member.fit_transform(df["Member"].astype(str))

    X = df[["member_encoded", "month", "day"]]
    y = df["Transaction Type"]
    return X, y


def evaluate_ticker(df_all: pd.DataFrame, ticker: str) -> tuple[PoliticianEvalResult, list[str], list[str]]:
    df = df_all[df_all["Ticker"] == ticker].copy()
    X, y = build_features(df)

    if len(X) < 10:
        raise ValueError(f"Not enough usable politician trades for {ticker}: {len(X)} rows")

    split_idx = max(int(len(X) * 0.8), 1)
    if split_idx >= len(X):
        split_idx = len(X) - 1

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    cm = confusion_matrix(y_test, y_pred, labels=[POSITIVE_LABEL, NEGATIVE_LABEL])
    tp = int(cm[0, 0])
    fn = int(cm[0, 1])
    fp = int(cm[1, 0])
    tn = int(cm[1, 1])

    result = PoliticianEvalResult(
        ticker=ticker,
        rows_used=int(len(X)),
        train_rows=int(len(X_train)),
        test_rows=int(len(X_test)),
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        accuracy=round(float(accuracy_score(y_test, y_pred)), 4),
        precision=round(float(precision_score(y_test, y_pred, pos_label=POSITIVE_LABEL, zero_division=0)), 4),
        recall=round(float(recall_score(y_test, y_pred, pos_label=POSITIVE_LABEL, zero_division=0)), 4),
        f1=round(float(f1_score(y_test, y_pred, pos_label=POSITIVE_LABEL, zero_division=0)), 4),
    )
    return result, list(y_test), list(y_pred)


def plot_confusion_per_ticker(results_with_preds: list[tuple[PoliticianEvalResult, list[str], list[str]]]) -> None:
    for r, y_true, y_pred in results_with_preds:
        cm = confusion_matrix(y_true, y_pred, labels=[POSITIVE_LABEL, NEGATIVE_LABEL])
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Buy (P)", "Sell (S)"])

        fig, ax = plt.subplots(figsize=(6, 5))
        disp.plot(ax=ax, colorbar=False)
        ax.set_title(f"{r.ticker} Confusion Matrix")
        fig.tight_layout()
        plt.show()
        plt.close(fig)


def plot_average_confusion(avg_confusion_matrix: dict[str, float]) -> None:
    cm = np.array([
        [avg_confusion_matrix["tp"], avg_confusion_matrix["fn"]],
        [avg_confusion_matrix["fp"], avg_confusion_matrix["tn"]],
    ])
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Buy (P)", "Sell (S)"])

    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(ax=ax, values_format=".2f", colorbar=False)
    ax.set_title("Average Confusion Matrix Across NVDA, AMD, AAPL")
    fig.tight_layout()
    plt.show()
    plt.close(fig)


def plot_metric_summary(results: list[PoliticianEvalResult]) -> None:
    tickers = [r.ticker for r in results]
    accuracies = [r.accuracy for r in results]
    precisions = [r.precision for r in results]
    recalls = [r.recall for r in results]
    f1s = [r.f1 for r in results]

    x = list(range(len(tickers)))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - 1.5 * width for i in x], accuracies, width=width, label="Accuracy")
    ax.bar([i - 0.5 * width for i in x], precisions, width=width, label="Precision")
    ax.bar([i + 0.5 * width for i in x], recalls, width=width, label="Recall")
    ax.bar([i + 1.5 * width for i in x], f1s, width=width, label="F1")
    ax.set_title("Politician Model Metrics by Ticker")
    ax.set_xlabel("Ticker")
    ax.set_ylabel("Score")
    ax.set_xticks(x, tickers)
    ax.legend()
    fig.tight_layout()
    plt.show()
    plt.close(fig)


def main() -> None:
    df_all = pd.read_csv(CSV_PATH)
    results_with_preds = [evaluate_ticker(df_all, ticker) for ticker in TICKERS]
    results = [item[0] for item in results_with_preds]

    avg_confusion_matrix = {
        "tp": round(sum(r.tp for r in results) / len(results), 4),
        "tn": round(sum(r.tn for r in results) / len(results), 4),
        "fp": round(sum(r.fp for r in results) / len(results), 4),
        "fn": round(sum(r.fn for r in results) / len(results), 4),
    }
    aggregate_confusion_matrix = {
        "tp": int(sum(r.tp for r in results)),
        "tn": int(sum(r.tn for r in results)),
        "fp": int(sum(r.fp for r in results)),
        "fn": int(sum(r.fn for r in results)),
    }
    average_metrics = {
        "accuracy": round(sum(r.accuracy for r in results) / len(results), 4),
        "precision": round(sum(r.precision for r in results) / len(results), 4),
        "recall": round(sum(r.recall for r in results) / len(results), 4),
        "f1": round(sum(r.f1 for r in results) / len(results), 4),
    }

    plot_confusion_per_ticker(results_with_preds)
    plot_average_confusion(avg_confusion_matrix)
    plot_metric_summary(results)

    payload = {
        "model": "RandomForestClassifier",
        "evaluation": "Chronological 80/20 split per ticker using politician, month, and day features. P is treated as the positive class.",
        "tickers": TICKERS,
        "per_ticker": [asdict(r) for r in results],
        "average_confusion_matrix": avg_confusion_matrix,
        "aggregate_confusion_matrix": aggregate_confusion_matrix,
        "average_metrics": average_metrics,
        "charts": {
            "display_mode": "matplotlib_show",
            "plots": [
                "per_ticker_confusion_matrices",
                "average_confusion_matrix",
                "metric_summary",
            ],
        },
    }

    with open("politician_eval_results.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        raise
