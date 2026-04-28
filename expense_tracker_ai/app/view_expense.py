from __future__ import annotations

from utils import load_expenses, summarize_currency, to_float


def display_expenses(category: str | None = None) -> None:
    expenses = to_float(load_expenses())
    if category:
        expenses = [expense for expense in expenses if str(expense["category"]).lower() == category.lower()]

    if not expenses:
        print("No expenses found.")
        return

    print("\nExpenses")
    print("-" * 72)
    print(f"{'Date':<12}{'Category':<18}{'Amount':<12}Description")
    print("-" * 72)
    for expense in sorted(expenses, key=lambda row: str(row["date"]), reverse=True):
        print(
            f"{expense['date']:<12}"
            f"{str(expense['category']):<18}"
            f"{summarize_currency(float(expense['amount'])):<12}"
            f"{expense['description']}"
        )


def prompt_view_expenses() -> None:
    category = input("Filter by category (leave blank for all): ").strip()
    display_expenses(category or None)
