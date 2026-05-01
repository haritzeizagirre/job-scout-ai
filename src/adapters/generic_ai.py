import os
from playwright.sync_api import Page
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from .base import BaseAdapter, JobDetails

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
