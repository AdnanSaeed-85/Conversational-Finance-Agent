from fastmcp import FastMCP
import aiohttp
from langgraph.types import interrupt

mcp = FastMCP('stock_mcp_server')

@mcp.tool
async def get_stock_price(symbol: str) -> dict:
    """
    fetched latest stock price for a given symbol (e.g AAPL, TSLA)
    using alpha vantage api key
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey=7XAD98V632VZEUIB"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


@mcp.tool
async def buy_stock_for_me(symbol: str, quantity: int) -> str:
    """
    simulate purchasing a given quantity of a stock symbol

    HUMAN-IN-THE-LOOP
    before confirming the purchase, this tool will interrupt
    and wait for human decision (yes/ anything else)
    """

    return f"Order to buy {quantity} shares of {symbol} has been approved successfully."


if __name__ == '__main__':
    mcp.run()