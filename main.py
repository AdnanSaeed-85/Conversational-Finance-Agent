# backend.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import uuid
import os
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
load_dotenv()
# Fix for Windows event loop - MUST be before asyncio.run()
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

client1 = MultiServerMCPClient(
    {
        "arthm": {
            "transport": 'stdio',
            "command": 'A:\\AI_Projects\\AI Conversational Agent\\.venv\\Scripts\\python.exe',  # Use venv Python
            "args": ['A:\\AI_Projects\\AI Conversational Agent\\mcp_server.py']
        }
    }
)

client2 = MultiServerMCPClient(
    {
        "rag": {
            "transport": 'stdio',
            "command": 'A:\\AI_Projects\\AI Conversational Agent\\.venv\\Scripts\\python.exe',  # Use venv Python
            "args": ['A:\\AI_Projects\\AI Conversational Agent\\rag_server.py']
        }
    }
)

client3 = MultiServerMCPClient(
    {
        "calc": {
            "transport": 'stdio',
            "command": 'A:\\AI_Projects\\AI Conversational Agent\\.venv\\Scripts\\python.exe',  # Use venv Python
            "args": ['A:\\AI_Projects\\AI Conversational Agent\\calc_server.py']
        }
    }
)

# -------------------
# 0. Create threads 
# -------------------
def new_threads():
    return str(uuid.uuid4())

# -------------------
# 1. Get all existing threads
# -------------------
async def get_all_threads(checkpointer):
    """Retrieve all unique thread IDs from the database."""
    threads = set()
    try:
        async for checkpoint in checkpointer.alist(None):
            thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
            if thread_id:
                threads.add(thread_id)
    except Exception as e:
        print(f"Error retrieving threads: {e}")
    return list(threads)

# -------------------
# 2. LLM
# -------------------
# llm = ChatGroq(model="llama-3.3-70b-versatile",temperature=0.7)
llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite', temperature=0.7)

# -------------------
# 3. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------
# 4. Nodes
# -------------------
    
async def main():

    tool1 = await client1.get_tools()
    tool2 = await client2.get_tools()
    tool3 = await client3.get_tools()
    tools = tool1 + tool2 + tool3

    # print(tools)

    llm_binding_tool = llm.bind_tools(tools)

    async def chat_node(state: ChatState):
        """LLM node that may answer or request a tool call."""
        messages = state["messages"]
        response = await llm_binding_tool.ainvoke(messages)

        # Check if the AI response includes tool/function calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Get list of all tool names being called
            tool_names = []
            for tool_call in response.tool_calls:
                tool_names.append(tool_call['name'])
            
            # Create a friendly message
            tools_text = ', '.join(tool_names)
            print(f"\n🔧 The AI is using these tools: {tools_text}\n")
            print(f"   Total tools being used: {len(tool_names)}\n")

        return {"messages": [response]}

    tool_node = ToolNode(tools) if tools else None

    # -------------------
    # 5. Database URI
    # -------------------
    DB_URI = "postgresql://postgres:password@localhost:5432/thread_database"

    # -------------------
    # 6. Use within context manager
    # -------------------
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # Setup database schema (only needed first time)
        await checkpointer.setup()
        
        # Build graph
        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_edge(START, "chat_node")
        
        if tool_node:
            async def tools_with_logging(state: ChatState):
                print(f"⚙️ Executing tools...")
                result = await tool_node.ainvoke(state)
                print(f"✅ Tool execution completed\n")
                return result
            
            graph.add_node("tools", tools_with_logging)
            graph.add_conditional_edges("chat_node", tools_condition)
            graph.add_edge("tools", "chat_node")
        else:
            graph.add_edge("chat_node", END)

        chatbot = graph.compile(checkpointer=checkpointer)
        
        # Run the chatbot
        print("Chat started! Type 'exit', 'quit', or 'bye' to end the conversation.\n")

        thread_input = input("Type 'YES' to create a new chat (or press Enter to load existing): ").strip()
        
        if thread_input.lower() == 'yes':
            # Create new thread
            threads = new_threads()
            config = {'configurable': {'thread_id': threads}}
            print(f"\n✅ New chat created with Thread ID: {threads}\n")
        
        else:
            # Load existing threads
            existing_threads = await get_all_threads(checkpointer)
            print(existing_threads)
            
            if not existing_threads:
                print("\n⚠️  No existing conversations found. Creating a new one...\n")
                threads = new_threads()
                config = {'configurable': {'thread_id': threads}}
                print(f"✅ New chat created with Thread ID: {threads}\n")
            else:
                print(f"\n📋 Found {len(existing_threads)} existing conversation(s):\n")
                for idx, thread_id in enumerate(existing_threads, 1):
                    print(f"{idx}. {thread_id}")
                
                # Let user choose a thread
                while True:
                    try:
                        choice = input(f"\nEnter number (1-{len(existing_threads)}) to load a conversation, or 'new' for new chat: ").strip()
                        
                        if choice.lower() == 'new':
                            threads = new_threads()
                            config = {'configurable': {'thread_id': threads}}
                            print(f"\n✅ New chat created with Thread ID: {threads}\n")
                            break
                        
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(existing_threads):
                            threads = existing_threads[choice_num - 1]
                            config = {'configurable': {'thread_id': threads}}
                            print(f"\n✅ Loaded conversation: {threads}\n")
                            break
                        else:
                            print(f"❌ Please enter a number between 1 and {len(existing_threads)}")
                    except ValueError:
                        print("❌ Invalid input. Please enter a number or 'new'")
        
        # Chat loop
        while True:
            user_input = input("🧑: ")
            if user_input.lower().strip() in ['exit', 'quit', 'bye']:
                print("Goodbye! 👋")
                break
            
            if not user_input.strip():
                continue
            
            # Invoke with just the new message - the checkpointer handles history
            response = await chatbot.ainvoke(
                {'messages': [HumanMessage(content=user_input)]},
                config=config
            )
            
            # Get the last message (the assistant's response)
            assistant_message = response['messages'][-1].content
            print(f"🤖: {assistant_message}\n")


if __name__ == "__main__":
    asyncio.run(main())