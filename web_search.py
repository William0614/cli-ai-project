import asyncio
from search import perform_google_search
from screenshot import take_screenshot_with_playwright

async def search_and_screenshot(query: str):
    """
    Orchestrates the process asynchronously:
    1. Performs a web search.
    2. Takes a screenshot of the first result.
    """
    print(f"--- Starting process for query: '{query}' ---")
    
    # Step 1: Get the URL from the search module.
    # This assumes perform_google_search is a REGULAR (sync) function.
    # If it were async, you would need to 'await' it too.
    url_to_capture = await perform_google_search(query)

    # Step 2: If we got a URL, await the async screenshot function.
    if url_to_capture:
        # Use 'await' to correctly call the async function
        await take_screenshot_with_playwright(url_to_capture, output_path="screenshot.png")
    else:
        print("Process failed because no URL was found from the web search.")
    
    print("--- Process finished ---")