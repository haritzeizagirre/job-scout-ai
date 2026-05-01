import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from src.scraper import scrape_live_url, extract_job_urls_from_page
from src.navigator import navigate_to_role_page
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
    # if os.path.exists("urls.txt"):
    #     with open("urls.txt", "r", encoding="utf-8") as f:
    #         urls = [line.strip() for line in f if line.strip()]

    # 3. Discover URLs from job boards
    target_role = os.environ.get("TARGET_ROLE", "Software Engineer")
    if os.path.exists("boards.txt"):
        with open("boards.txt", "r", encoding="utf-8") as f:
            boards = [line.strip() for line in f if line.strip()]
            
        if boards:
            print("\nAvailable boards:")
            for idx, b in enumerate(boards):
                print(f"{idx + 1}. {b}")
            print(f"{len(boards) + 1}. All of them")
            
            choice = input("\nSelect an option by number (default is All): ").strip()
            
            if choice and choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(boards):
                    boards = [boards[choice_idx]]
                elif choice_idx == len(boards):
                    pass # all
                else:
                    print("Invalid choice, running all.")
                    
            print(f"\nDiscovering job links for '{target_role}' from boards...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                for board_url in boards:
                    print(f"\n--- Navigating Board: {board_url} ---")
                    page = context.new_page()
                    try:
                        page.goto(board_url, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(3000)
                        
                        # Use Navigator to find the jobs
                        success = navigate_to_role_page(page, target_role)
                        if success:
                            discovered = extract_job_urls_from_page(page, target_role)
                            print(f"Discovered {len(discovered)} jobs on {board_url}")
                            urls.extend(discovered)
                        else:
                            print(f"Failed to navigate {board_url}")
                    except Exception as e:
                        print(f"Error exploring board {board_url}: {e}")
                    finally:
                        page.close()
                
                browser.close()

    if not urls:
        print("No job URLs found in urls.txt and no jobs discovered from boards.txt. Exiting.")
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
                    f.write(f"**URL:** {url}\n\n")
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
