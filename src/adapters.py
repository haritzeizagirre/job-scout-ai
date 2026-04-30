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

class LinkedInAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        # LinkedIn public job pages usually have these selectors
        try:
            job_title = page.locator("h1.top-card-layout__title, h1").first.inner_text(timeout=5000)
        except Exception:
            job_title = "Unknown LinkedIn Title"
            
        try:
            company = page.locator("a.topcard__org-name-link, span.topcard__flavor").first.inner_text(timeout=5000)
        except Exception:
            company = "Unknown LinkedIn Company"
            
        try:
            job_description = page.locator("div.show-more-less-html__markup, div.description__text").first.inner_text(timeout=5000)
        except Exception:
            job_description = page.locator("body").inner_text(timeout=5000)
            
        return JobDetails(job_title=job_title.strip(), company=company.strip(), job_description=job_description.strip())

class InfoJobsAdapter(BaseAdapter):
    def extract(self, page: Page) -> JobDetails:
        try:
            job_title = page.locator("h1.title, h1").first.inner_text(timeout=5000)
        except Exception:
            job_title = "Unknown InfoJobs Title"
            
        try:
            company = page.locator("a.link, .company-name").first.inner_text(timeout=5000)
        except Exception:
            company = "Unknown InfoJobs Company"
            
        try:
            job_description = page.locator("#tracking-scroll-description, .description").first.inner_text(timeout=5000)
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
        if "linkedin.com" in url.lower():
            print("=> Using LinkedInAdapter")
            return LinkedInAdapter()
        elif "infojobs.net" in url.lower():
            print("=> Using InfoJobsAdapter")
            return InfoJobsAdapter()
        else:
            print("=> Using GenericAIAdapter")
            return GenericAIAdapter()
