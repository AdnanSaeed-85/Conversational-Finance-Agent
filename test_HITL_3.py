from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict
from langgraph.types import interrupt, Command
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langchain_community.tools import tool
import requests
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()
llm = ChatGroq(model='llama-3.3-70b-versatile', temperature=0.7)
@tool
def get_stock_price(symbol: str) -> dict:
    """
    fetched latest stock price for a given symbol (e.g AAPL, TSLA)
    using alpha vantage api key
    """
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey=7XAD98V632VZEUIB"
    )
    r = requests.get(url)
    return r.json()

@tool
def buy_stock_price(symbol: str, quantity: int) -> str:
    """
    simulate purchasing a given quantity of a stock symbol

    HUMAN-IN-THE-LOOP
    before confirming the purchase, this tool will interrupt
    and wait for human decision (yes/ anything else)
    """
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")

    if isinstance(decision, str) and decision.lower() == 'yes':
        return f'Purchased order placed for {quantity} shares of {symbol}'
    else:
        return f'Order for purchasing shares of {symbol} was declined by human'
    
tools = [get_stock_price, buy_stock_price]
llm_binded_tools = llm.bind_tools(tools)

class state_class(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_bot(state: state_class):
    response = llm_binded_tools.invoke(state['messages'])
    return {'messages': [response]}

tool_node = ToolNode(tools)

checkpointer = MemorySaver()

graph = StateGraph(state_class)

graph.add_node('chatbot', chat_bot)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chatbot')
graph.add_conditional_edges('chatbot', tools_condition)
graph.add_edge('tools', 'chatbot')

chatbot = graph.compile(checkpointer=checkpointer)

# human_message = {
#     'messages': [HumanMessage(content='purchase stock for AAPL price is 990')]
# }

# chatbot.invoke(human_message, config=config)

while True:
    user_input = input('you: ')
    if user_input.lower().strip() in {'exit', 'quit'}:
        print('Goodbye')
        break

    mes = {'messages': [HumanMessage(content=user_input)]}
    config = {'configurable': {'thread_id': 9}}
    result = chatbot.invoke(mes, config=config)

    interrupts = result.get("__interrupt__", [])
    if interrupts:
        prompt_to_human = interrupts[0].value
        print(f"HITL: {prompt_to_human}")
        decision = input('your decision: ').strip().lower()
        result = chatbot.invoke(Command(resume=decision), config=config)

    last_msg = result['messages'][-1]
    print(f"bot: {last_msg.content}\n")