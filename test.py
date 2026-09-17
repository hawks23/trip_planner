# from tools.tavily_tool import tavily_search
# from tools.flight_tool import search_flights
# from backend import run_travel_agent

# res = tavily_search("Best travel destinations in Europe for summer 2024")
# print(res)

# res = search_flights("Plan a 7 days Japan trip from Bangladesh")
# print(res)
# user_input = input("Enter your travel query: ")

# response = run_travel_agent(
#     user_input=user_input,
#     thread_id="test_user"
#     )

# print(f"\nFinal response\n{response['answer']}")

import asyncio
from mcp_client_test import get_all_tools, tavily_mcp_search

if __name__ == "__main__":
    asyncio.run(tavily_mcp_search("Best places to visit copenhagen in summer"))