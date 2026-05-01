from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

class MatchEvaluation(BaseModel):
    is_match: bool = Field(description="True if the candidate is a good match for the job, False otherwise.")
    match_reason: str = Field(description="A 1-2 sentence explanation of why the candidate is or is not a match.")

def evaluate_job(target_role: str, experience_level: str, additional_filters: str, job_title: str, company: str, job_description: str, my_cv: str) -> MatchEvaluation:
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
    
    IMPORTANT: We are SPECIFICALLY looking for a "{target_role}" position.
    Experience Level Required: {experience_level}
    Additional User Filters: {additional_filters}
    
    Job Title: {job_title}
    Company: {company}
    
    Job Description:
    {job_description}
    
    Candidate CV:
    {my_cv}
    
    Evaluate if this job is a match.
    CRITICAL RULE 1: If the Job Title '{job_title}' or Job Description is NOT a "{target_role}" position, you MUST return is_match=False and explain that the role does not match what we are looking for.
    CRITICAL RULE 2: If the job description strictly requires an experience level that conflicts with "{experience_level}", return is_match=False. (Ignore this rule if experience level is "Any").
    CRITICAL RULE 3: If there are additional filters ("{additional_filters}") and the job clearly violates them, return is_match=False.
    
    If the job passes the filters, evaluate if the candidate's skills and experience make them a good fit.
    
    Return a structured response with a boolean 'is_match' and a short 'match_reason'.
    """)
    
    chain = prompt | structured_llm
    
    return chain.invoke({
        "target_role": target_role,
        "experience_level": experience_level,
        "additional_filters": additional_filters,
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
