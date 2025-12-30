from fastmcp import FastMCP
import datetime


mcp = FastMCP('expense_tracker')

DB_URI = "postgresql://postgres:password@localhost:5432/expense_tracker"

# Lazy initialization flag
_initialized = False

def ensure_table():
    """Initialize table only when first tool is called"""
    global _initialized
    if not _initialized:
        try:
            import psycopg  # Import only when needed
            with psycopg.connect(DB_URI) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS expenses (
                            id SERIAL PRIMARY KEY,
                            date TEXT NOT NULL,
                            amount REAL NOT NULL,
                            category TEXT NOT NULL,
                            subcategory TEXT DEFAULT '',
                            note TEXT DEFAULT ''
                        )
                        """
                    )
                    conn.commit()
            _initialized = True
        except Exception as e:
            print(f"Table init error: {e}")

@mcp.tool
def add_expense(amount: float, category: str, subcategory: str = '', note: str = '') -> str:
    """Add a new expense entry with amount, category, and description"""
    import psycopg  # Import inside tool
    ensure_table()
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expenses (date, amount, category, subcategory, note)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (date, amount, category, subcategory, note)
            )
            conn.commit()
    return f"Expense added: ${amount} for {category}"

@mcp.tool
def show_expense() -> str:
    """Display all recorded expenses with their details"""
    import psycopg
    ensure_table()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM expenses ORDER BY date DESC")
            expenses = cur.fetchall()
    return str(expenses) if expenses else "No expenses found"

@mcp.tool
def summarize_expense(group_by: str = 'category') -> str:
    """Generate a summary of expenses by category or time period"""
    import psycopg
    ensure_table()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            if group_by == 'category':
                cur.execute(
                    """
                    SELECT category, SUM(amount) as total
                    FROM expenses
                    GROUP BY category
                    ORDER BY total DESC
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT date, SUM(amount) as total
                    FROM expenses
                    GROUP BY date
                    ORDER BY date DESC
                    """
                )
            summary = cur.fetchall()
    return str(summary) if summary else "No expenses to summarize"

@mcp.tool
def delete_expense(expense_id: int) -> str:
    """Remove an expense entry by its ID or identifier"""
    import psycopg
    ensure_table()
    with psycopg.connect(DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
            conn.commit()
    return f"Expense {expense_id} deleted"


if __name__ == '__main__':
    mcp.run()