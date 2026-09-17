import os
import asyncio
import certifi
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
    }
)

async def get_all_tools():
    tools = await client.get_tools()
    print("Available tools:")
    for tool in tools:
        print(f" - {tool.name}: \n{tool.description}\n\n")

## CREATE THE TAVILY SEARCH TOOL

tavily_search_tool = None

async def get_tavily_search_tool():
    global tavily_search_tool
    if tavily_search_tool is not None:
        return tavily_search_tool
    
    tools = await client.get_tools()
    # print("Available tools:")
    # for tool in tools:
    #     print(f" - {tool.name}")
    # If we find the tool, we can store it in the global variable, else return none. next is similar to break, when we find the first match, we return it.
    tavily_search_tool = next((tool for tool in tools if tool.name == "tavily_search"), None)

# tool call along with the query, and we can get the result from the web search tool. 
async def tavily_mcp_search(query: str):
    await get_tavily_search_tool()
    result = await tavily_search_tool.ainvoke(
        {
            "query": query
        }
    )
    # print(f"Result from tavily_search tool:\n{result}")
    return result