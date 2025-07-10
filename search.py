# file: web_search.py

import os
import requests
import asyncio

# It's safer to use environment variables for keys.
# In your terminal: export GOOGLE_API_KEY="YourKey" and export GOOGLE_CX="YourCx"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAanre6Mreyl-TXOQxy5EhPLQDWUwIjzhs")
GOOGLE_CX = os.getenv("GOOGLE_CX", "304b4a42cbaa74f57")

async def perform_google_search(query: str) -> str:
    """
    Performs a search using Google Custom Search API and returns the first link.

    Args:
        query: The search term.

    Returns:
        The URL of the first search result, or None if an error occurs.
    """
    print(f"Searching for: '{query}'...")
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes

        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            first_result = data['items'][0]
            link = first_result.get('link')
            if link:
                print(f"Found URL: {link}")
                return link
            else:
                print("Error: First result found, but it has no 'link' field.")
                return None
        else:
            print("Error: No search results found.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None
    except KeyError:
        print("Error: Invalid data format received from API.")
        return None