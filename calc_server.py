from fastmcp import FastMCP

mcp = FastMCP('calculator_server')

@mcp.tool
async def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

@mcp.tool
async def subtract(a: float, b: float) -> float:
    """Subtract b from a"""
    return a - b

@mcp.tool
async def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b

@mcp.tool
async def divide(a: float, b: float) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    mcp.run()