from playwright.sync_api import sync_playwright
from src.adapters import AdapterFactory

def scrape_live_url(url: str) -> dict:
    """
    Visits a live URL, selects the correct adapter, and extracts job details.
    """
    with sync_playwright() as p:
        # Run in headed mode to allow manual intervention if needed (captchas, login walls)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"Navigating to {url} ...")
        # Go to URL and wait a bit for dynamic content to load
        # Use a generous timeout in case of manual captcha solving
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000) # Give it an extra 3 seconds for dynamic renders
        except Exception as e:
            print(f"Warning: Navigation timeout or error: {e}")
            # Try to continue anyway, it might have loaded enough
        
        # Get adapter
        adapter = AdapterFactory.get_adapter(url)
        
        # Extract details
        job_details = adapter.extract(page)
        
        browser.close()
        
        return {
            "job_title": job_details.job_title,
            "company": job_details.company,
            "job_description": job_details.job_description
        }
