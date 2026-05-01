from playwright.sync_api import sync_playwright
from src.navigator import navigate_to_role_page
from src.scraper import extract_job_urls_from_page

def test_nav():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://nodesk.co", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        target_role = "Customer Support"
        print(f"Testing navigation for: {target_role}")
        success = navigate_to_role_page(page, target_role)
        print(f"Navigation success: {success}")
        
        if success:
            urls = extract_job_urls_from_page(page, target_role)
            print("Extracted URLs:")
            for u in urls:
                print(u)
                
        browser.close()

if __name__ == "__main__":
    test_nav()
