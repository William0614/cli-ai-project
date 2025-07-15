from screenshot import take_screenshot_with_playwright
import asyncio

async def main():
    await take_screenshot_with_playwright("https://www.google.com/search?q=yahoo+finance")
