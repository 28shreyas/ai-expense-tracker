from __future__ import annotations

from analytics import build_analytics
from utils import summarize_currency


def generate_insights() -> str:
    analytics = build_analytics()
    count = int(analytics["count"])
    total = float(analytics["total"])

    if count == 0:
        return "No expense data yet. Add a few entries and I can generate spending insights."

    by_category = analytics["by_category"]
    by_month = analytics["by_month"]
    top_category = next(iter(by_category.items()))
    latest_month = list(by_month.items())[-1]
    average = total / count

    insights = [
        f"You have logged {count} expenses totaling {summarize_currency(total)}.",
        f"Your highest spending category is {top_category[0]} at {summarize_currency(float(top_category[1]))}.",
        f"The latest tracked month is {latest_month[0]}, with spending of {summarize_currency(float(latest_month[1]))}.",
        f"Your average expense size is {summarize_currency(average)}.",
    ]

    if float(top_category[1]) > total * 0.4:
        insights.append(
            f"{top_category[0]} makes up more than 40% of your spending, so it may be the best place to optimize first."
        )
    else:
        insights.append("Your spending appears reasonably distributed across categories.")

    return "\n".join(insights)


def print_ai_insights() -> None:
    print("\nAI Insights")
    print("-" * 30)
    print(generate_insights())
