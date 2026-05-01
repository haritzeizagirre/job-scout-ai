import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from src.scraper import scrape_live_url, extract_job_urls_from_page
from src.navigator import navigate_to_role_page
from src.graph import build_graph
from src.db import (
    is_url_already_rejected,
    save_match,
    save_non_match,
    update_scout_run,
)

# Load environment variables
load_dotenv()


def slugify(value):
    """Convert string to slug for safe filenames."""
    value = str(value).lower()
    return re.sub(r'[\W_]+', '-', value)


def run_job_scout(
    target_role: str,
    boards: list[str],
    my_cv: str,
    experience_level: str = "Any",
    additional_filters: str = "",
    run_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    """
    Main scouting logic.
    Returns a dict: {"matches": int, "skipped": int, "ai_calls": int}
    """
    urls = []
    match_count = 0
    skip_count = 0
    ai_calls = 0

    print(f"\nDiscovering job links for '{target_role}' from boards...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless — same results, no GUI needed on server
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        for board_url in boards:
            print(f"\n--- Navigating Board: {board_url} ---")
            page = context.new_page()
            try:
                page.goto(board_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

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
        print("No job URLs found. Exiting.")
        if run_id:
            update_scout_run(run_id, "done", 0, 0)
        return {"matches": 0, "skipped": 0, "ai_calls": 0}

    # Build LangGraph workflow
    graph = build_graph()

    # Create outputs directory (legacy — kept for guest users)
    os.makedirs("outputs", exist_ok=True)

    for i, url in enumerate(urls):
        print(f"\n================ Processing URL {i+1}/{len(urls)} ================")
        print(f"URL: {url}")

        # ── Non-match skip check ─────────────────────────────────────────────
        if user_id and is_url_already_rejected(user_id, url):
            print(f"[SKIP] Already rejected previously: {url}")
            skip_count += 1
            continue

        try:
            job_data = scrape_live_url(url)
            print(f"Extracted Title: {job_data['job_title']}")
            print(f"Extracted Company: {job_data['company']}")

            initial_state = {
                "target_role": target_role,
                "experience_level": experience_level,
                "additional_filters": additional_filters,
                "job_title": job_data["job_title"],
                "company": job_data["company"],
                "job_description": job_data["job_description"],
                "my_cv": my_cv,
            }

            final_state = graph.invoke(initial_state)
            ai_calls += 1  # evaluator call
            if final_state.get("is_match"):
                ai_calls += 1  # drafter call (only on matches)

            if final_state.get("is_match"):
                # ── Save to DB ───────────────────────────────────────────────
                if run_id and user_id:
                    save_match(
                        run_id=run_id,
                        user_id=user_id,
                        job_url=url,
                        job_title=final_state["job_title"],
                        company=final_state["company"],
                        match_reason=final_state.get("match_reason", ""),
                        cover_letter=final_state.get("cover_letter", ""),
                    )

                # ── Legacy filesystem save (guests + backwards compat) ────────
                safe_title = slugify(final_state["job_title"])
                safe_company = slugify(final_state["company"])
                output_file = f"outputs/{safe_company}_{safe_title}.md"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# {final_state['job_title']} at {final_state['company']}\n\n")
                    f.write(f"**URL:** {url}\n\n")
                    f.write(f"**Reason for Match:** {final_state['match_reason']}\n\n")
                    f.write("---\n\n")
                    f.write(final_state.get("cover_letter", ""))
                print(f"Match saved: {output_file}")
                match_count += 1

            else:
                print(f"Not a match: {url} — {final_state.get('match_reason', '')}")
                # ── Save non-match to DB (skip-list) ─────────────────────────
                if run_id and user_id:
                    save_non_match(
                        run_id=run_id,
                        user_id=user_id,
                        job_url=url,
                        job_title=final_state.get("job_title", job_data.get("job_title", "")),
                        company=final_state.get("company", job_data.get("company", "")),
                        rejection_reason=final_state.get("match_reason", ""),
                    )

        except Exception as e:
            print(f"Error processing {url}: {e}")

    # ── Finalise run record ──────────────────────────────────────────────────
    if run_id:
        update_scout_run(run_id, "done", match_count, skip_count)

    return {"matches": match_count, "skipped": skip_count, "ai_calls": ai_calls}


def main():
    """CLI entry point for local testing."""
    with open("my_cv.txt", "r", encoding="utf-8") as f:
        my_cv = f.read()

    target_role = os.environ.get("TARGET_ROLE", "Software Engineer")
    boards = []
    if os.path.exists("boards.txt"):
        with open("boards.txt", "r", encoding="utf-8") as f:
            all_boards = [line.strip() for line in f if line.strip()]

        if all_boards:
            print("\nAvailable boards:")
            for idx, b in enumerate(all_boards):
                print(f"{idx + 1}. {b}")
            print(f"{len(all_boards) + 1}. All of them")

            choice = input("\nSelect an option by number (default is All): ").strip()
            if choice and choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(all_boards):
                    boards = [all_boards[choice_idx]]
                elif choice_idx == len(all_boards):
                    boards = all_boards
                else:
                    boards = all_boards
            else:
                boards = all_boards

    result = run_job_scout(target_role, boards, my_cv)
    print(f"\nDone — Matches: {result['matches']}, Skipped: {result['skipped']}")


if __name__ == "__main__":
    main()
