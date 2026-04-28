from __future__ import annotations

from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for

from ai_model import generate_insights
from analytics import build_analytics
from utils import (
    archive_expenses_older_than_one_year,
    create_expense,
    create_yearly_report,
    delete_expense,
    ensure_data_files,
    get_budget,
    load_expenses,
    load_reports,
    save_budget,
    save_expense,
    summarize_currency,
    to_float,
    update_expense,
)


app = Flask(__name__)


def sync_archived_expenses() -> dict[str, object]:
    return archive_expenses_older_than_one_year()


def get_filtered_expenses(category_filter: str = "") -> list[dict[str, object]]:
    expenses = to_float(load_expenses())
    indexed_expenses = []
    for index, expense in enumerate(expenses):
        indexed_expense = dict(expense)
        indexed_expense["id"] = index
        indexed_expenses.append(indexed_expense)
    normalized_filter = category_filter.strip().lower()
    if normalized_filter:
        indexed_expenses = [expense for expense in indexed_expenses if str(expense["category"]).lower() == normalized_filter]
    return sorted(indexed_expenses, key=lambda row: str(row["date"]), reverse=True)


def build_dashboard_context(
    *,
    category_filter: str = "",
    form_data: dict[str, str] | None = None,
    error: str | None = None,
    selected_month: str = "",
    selected_year: str = "",
    edit_expense_id: str = "",
) -> dict[str, object]:
    archive_summary = sync_archived_expenses()
    analytics = build_analytics()
    by_category = list(dict(analytics["by_category"]).items())
    by_month = list(dict(analytics["by_month"]).items())
    by_year = list(dict(analytics["by_year"]).items())
    reports = load_reports()
    
    # Get latest month or use selected month
    latest_month = by_month[-1][0] if by_month else None
    month_to_display = selected_month if selected_month in analytics["by_month"] else latest_month
    
    # Get latest year or use selected year
    latest_year = by_year[-1][0] if by_year else None
    year_to_display = selected_year if selected_year in analytics["by_year"] else latest_year
    
    # Get month details
    month_expense_total = analytics["by_month"].get(month_to_display, 0) if month_to_display else 0
    month_categories = analytics["month_details"].get(month_to_display, {}) if month_to_display else {}
    month_budget = get_budget(month_to_display) if month_to_display else 0.0
    month_balance = month_budget - month_expense_total

    # Get year details
    year_expense_total = analytics["by_year"].get(year_to_display, 0) if year_to_display else 0
    year_categories = analytics["year_details"].get(year_to_display, {}) if year_to_display else {}
    year_totals = analytics["year_totals"].get(year_to_display, {}) if year_to_display else {}

    all_expenses = get_filtered_expenses()
    editing_expense = next((expense for expense in all_expenses if str(expense["id"]) == edit_expense_id), None) if edit_expense_id else None

    return {
        "expenses": get_filtered_expenses(category_filter),
        "filter_value": category_filter,
        "analytics": analytics,
        "insights": generate_insights().splitlines(),
        "error": error,
        "form_data": form_data
        or {
            "date": str(editing_expense["date"]) if editing_expense else datetime.today().strftime("%Y-%m-%d"),
            "category": str(editing_expense["category"]) if editing_expense else "",
            "amount": f"{float(editing_expense['amount']):.2f}" if editing_expense else "",
            "description": str(editing_expense["description"]) if editing_expense else "",
        },
        "edit_expense_id": edit_expense_id if editing_expense else "",
        "stats": {
            "total": summarize_currency(float(analytics["total"])),
            "count": int(analytics["count"]),
            "top_category": by_category[0][0] if by_category else "No data",
            "latest_month": by_month[-1][0] if by_month else "No data",
            "latest_year": by_year[-1][0] if by_year else "No data",
        },
        "category_breakdown": by_category,
        "monthly_breakdown": by_month,
        "monthly_budget_rows": analytics["monthly_traces"],
        "yearly_breakdown": by_year,
        "reports": reports,
        "available_report_years": sorted({str(row["date"])[:4] for row in get_filtered_expenses()}, reverse=True),
        "archive_summary": archive_summary,
        "monthly_summary": {
            "selected_month": month_to_display,
            "total_expense": summarize_currency(float(month_expense_total)),
            "expense_amount": float(month_expense_total),
            "budget_amount": float(month_budget),
            "total_budget": summarize_currency(float(month_budget)),
            "balance_amount": float(month_balance),
            "total_balance": summarize_currency(float(month_balance)),
            "balance_status": "positive" if month_balance >= 0 else "negative",
            "categories": list(month_categories.items()),
            "available_months": [m[0] for m in by_month],
        },
        "yearly_summary": {
            "selected_year": year_to_display,
            "total_expense": summarize_currency(float(year_expense_total)),
            "expense_amount": float(year_expense_total),
            "categories": list(year_categories.items()),
            "monthly_count": year_totals.get("monthly_count", 0),
            "category_count": year_totals.get("category_count", 0),
            "available_years": [y[0] for y in by_year],
        },
    }


