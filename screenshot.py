from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

async def take_screenshot_with_playwright(url: str, output_path: str = "screenshot.png"):
    """
    Navigates to a URL using Playwright asynchronously and takes a screenshot.

    Args:
        url: The URL to visit.
        output_path: The file path to save the screenshot.
    """
    if not url:
        print("Error: URL cannot be empty.")
        return

    print(f"Taking screenshot of {url}...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate using the 'load' event, which is more reliable.
            await page.goto(url, wait_until='load', timeout=30000)
            
            await page.screenshot(path=output_path, full_page=True)
            print(f"Screenshot successfully saved as '{output_path}'")
            await browser.close()
            
    except PlaywrightTimeoutError:
        print(f"Timeout Error: The page at {url} took too long to load (more than 30 seconds).")
    except PlaywrightError as e:
        print(f"A Playwright error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while taking screenshot: {e}")