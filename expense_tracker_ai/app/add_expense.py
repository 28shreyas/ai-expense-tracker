from __future__ import annotations

from utils import create_expense, save_expense


def prompt_new_expense() -> None:
    print("\nAdd Expense")
    print("-" * 30)
    try:
        expense = create_expense(
            input("Date (YYYY-MM-DD): "),
            input("Category: "),
            input("Amount: "),
            input("Description: "),
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    save_expense(expense)
    print("Expense saved successfully.")
