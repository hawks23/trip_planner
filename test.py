from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights


# res = tavily_search("Best travel destinations in Europe for summer 2024")
# print(res)

res = search_flights("Plan a 7 days Japan trip from Bangladesh")
print(res)