def build_monthly_analysis_context() -> dict[str, object]:
    sync_archived_expenses()
    analytics = build_analytics()
    by_month = list(dict(analytics["by_month"]).items())

    return {
        "monthly_traces": analytics["monthly_traces"],
        "stats": {
            "tracked_months": len(by_month),
            "latest_month": by_month[-1][0] if by_month else "No data",
            "highest_month": max(by_month, key=lambda item: item[1])[0] if by_month else "No data",
        },
    }


@app.route("/", methods=["GET"])
def dashboard() -> str:
    category_filter = request.args.get("category", "")
    selected_month = request.args.get("month", "")
    selected_year = request.args.get("year", "")
    edit_expense_id = request.args.get("edit", "")
    budget_saved = request.args.get("budget_saved", "")
    budget_error = request.args.get("budget_error", "")
    report_saved = request.args.get("report_saved", "")
    report_error = request.args.get("report_error", "")
    updated = request.args.get("updated", "")
    deleted = request.args.get("deleted", "")
    delete_error = request.args.get("delete_error", "")
    
    context = build_dashboard_context(
        category_filter=category_filter,
        selected_month=selected_month,
        selected_year=selected_year,
        edit_expense_id=edit_expense_id,
    )
    if budget_saved == "1":
        context["budget_success"] = "Budget saved successfully."
    if budget_error:
        context["budget_error"] = budget_error
    if report_saved == "1":
        context["report_success"] = "Yearly report generated successfully."
    if report_error:
        context["report_error"] = report_error
    if updated == "1":
        context["expense_updated"] = "Expense updated successfully."
    if deleted == "1":
        context["expense_deleted"] = "Expense removed successfully."
    if delete_error:
        context["delete_error"] = delete_error
    
    return render_template("index.html", **context)


@app.route("/monthly-analysis", methods=["GET"])
def monthly_analysis() -> str:
    return render_template("monthly_analysis.html", **build_monthly_analysis_context())


@app.route("/", methods=["POST"])
def filter_expenses() -> str:
    category_filter = request.form.get("category", "").strip()
    return redirect(url_for("dashboard", category=category_filter))


@app.route("/month", methods=["POST"])
def select_month() -> str:
    selected_month = request.form.get("month", "").strip()
    return redirect(url_for("dashboard", month=selected_month))


@app.route("/year", methods=["POST"])
def select_year() -> str:
    selected_year = request.form.get("year", "").strip()
    return redirect(url_for("dashboard", year=selected_year))


@app.route("/budget", methods=["POST"])
def set_budget() -> str:
    month = request.form.get("month", "").strip()
    budget_str = request.form.get("budget", "").strip()
    
    try:
        budget = float(budget_str)
        if budget < 0:
            raise ValueError("Budget cannot be negative.")
        save_budget(month, budget)
    except ValueError as exc:
        return redirect(url_for("dashboard", month=month, budget_error=str(exc)))
    
    return redirect(url_for("dashboard", month=month, budget_saved="1"))


@app.route("/expenses", methods=["POST"])
def add_expense() -> str:
    form_data = {
        "date": request.form.get("date", ""),
        "category": request.form.get("category", ""),
        "amount": request.form.get("amount", ""),
        "description": request.form.get("description", ""),
    }

    try:
        expense = create_expense(
            form_data["date"],
            form_data["category"],
            form_data["amount"],
            form_data["description"],
        )
    except ValueError as exc:
        return render_template("index.html", **build_dashboard_context(form_data=form_data, error=str(exc)))

    save_expense(expense)
    return redirect(url_for("dashboard", saved="1"))


@app.route("/expenses/<int:expense_id>/edit", methods=["POST"])
def edit_expense(expense_id: int) -> str:
    form_data = {
        "date": request.form.get("date", ""),
        "category": request.form.get("category", ""),
        "amount": request.form.get("amount", ""),
        "description": request.form.get("description", ""),
    }

    try:
        expense = create_expense(
            form_data["date"],
            form_data["category"],
            form_data["amount"],
            form_data["description"],
        )
        update_expense(expense_id, expense)
    except ValueError as exc:
        return render_template(
            "index.html",
            **build_dashboard_context(form_data=form_data, error=str(exc), edit_expense_id=str(expense_id)),
        )

    return redirect(url_for("dashboard", updated="1"))


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def remove_expense(expense_id: int) -> str:
    try:
        delete_expense(expense_id)
    except ValueError as exc:
        return redirect(url_for("dashboard", delete_error=str(exc)))

    return redirect(url_for("dashboard", deleted="1"))


@app.route("/reports", methods=["POST"])
def generate_report() -> str:
    year = request.form.get("year", "").strip()
    try:
        create_yearly_report(year)
    except ValueError as exc:
        return redirect(url_for("dashboard", report_error=str(exc)))

    return redirect(url_for("dashboard", report_saved="1"))


@app.context_processor
def inject_helpers() -> dict[str, object]:
    return {"summarize_currency": summarize_currency}


def main() -> None:
    ensure_data_files()
    app.run(debug=True)


if __name__ == "__main__":
    main()
