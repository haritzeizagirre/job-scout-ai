from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

class MatchEvaluation(BaseModel):
    is_match: bool = Field(description="True if the candidate is a good match for the job, False otherwise.")
    match_reason: str = Field(description="A 1-2 sentence explanation of why the candidate is or is not a match.")

def evaluate_job(job_title: str, company: str, job_description: str, my_cv: str) -> MatchEvaluation:
    # Uses environment variables OPENAI_API_KEY and optionally OPENAI_BASE_URL
    llm = ChatOpenAI(model="openai/gpt-4o-mini", temperature=0) # using openai/gpt-4o-mini for openrouter compatibility
    
    # Let's fallback to standard gpt-4o-mini if not using openrouter
    import os
    model_name = "gpt-4o-mini"
    if "openrouter" in os.environ.get("OPENAI_BASE_URL", ""):
         model_name = "openai/gpt-4o-mini"
         
    llm = ChatOpenAI(model=model_name, temperature=0)
    structured_llm = llm.with_structured_output(MatchEvaluation)
    
    prompt = PromptTemplate.from_template("""
    You are an expert technical recruiter evaluating a candidate for a role.
    
    Job Title: {job_title}
    Company: {company}
    
    Job Description:
    {job_description}
    
    Candidate CV:
    {my_cv}
    
    Evaluate if this candidate is a good match for the job based on their skills and experience.
    Return a structured response with a boolean 'is_match' and a short 'match_reason'.
    """)
    
    chain = prompt | structured_llm
    
    return chain.invoke({
        "job_title": job_title,
        "company": company,
        "job_description": job_description,
        "my_cv": my_cv
    })

def draft_cover_letter(job_title: str, company: str, job_description: str, my_cv: str, match_reason: str) -> str:
    import os
    model_name = "gpt-4o-mini"
    if "openrouter" in os.environ.get("OPENAI_BASE_URL", ""):
         model_name = "openai/gpt-4o-mini"
         
    llm = ChatOpenAI(model=model_name, temperature=0.7)
    
    prompt = PromptTemplate.from_template("""
    You are the candidate applying for the job. Write a highly professional, 3-paragraph cover letter.
    
    Job Title: {job_title}
    Company: {company}
    
    Job Description:
    {job_description}
    
    My CV:
    {my_cv}
    
    Why I am a match:
    {match_reason}
    
    Write a tailored cover letter highlighting the specific overlapping skills. Do not include placeholder addresses, just start with "Dear Hiring Manager,".
    """)
    
    chain = prompt | llm
    
    response = chain.invoke({
        "job_title": job_title,
        "company": company,
        "job_description": job_description,
        "my_cv": my_cv,
        "match_reason": match_reason
    })
    
    return response.content
