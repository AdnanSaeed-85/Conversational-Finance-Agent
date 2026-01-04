from fastmcp import FastMCP
import datetime
import asyncpg

mcp = FastMCP('expense_tracker')

DB_URI = "postgresql://postgres:password@localhost:5432/expense_tracker"

# Lazy initialization flag
_initialized = False

async def ensure_table():
    """Initialize table only when first tool is called"""
    global _initialized
    if not _initialized:
        try:
            conn = await asyncpg.connect(DB_URI)
            await conn.execute(
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
            await conn.close()
            _initialized = True
        except Exception as e:
            print(f"Table init error: {e}")

@mcp.tool
async def add_expense(date: str, amount: float, category: str, subcategory: str = '', note: str = '') -> str:
    """Add a new expense entry with amount, category, and description"""
    await ensure_table()
    
    conn = await asyncpg.connect(DB_URI)
    await conn.execute(
        """
        INSERT INTO expenses (date, amount, category, subcategory, note)
        VALUES ($1, $2, $3, $4, $5)
        """,
        date, amount, category, subcategory, note
    )
    await conn.close()
    return f"Expense added: ${amount} for {category}"

@mcp.tool
async def show_expense() -> str:
    """Display all recorded expenses with their details"""
    await ensure_table()
    
    conn = await asyncpg.connect(DB_URI)
    expenses = await conn.fetch("SELECT * FROM expenses ORDER BY date DESC")
    await conn.close()
    
    return str([dict(row) for row in expenses]) if expenses else "No expenses found"

@mcp.tool
async def summarize_expense(group_by: str = 'category') -> str:
    """Generate a summary of expenses by category or time period"""
    await ensure_table()
    
    conn = await asyncpg.connect(DB_URI)
    if group_by == 'category':
        summary = await conn.fetch(
            """
            SELECT category, SUM(amount) as total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
            """
        )
    else:
        summary = await conn.fetch(
            """
            SELECT date, SUM(amount) as total
            FROM expenses
            GROUP BY date
            ORDER BY date DESC
            """
        )
    await conn.close()
    
    return str([dict(row) for row in summary]) if summary else "No expenses to summarize"

@mcp.tool
async def delete_expense(expense_id: int) -> str:
    """Remove an expense entry by its ID or identifier"""
    await ensure_table()
    
    conn = await asyncpg.connect(DB_URI)
    await conn.execute("DELETE FROM expenses WHERE id = $1", expense_id)
    await conn.close()
    
    return f"Expense {expense_id} deleted"


if __name__ == '__main__':
    mcp.run()