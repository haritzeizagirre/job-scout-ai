from playwright.sync_api import Page
from .base import BaseAdapter, JobDetails

class WorkingNomadsAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        try:
            job_title = page.locator("h1, h2.title").first.inner_text(timeout=5000)
        except Exception:
            job_title = "Unknown WorkingNomads Title"
            
        try:
            company = page.locator(".company, .company-name").first.inner_text(timeout=5000)
        except Exception:
            company = "Unknown WorkingNomads Company"
            
        try:
            job_description = page.locator(".description, .job-details, main").first.inner_text(timeout=5000)
        except Exception:
            job_description = page.locator("body").inner_text(timeout=5000)
            
        return JobDetails(job_title=job_title.strip(), company=company.strip(), job_description=job_description.strip())
