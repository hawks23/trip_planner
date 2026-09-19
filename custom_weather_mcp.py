from mcp.server.fastmcp import FastMCP
import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

mcp = FastMCP("Weather MCP Server")

## SINCE THIS IS A CUSTOM MCP, THE API ENDPOINT HAS TO BE UPDATED IF IT GETS DERPECATED. THE CURRENT ENDPOINT IS: https://api.openweathermap.org/data/2.5/weather

@mcp.tool()
def get_current_weather(city: str):

    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
    )
    data = response.json()

    if response.status_code != 200:
        return f"Error: {data.get('message', 'Unable to fetch weather data')}"

    return {
        "city": data["name"],
        "temperature_c": data["main"]["temp"],
        "feels_like_c": data["main"]["feels_like"],
        "description": data["weather"][0]["description"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"]
    }

@mcp.tool()
def get_forecast(city: str):
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
    )
    data = response.json()

    if response.status_code != 200:
        return f"Error: {data.get('message', 'Unable to fetch forecast data')}"

    forecast_list = []
    for item in data["list"][-5:]:  # Get the last 5 forecast entries
        forecast_list.append({
            "datetime": item["dt_txt"],
            "temperature_c": item["main"]["temp"],
            "description": item["weather"][0]["description"],
        })

    return {
        "city": city,
        "forecast": forecast_list
    }

if __name__ == "__main__":
    mcp.run()