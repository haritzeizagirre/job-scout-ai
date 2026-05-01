from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.agents import evaluate_job, draft_cover_letter

class JobState(TypedDict):
    target_role: str
    experience_level: str
    additional_filters: str
    job_title: str
    company: str
    job_description: str
    my_cv: str
    is_match: bool
    match_reason: str
    cover_letter: str

def evaluator_node(state: JobState):
    print(f"--- Evaluating Job: {state.get('job_title')} at {state.get('company')} ---")
    result = evaluate_job(
        state['target_role'],
        state.get('experience_level', 'Any'),
        state.get('additional_filters', ''),
        state['job_title'],
        state['company'],
        state['job_description'],
        state['my_cv']
    )
    print(f"Match: {result.is_match} | Reason: {result.match_reason}")
    return {"is_match": result.is_match, "match_reason": result.match_reason}

def drafter_node(state: JobState):
    print(f"--- Drafting Cover Letter for: {state.get('job_title')} ---")
    cover_letter = draft_cover_letter(
        state['job_title'],
        state['company'],
        state['job_description'],
        state['my_cv'],
        state['match_reason']
    )
    return {"cover_letter": cover_letter}

def route_based_on_match(state: JobState):
    if state.get('is_match'):
        return "drafter"
    return END

def build_graph():
    workflow = StateGraph(JobState)
    
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("drafter", drafter_node)
    
    workflow.set_entry_point("evaluator")
    
    workflow.add_conditional_edges(
        "evaluator",
        route_based_on_match,
        {
            "drafter": "drafter",
            END: END
        }
    )
    
    workflow.add_edge("drafter", END)
    
    return workflow.compile()
