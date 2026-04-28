# Expense Tracker AI

A Flask-based web app for tracking expenses. It stores entries in CSV format, shows analytics in a browser dashboard, and generates lightweight AI-style spending insights.

## Project Structure

```text
expense_tracker_ai/
|-- data/
|   |-- expenses.csv
|   `-- models/
|-- app/
|   |-- main.py
|   |-- add_expense.py
|   |-- view_expense.py
|   |-- analytics.py
|   |-- ai_model.py
|   `-- utils.py
|-- requirements.txt
`-- README.md
```

## Run

```bash
cd expense_tracker_ai
pip install -r requirements.txt
python app/main.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Features

- Browser-based dashboard with a modern responsive layout
- Add expense records with date, category, amount, and description
- View all expenses or filter by category
- See totals by category and month
- Generate simple spending insights
