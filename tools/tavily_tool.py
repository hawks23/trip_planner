from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

def tavily_search(query: str):
    """
    Search for travel destinations using Tavily API.

    Args:
        query (str): The search query.

    Returns:
        dict: The search results.
    """

    response = client.search(
        query = query,
        max_results = 5,
    )

    """We have to remove the unwanted metadata from the response and format it nicely for the user. The response is a dictionary with a "results" key that contains a list of results. Each result is a dictionary with "title", "url", and "content" keys."""

    results = []

    for i, r in enumerate(response["results"], 1):
        title   = r.get("title", "Unknown")
        url     = r.get("url", "")
        snippet = r.get("content", "").strip()
        # Keep only the first 300 characters to avoid wall-of-text
        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

        results.append(f"{i}. **{title}**\n   {url}\n   {snippet}")

    return "\n\n".join(results)