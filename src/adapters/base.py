from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from playwright.sync_api import Page

class JobDetails(BaseModel):
    job_title: str = Field(description="The title of the job role")
    company: str = Field(description="The name of the company offering the job")
    job_description: str = Field(description="The full job description and requirements")

class BaseAdapter(ABC):
    @abstractmethod
    def extract(self, page: Page) -> JobDetails:
        pass
