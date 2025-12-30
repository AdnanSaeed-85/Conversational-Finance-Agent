from fastmcp import FastMCP
import asyncio

mcp = FastMCP('test_tool')

@mcp.tool
async def add_tool(num1: int, num2: int) -> str:
    "you have two numbers, just add them and return output"
    result = num1 + num2
    return f"[TOOL EXECUTED] Addition result: {result}"

@mcp.tool
async def sub_tool(num1: int, num2: int) -> str:
    "you have two numbers, just subtract them and return output"
    result = num1 - num2
    return f"[TOOL EXECUTED] Subtraction result: {result}"

@mcp.tool
async def waited_tool() -> str:
    "tool which is used for just pause for 5 seconds"
    await asyncio.sleep(5)
    return "[TOOL EXECUTED] waited for 5 seconds"

if __name__ == '__main__':
    mcp.run()