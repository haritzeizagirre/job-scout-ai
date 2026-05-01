from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from playwright.sync_api import Page
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import os

class JobDetails(BaseModel):
    job_title: str = Field(description="The title of the job role")
    company: str = Field(description="The name of the company offering the job")
    job_description: str = Field(description="The full job description and requirements")

class BaseAdapter(ABC):
    @abstractmethod
    def extract(self, page: Page) -> JobDetails:
        pass

class JustRemoteAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        try:
            job_title = page.locator("h1").first.inner_text(timeout=5000)
        except Exception:
            job_title = "Unknown JustRemote Title"
            
        try:
            # JustRemote often puts the company name in an h2 or a div near the top
            company = page.locator("h2, .company-name").first.inner_text(timeout=5000)
        except Exception:
            company = "Unknown JustRemote Company"
            
        try:
            job_description = page.locator(".job-description, article, main").first.inner_text(timeout=5000)
        except Exception:
            job_description = page.locator("body").inner_text(timeout=5000)
            
        return JobDetails(job_title=job_title.strip(), company=company.strip(), job_description=job_description.strip())

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

class GenericAIAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        try:
            raw_text = page.locator("body").inner_text(timeout=10000)
        except Exception:
            raw_text = "Failed to extract body text."
            
        model_name = "gpt-4o-mini"
        if "openrouter" in os.environ.get("OPENAI_BASE_URL", "").lower():
            model_name = "openai/gpt-4o-mini"
             
        llm = ChatOpenAI(model=model_name, temperature=0)
        structured_llm = llm.with_structured_output(JobDetails)
        
        prompt = PromptTemplate.from_template("""
        You are an expert web data extractor. I am giving you the raw, unformatted text extracted from a job posting webpage.
        
        Extract the following information:
        1. Job Title
        2. Company Name
        3. Full Job Description (include requirements, responsibilities, etc.)
        
        If you cannot find a specific piece of information, return 'Unknown'.
        
        Raw Text:
        {raw_text}
        """)
        
        chain = prompt | structured_llm
        
        try:
            result = chain.invoke({"raw_text": raw_text[:20000]}) # Limit text
            return result
        except Exception as e:
            return JobDetails(job_title="Error", company="Error", job_description=str(e))

class AdapterFactory:
    @staticmethod
    def get_adapter(url: str) -> BaseAdapter:
        if "justremote.co" in url.lower():
            print("=> Using JustRemoteAdapter")
            return JustRemoteAdapter()
        elif "nodesk.co" in url.lower():
            print("=> Using NoDeskAdapter")
            return NoDeskAdapter()
        elif "workingnomads.com" in url.lower():
            print("=> Using WorkingNomadsAdapter")
            return WorkingNomadsAdapter()
        else:
            print("=> Using GenericAIAdapter")
            return GenericAIAdapter()
