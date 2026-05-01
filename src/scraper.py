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

import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from urllib.parse import urlparse, urljoin

class JobLinksOutput(BaseModel):
    urls: list[str] = Field(description="List of absolute URLs to job postings.")

def extract_job_urls_from_page(page, target_role: str) -> list[str]:
    links = page.locator("a").all()
    link_data = []
    parsed_base = urlparse(page.url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    for el in links:
        try:
            if not el.is_visible():
                continue
            href = el.get_attribute("href")
            if not href:
                continue
            href = urljoin(page.url, href)
                
            text = el.inner_text().strip()
            if len(text) > 5 and len(text) < 150:
                link_data.append(f"Text: '{text}' | URL: {href}")
        except Exception:
            pass
            
    link_data = list(set(link_data))
    if not link_data:
        return []
        
    links_text = "\n".join(link_data[:300]) 
    
    model_name = "gpt-4o-mini"
    if "openrouter" in os.environ.get("OPENAI_BASE_URL", "").lower():
        model_name = "openai/gpt-4o-mini"
            
    llm = ChatOpenAI(model=model_name, temperature=0)
    structured_llm = llm.with_structured_output(JobLinksOutput)
    
    prompt = PromptTemplate.from_template("""
    You are an expert at finding job links. 
    Here is a list of links found on a job board:
    {links}
    
    Target Role: {target_role}
    
    Please return a list of the URLs that represent specific job postings that are relevant to the target role. 
    Do not include pagination links, category links, or irrelevant jobs. Return a maximum of 5 URLs to keep it quick.
    """)
    
    print("Asking LLM to filter job links from page...")
    try:
        result = structured_llm.invoke(prompt.format(links=links_text, target_role=target_role))
        return result.urls
    except Exception as e:
        print(f"Error extracting links: {e}")
        return []
