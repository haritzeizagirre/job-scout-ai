import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from playwright.sync_api import Page
import time

class NavigationAction(BaseModel):
    action: str = Field(description="The action to perform: 'type', 'click', or 'done'. 'done' means we are already on a page with job results for the target role.")
    element_id: str = Field(description="The data-ai-id of the element to interact with. Leave empty if action is 'done'.")
    value: str = Field(description="The text to type if action is 'type'. Leave empty otherwise.")

def annotate_and_extract_elements(page: Page):
    """
    Injects data-ai-id into interactive elements and returns a summary of them for the LLM.
    """
    elements_summary = []
    
    # 1. Annotate inputs
    inputs = page.locator("input[type='text'], input[type='search'], input:not([type])").all()
    for i, el in enumerate(inputs):
        try:
            if not el.is_visible():
                continue
            ai_id = f"input-{i}"
            el.evaluate(f"node => node.setAttribute('data-ai-id', '{ai_id}')")
            placeholder = el.get_attribute('placeholder') or ''
            name = el.get_attribute('name') or ''
            elements_summary.append(f"[input] data-ai-id='{ai_id}' placeholder='{placeholder}' name='{name}'")
        except Exception:
            pass

    # 2. Annotate buttons
    buttons = page.locator("button").all()
    for i, el in enumerate(buttons):
        try:
            if not el.is_visible():
                continue
            ai_id = f"button-{i}"
            el.evaluate(f"node => node.setAttribute('data-ai-id', '{ai_id}')")
            text = el.inner_text().strip()[:50]
            elements_summary.append(f"[button] data-ai-id='{ai_id}' text='{text}'")
        except Exception:
            pass
            
    # 3. Annotate links
    links = page.locator("a").all()
    for i, el in enumerate(links):
        try:
            if not el.is_visible():
                continue
            text = el.inner_text().strip()
            if not text:
                continue
            # Keep it reasonable length
            text = text[:50].replace('\n', ' ')
            ai_id = f"link-{i}"
            el.evaluate(f"node => node.setAttribute('data-ai-id', '{ai_id}')")
            href = el.get_attribute('href') or ''
            elements_summary.append(f"[link] data-ai-id='{ai_id}' text='{text}' href='{href}'")
        except Exception:
            pass
            
    return "\n".join(elements_summary)

def navigate_to_role_page(page: Page, target_role: str):
    """
    Uses LLM to decide how to navigate the current page to find jobs for the target role.
    Returns True if it thinks it successfully navigated or is already there.
    """
    model_name = "gpt-4o-mini"
    if "openrouter" in os.environ.get("OPENAI_BASE_URL", "").lower():
        model_name = "openai/gpt-4o-mini"
            
    llm = ChatOpenAI(model=model_name, temperature=0)
    structured_llm = llm.with_structured_output(NavigationAction)
    
    prompt = PromptTemplate.from_template("""
    You are an autonomous web navigator. Your goal is to find job postings for the role: "{target_role}".
    
    You are currently on: {current_url}
    
    Here are the interactive elements on the page:
    {elements}
    
    Determine the BEST next action to get to a list of jobs for "{target_role}".
    - If there is a search input, you should probably 'type' the target role into it (and the system will automatically press Enter).
    - If there is a category link that matches the role closely, you can 'click' it.
    - If you believe we are ALREADY on a page showing job results for this role, output 'done'.
    
    Return the action, the data-ai-id of the element to interact with, and the value to type (if applicable).
    """)
    
    max_steps = 3
    for step in range(max_steps):
        print(f"--- Navigation Step {step+1} ---")
        page.wait_for_timeout(2000) # Let page settle
        elements_text = annotate_and_extract_elements(page)
        
        # If too many elements, truncate to save tokens (just taking first 200 elements)
        lines = elements_text.split('\n')
        if len(lines) > 200:
            elements_text = "\n".join(lines[:200])
            
        try:
            action_plan = structured_llm.invoke(prompt.format(
                target_role=target_role,
                current_url=page.url,
                elements=elements_text
            ))
            
            print(f"LLM Decision: {action_plan.action} on {action_plan.element_id} with value '{action_plan.value}'")
            
            if action_plan.action == "done":
                print("Navigator reached the destination.")
                return True
                
            if not action_plan.element_id:
                print("No element ID provided. Stopping.")
                return False
                
            locator = page.locator(f"[data-ai-id='{action_plan.element_id}']").first
            
            if action_plan.action == "type":
                locator.fill(action_plan.value)
                # Press enter after typing to trigger search
                locator.press("Enter")
                page.wait_for_timeout(5000) # Wait for results
                return True # We assume submitting a search takes us to the results
                
            elif action_plan.action == "click":
                locator.click()
                page.wait_for_timeout(5000)
                # We loop around to see if we need to do anything else, or if we are 'done'
                
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
            
    return True # Assume we got somewhere after max steps
