from playwright.sync_api import Page
from .base import BaseAdapter, JobDetails

class NoDeskAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        try:
            job_title = page.locator("h1").first.inner_text(timeout=5000)
        except Exception:
            job_title = "Unknown NoDesk Title"
            
        try:
            company = page.locator("h2, .company-title, a.company").first.inner_text(timeout=5000)
        except Exception:
            company = "Unknown NoDesk Company"
            
        try:
            job_description = page.locator(".job-description, .content, main").first.inner_text(timeout=5000)
        except Exception:
            job_description = page.locator("body").inner_text(timeout=5000)
            
        return JobDetails(job_title=job_title.strip(), company=company.strip(), job_description=job_description.strip())
