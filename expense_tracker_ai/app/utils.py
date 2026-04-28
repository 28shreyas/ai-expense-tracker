from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
REPORTS_DIR = DATA_DIR / "reports"
EXPENSES_FILE = DATA_DIR / "expenses.csv"
BUDGETS_FILE = DATA_DIR / "budgets.json"
REPORTS_INDEX_FILE = REPORTS_DIR / "reports.json"
DATE_FORMAT = "%Y-%m-%d"
EXPENSE_FIELDS = ["date", "category", "amount", "description"]


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPENSES_FILE.exists():
        EXPENSES_FILE.write_text("date,category,amount,description\n", encoding="utf-8")
    if not BUDGETS_FILE.exists():
        BUDGETS_FILE.write_text("{}\n", encoding="utf-8")
    if not REPORTS_INDEX_FILE.exists():
        REPORTS_INDEX_FILE.write_text("[]\n", encoding="utf-8")


def load_budgets() -> dict[str, float]:
    ensure_data_files()
    try:
        with BUDGETS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_budgets(budgets: dict[str, float]) -> None:
    ensure_data_files()
    with BUDGETS_FILE.open("w", encoding="utf-8") as file:
        json.dump(budgets, file, indent=2)


def save_budget(month: str, amount: float) -> None:
    ensure_data_files()
    budgets = load_budgets()
    budgets[month] = round(amount, 2)
    save_budgets(budgets)


def get_budget(month: str) -> float:
    budgets = load_budgets()
    return budgets.get(month, 0.0)


def parse_date(value: str) -> str:
    parsed = datetime.strptime(value.strip(), DATE_FORMAT)
    return parsed.strftime(DATE_FORMAT)


def parse_amount(value: str) -> float:
    amount = float(value)
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")
    return round(amount, 2)


def load_expenses() -> list[dict[str, str]]:
    ensure_data_files()
    with EXPENSES_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def rewrite_expenses(expenses: list[dict[str, str]]) -> None:
    ensure_data_files()
    with EXPENSES_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXPENSE_FIELDS)
        writer.writeheader()
        writer.writerows(expenses)


def save_expense(expense: dict[str, str]) -> None:
    ensure_data_files()
    with EXPENSES_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXPENSE_FIELDS)
        writer.writerow(expense)


def update_expense(expense_index: int, updated_expense: dict[str, str]) -> None:
    expenses = load_expenses()
    if expense_index < 0 or expense_index >= len(expenses):
        raise ValueError("Expense not found.")
    expenses[expense_index] = updated_expense
    rewrite_expenses(expenses)


def delete_expense(expense_index: int) -> None:
    expenses = load_expenses()
    if expense_index < 0 or expense_index >= len(expenses):
        raise ValueError("Expense not found.")
    del expenses[expense_index]
    rewrite_expenses(expenses)


def load_reports() -> list[dict[str, object]]:
    ensure_data_files()
    try:
        with REPORTS_INDEX_FILE.open("r", encoding="utf-8") as file:
            reports = json.load(file)
            return reports if isinstance(reports, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_reports(reports: list[dict[str, object]]) -> None:
    ensure_data_files()
    with REPORTS_INDEX_FILE.open("w", encoding="utf-8") as file:
        json.dump(reports, file, indent=2)


def normalize_category(value: str) -> str:
    category = value.strip()
    if not category:
        raise ValueError("Category cannot be empty.")
    return category.title()


def create_expense(date: str, category: str, amount: str, description: str) -> dict[str, str]:
    normalized_date = parse_date(date)
    normalized_category = normalize_category(category)
    normalized_amount = parse_amount(amount)
    return {
        "date": normalized_date,
        "category": normalized_category,
        "amount": f"{normalized_amount:.2f}",
        "description": description.strip(),
    }


def summarize_currency(value: float) -> str:
    return f"₹{value:,.2f}"


def to_float(expenses: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for expense in expenses:
        normalized.append(
            {
                "date": expense["date"],
                "category": expense["category"],
                "amount": float(expense["amount"]),
                "description": expense["description"],
            }
        )
    return normalized


def build_report_payload(
    *,
    year: str,
    expenses: list[dict[str, str]],
    report_type: str,
    generated_at: str,
) -> dict[str, object]:
    normalized = to_float(expenses)
    total = sum(float(expense["amount"]) for expense in normalized)
    by_category: dict[str, float] = {}
    by_month: dict[str, float] = {}

    for expense in normalized:
        category = str(expense["category"])
        month = str(expense["date"])[:7]
        amount = float(expense["amount"])
        by_category[category] = by_category.get(category, 0.0) + amount
        by_month[month] = by_month.get(month, 0.0) + amount

    return {
        "year": year,
        "report_type": report_type,
        "generated_at": generated_at,
        "total_entries": len(expenses),
        "total_expense": round(total, 2),
        "by_category": dict(sorted(by_category.items(), key=lambda item: item[1], reverse=True)),
        "by_month": dict(sorted(by_month.items())),
        "expenses": expenses,
    }


def create_yearly_report(year: str, *, report_type: str = "manual") -> dict[str, object]:
    ensure_data_files()
    expenses = load_expenses()
    year_expenses = [expense for expense in expenses if expense["date"].startswith(year)]
    if not year_expenses:
        raise ValueError(f"No expenses found for {year}.")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = build_report_payload(
        year=year,
        expenses=year_expenses,
        report_type=report_type,
        generated_at=generated_at,
    )
    filename = f"report_{year}_{report_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    with (REPORTS_DIR / filename).open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    reports = load_reports()
    report_record = {
        "year": year,
        "report_type": report_type,
        "generated_at": generated_at,
        "total_entries": payload["total_entries"],
        "total_expense": payload["total_expense"],
        "file_name": filename,
    }
    reports.insert(0, report_record)
    save_reports(reports)
    return report_record


def archive_expenses_older_than_one_year() -> dict[str, object]:
    ensure_data_files()
    expenses = load_expenses()
    if not expenses:
        return {"archived_count": 0, "archived_years": []}

    cutoff_date = datetime.today() - timedelta(days=365)
    archived_by_year: dict[str, list[dict[str, str]]] = {}
    active_expenses: list[dict[str, str]] = []

    for expense in expenses:
        expense_date = datetime.strptime(expense["date"], DATE_FORMAT)
        if expense_date < cutoff_date:
            archived_by_year.setdefault(expense["date"][:4], []).append(expense)
        else:
            active_expenses.append(expense)

    if not archived_by_year:
        return {"archived_count": 0, "archived_years": []}

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reports = load_reports()
    archived_years: list[str] = []

    for year, year_expenses in sorted(archived_by_year.items()):
        payload = build_report_payload(
            year=year,
            expenses=year_expenses,
            report_type="auto-archive",
            generated_at=generated_at,
        )
        filename = f"report_{year}_auto_archive_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.json"
        with (REPORTS_DIR / filename).open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
        reports.insert(
            0,
            {
                "year": year,
                "report_type": "auto-archive",
                "generated_at": generated_at,
                "total_entries": payload["total_entries"],
                "total_expense": payload["total_expense"],
                "file_name": filename,
            },
        )
        archived_years.append(year)

    rewrite_expenses(active_expenses)

    budgets = load_budgets()
    active_months = {expense["date"][:7] for expense in active_expenses}
    save_budgets({month: amount for month, amount in budgets.items() if month in active_months})
    save_reports(reports)

    return {
        "archived_count": sum(len(items) for items in archived_by_year.values()),
        "archived_years": archived_years,
    }
