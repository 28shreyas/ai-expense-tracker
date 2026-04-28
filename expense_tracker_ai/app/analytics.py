from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from utils import load_expenses, summarize_currency, to_float, load_budgets


def build_analytics() -> dict[str, object]:
    expenses = to_float(load_expenses())
    total = sum(float(expense["amount"]) for expense in expenses)
    budgets = load_budgets()

    by_category: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    by_year: dict[str, float] = defaultdict(float)
    month_categories: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    year_categories: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    month_entries: dict[str, list[dict[str, object]]] = defaultdict(list)

    for expense in expenses:
        amount = float(expense["amount"])
        category = str(expense["category"])
        month = str(expense["date"])[:7]
        year = str(expense["date"])[:4]
        by_category[category] += amount
        by_month[month] += amount
        by_year[year] += amount
        month_categories[month][category] += amount
        year_categories[year][category] += amount
        month_entries[month].append(expense)

    # Calculate balance for each month
    month_balance: dict[str, dict[str, object]] = {}
    for month, expense_total in by_month.items():
        budget = budgets.get(month, 0.0)
        balance = budget - expense_total
        month_balance[month] = {
            "expenses": expense_total,
            "budget": budget,
            "balance": balance,
        }

    # Calculate totals for each year
    year_totals: dict[str, dict[str, object]] = {}
    for year, expense_total in by_year.items():
        year_totals[year] = {
            "expenses": expense_total,
            "monthly_count": sum(1 for m in by_month.keys() if m.startswith(year)),
            "category_count": len(year_categories.get(year, {})),
        }

    monthly_traces: list[dict[str, object]] = []
    previous_month_total = 0.0
    previous_categories: dict[str, float] = {}
    for index, month in enumerate(sorted(by_month.keys())):
        expense_total = float(by_month[month])
        budget = float(budgets.get(month, 0.0))
        balance = budget - expense_total
        expense_within_budget = min(expense_total, budget) if budget > 0 else 0.0
        remaining_budget = max(balance, 0.0) if budget > 0 else 0.0
        exceeded_budget = abs(balance) if budget > 0 and balance < 0 else 0.0
        budget_usage_percent = (expense_total / budget * 100) if budget > 0 else 0.0
        categories = dict(sorted(month_categories[month].items(), key=lambda item: item[1], reverse=True))
        entries = sorted(month_entries[month], key=lambda item: str(item["date"]))
        expense_count = len(entries)
        average_expense = expense_total / expense_count if expense_count else 0.0
        top_category, top_category_amount = next(iter(categories.items()), ("No category", 0.0))
        largest_expense = max(entries, key=lambda item: float(item["amount"]), default=None)
        change_amount = expense_total - previous_month_total if index > 0 else 0.0
        change_percent = (change_amount / previous_month_total * 100) if previous_month_total else 0.0
        previous_top_amount = float(previous_categories.get(top_category, 0.0))
        category_change = float(top_category_amount) - previous_top_amount

        if index == 0:
            trend = "new"
        elif change_amount > 0:
            trend = "up"
        elif change_amount < 0:
            trend = "down"
        else:
            trend = "flat"

        if expense_count == 0:
            analysis = "No expenses were recorded for this month."
        else:
            analysis = (
                f"Spent {summarize_currency(expense_total)} across {expense_count} expenses. "
                f"{top_category} was the highest category at {summarize_currency(float(top_category_amount))}. "
                f"The average expense was {summarize_currency(average_expense)}."
            )
            if budget > 0:
                if balance >= 0:
                    analysis += f" You stayed within budget with {summarize_currency(balance)} remaining."
                else:
                    analysis += f" You exceeded the budget by {summarize_currency(abs(balance))}."
            if trend == "up":
                analysis += f" Spending increased by {summarize_currency(change_amount)} from the previous month."
            elif trend == "down":
                analysis += f" Spending decreased by {summarize_currency(abs(change_amount))} from the previous month."
            elif trend == "flat" and index > 0:
                analysis += " Spending matched the previous month."

        alert_level = "info"
        if expense_count == 0:
            alert_message = "No expenses were added for this month, so there is no alert."
        elif budget > 0 and expense_total > budget:
            alert_level = "danger"
            alert_message = (
                f"You spent {summarize_currency(abs(balance))} more than your monthly budget. "
                "Try reducing optional expenses in this month."
            )
        elif budget > 0 and expense_total >= budget * 0.9:
            alert_level = "warning"
            alert_message = (
                "Your spending is very close to the monthly budget limit. "
                "Review extra expenses before they go over budget."
            )
        elif trend == "up" and change_percent >= 20:
            alert_level = "warning"
            increase_reason = f"most of the increase came from {top_category}, which reached {summarize_currency(float(top_category_amount))}"
            if category_change > 0:
                increase_reason += f" after going up by {summarize_currency(category_change)} from last month"
            if largest_expense:
                largest_description = str(largest_expense.get("description", "")).strip()
                largest_label = largest_description if largest_description else str(largest_expense.get("category", top_category))
                increase_reason += (
                    f". The biggest single expense was {largest_label} for "
                    f"{summarize_currency(float(largest_expense['amount']))}"
                )
            alert_message = (
                f"Your spending increased by {abs(change_percent):.1f}% compared with last month because "
                f"{increase_reason}."
            )
        elif expense_total > 0 and float(top_category_amount) >= expense_total * 0.5:
            alert_level = "info"
            alert_message = (
                f"More than half of this month's spending came from {top_category}. "
                "Start reviewing that category first."
            )
        elif trend == "down" and index > 0:
            alert_level = "success"
            alert_message = "This month's spending is lower than last month. Keep going in the same direction."
        else:
            alert_level = "success"
            alert_message = "This month looks stable. No major spending issue was found."

        monthly_traces.append(
            {
                "month": month,
                "label": datetime.strptime(f"{month}-01", "%Y-%m-%d").strftime("%B %Y"),
                "total": expense_total,
                "total_display": summarize_currency(expense_total),
                "budget": budget,
                "budget_display": summarize_currency(budget),
                "balance": balance,
                "balance_display": summarize_currency(balance),
                "status": "positive" if balance >= 0 else "negative",
                "expense_within_budget": expense_within_budget,
                "expense_within_budget_display": summarize_currency(expense_within_budget),
                "remaining_budget": remaining_budget,
                "remaining_budget_display": summarize_currency(remaining_budget),
                "exceeded_budget": exceeded_budget,
                "exceeded_budget_display": summarize_currency(exceeded_budget),
                "budget_usage_percent": budget_usage_percent,
                "has_budget": budget > 0,
                "budget_health": "within" if budget > 0 and expense_total <= budget else "over" if budget > 0 else "none",
                "expense_count": expense_count,
                "average_expense": average_expense,
                "average_expense_display": summarize_currency(average_expense),
                "top_category": top_category,
                "top_category_amount": float(top_category_amount),
                "top_category_amount_display": summarize_currency(float(top_category_amount)),
                "change_amount": change_amount,
                "change_amount_display": summarize_currency(abs(change_amount)),
                "change_percent": abs(change_percent),
                "trend": trend,
                "analysis": analysis,
                "alert_level": alert_level,
                "alert_message": alert_message,
                "categories": list(categories.items()),
                "largest_expense": largest_expense,
            }
        )
        previous_month_total = expense_total
        previous_categories = categories

    return {
        "count": len(expenses),
        "total": total,
        "by_category": dict(sorted(by_category.items(), key=lambda item: item[1], reverse=True)),
        "by_month": dict(sorted(by_month.items())),
        "by_year": dict(sorted(by_year.items())),
        "month_details": {month: dict(sorted(cats.items(), key=lambda item: item[1], reverse=True)) 
                         for month, cats in month_categories.items()},
        "year_details": {year: dict(sorted(cats.items(), key=lambda item: item[1], reverse=True)) 
                        for year, cats in year_categories.items()},
        "month_balance": month_balance,
        "monthly_traces": list(reversed(monthly_traces)),
        "year_totals": year_totals,
        "budgets": budgets,
    }


def print_analytics() -> None:
    analytics = build_analytics()
    if analytics["count"] == 0:
        print("No expenses available for analytics.")
        return

    print("\nAnalytics")
    print("-" * 30)
    print(f"Total entries : {analytics['count']}")
    print(f"Total spend   : {summarize_currency(float(analytics['total']))}")

    print("\nBy category")
    for category, amount in analytics["by_category"].items():
        print(f"- {category}: {summarize_currency(float(amount))}")

    print("\nBy month")
    for month, amount in analytics["by_month"].items():
        print(f"- {month}: {summarize_currency(float(amount))}")

    print("\nBy year")
    for year, amount in analytics["by_year"].items():
        print(f"- {year}: {summarize_currency(float(amount))}")
