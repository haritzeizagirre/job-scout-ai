import os
import re
from dotenv import load_dotenv
from src.scraper import scrape_live_url
from src.graph import build_graph

# Load environment variables
load_dotenv()

def slugify(value):
    """Convert string to slug for safe filenames."""
    value = str(value).lower()
    return re.sub(r'[\W_]+', '-', value)

def main():
    # 1. Read CV
    with open("my_cv.txt", "r", encoding="utf-8") as f:
        my_cv = f.read()

    # 2. Read URLs
    urls = []
    if os.path.exists("urls.txt"):
        with open("urls.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        print("urls.txt not found. Please create it and add job URLs.")
        return

    if not urls:
        print("urls.txt is empty. Please add some job URLs.")
        return

    # 3. Build graph
    graph = build_graph()

    # 4. Create outputs directory
    os.makedirs("outputs", exist_ok=True)

    # 5. Process each URL
    for i, url in enumerate(urls):
        print(f"\n================ Processing URL {i+1} ================")
        print(f"URL: {url}")
        
        try:
            # Scrape job details from live URL
            job_data = scrape_live_url(url)
            
            # Print extraction results for debugging
            print(f"Extracted Title: {job_data['job_title']}")
            print(f"Extracted Company: {job_data['company']}")
            
            initial_state = {
                "job_title": job_data["job_title"],
                "company": job_data["company"],
                "job_description": job_data["job_description"],
                "my_cv": my_cv,
            }
            
            # Run LangGraph workflow
            final_state = graph.invoke(initial_state)
            
            # Check if matched and save output
            if final_state.get("is_match"):
                safe_title = slugify(final_state['job_title'])
                safe_company = slugify(final_state['company'])
                output_file = f"outputs/{safe_company}_{safe_title}.md"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# Cover Letter for {final_state['job_title']} at {final_state['company']}\n\n")
                    f.write(f"**Reason for Match:** {final_state['match_reason']}\n\n")
                    f.write("---\n\n")
                    f.write(final_state.get("cover_letter", ""))
                print(f"Saved cover letter to {output_file}")
            else:
                print(f"Job at {url} was not a match. Skipping draft.")
                
        except Exception as e:
            print(f"Error processing {url}: {e}")

if __name__ == "__main__":
    main()
