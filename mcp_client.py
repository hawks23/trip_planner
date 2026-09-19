import os
import certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="openai/gpt-oss-20b",
    temperature=0.0
)
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
        "Aviationstack MCP": 
        {
            "transport": "stdio",
            "command": "uvx",
            "args": 
            [
              "aviationstack-mcp"
            ],
            "env": 
            {
              "AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY
            }
        },
        "Weather MCP": {
            "transport": "stdio",
            "command": r"C:\Users\sweet\miniconda3\envs\travel\python.exe",
            "args": [
                r"C:\Users\sweet\Documents\From old PC\Coding_stuff\trip_planner\trip_planner\custom_weather_mcp.py"
            ],
            "env": {
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
            }
        }
    }
)

async def get_all_tools():
    tools = await client.get_tools()
    print("Available tools:")
    for tool in tools:
        print(f" - {tool.name}")

## Tavily and aviation tools

search_tool = None
aviation_tools = {}
weather_tools = None
forecast_tool = None

async def initialize_mcp():
    global search_tool
    global aviation_tools

    if search_tool is not None and aviation_tools:
        return

    tools = await client.get_tools()
    print("Available tools:")

    for tool in tools:
        print(tool.name)

    # 1. Store Tavily search tool
    search_tool = next((tool for tool in tools if tool.name == "tavily_search"), None)

    # 2. Define non-allowed / restricted AviationStack endpoints on the free plan
    restricted_keywords = [
        "airport", 
        "airline", 
        "airplane", 
        "city", 
        "cities", 
        "country", 
        "countries", 
        "schedule", 
        "timetable"
    ]

    # 3. Filter aviation tools to only include allowed flight execution tools
    aviation_tools = {
        tool.name: tool 
        for tool in tools 
        if tool.name != "tavily_search" and not any(kw in tool.name.lower() for kw in restricted_keywords)
    }

async def initialize_weather_tools():
    global weather_tools
    global forecast_tool

    if weather_tools is not None and forecast_tool is not None:
        return

    tools = await client.get_tools()
    print("Available tools:")

    for tool in tools:
        print(tool.name)

    # 1. Store Weather MCP tools
    weather_tools = next((tool for tool in tools if tool.name == "get_current_weather"), None)
    forecast_tool = next((tool for tool in tools if tool.name == "get_forecast"), None)



async def weather_mcp_search(city: str):
    await initialize_weather_tools()
    result = await weather_tools.ainvoke(
        {
            "city": city
        }
    )
    return result


async def forecast_mcp_search(city: str):
    await initialize_weather_tools()
    result = await forecast_tool.ainvoke(
        {
            "city": city
        }
    )
    return result


def extract_destination(query: str) -> str:

    prompt = f"""
    Extract only the destination city from the following travel query. If no destination is found, return 'Unknown'.
    Travel Query: "{query}"
    Return only the destination city name, without any additional text or punctuation.
    """

    response = llm.invoke(prompt)
    return response.content.strip()


async def tavily_mcp_search(query: str):
    await initialize_mcp()
    result = await search_tool.ainvoke(
        {
            "query": query
        }
    )
    return result


async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict = None
):
    # 1. Ensure tools are loaded into memory first
    await initialize_mcp()

    # 2. Look up the tool from the cached dictionary
    tool = aviation_tools.get(tool_name)
    
    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found in AviationStack MCP.")

    # 3. Directly invoke the tool
    result = await tool.ainvoke(tool_args or {})
    return result