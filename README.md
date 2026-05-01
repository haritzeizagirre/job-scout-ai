# AI Job Scout

Student: Haritz Eizagirre

An automated AI assistant designed to streamline the job search process using LangGraph, Playwright, and OpenAI. The tool visits live job posting URLs, evaluates the job descriptions against your personal CV using an LLM, and automatically drafts highly tailored cover letters for the roles that are a good match.

## Current Features

- **Autonomous Job Board Navigator**: Automatically navigates supported job boards (like JustRemote, NoDesk, Working Nomads), searches for your target role using an LLM-powered agent, and extracts the relevant job links.
- **Smart Adapter Pattern**: Automatically selects the best extraction strategy based on the URL:
  - **JustRemote / NoDesk / WorkingNomads Adapters**: Fast extraction using specific CSS selectors for these boards.
  - **Generic AI Adapter**: A smart fallback for unknown pages. It extracts raw page text and uses OpenAI to structure the job title, company, and description.
- **AI Evaluator**: Acts as a strict technical recruiter, comparing the extracted job requirements to your CV and deciding if you are a match.
- **AI Drafter**: If the Evaluator determines a match, the Drafter automatically writes a professional, 3-paragraph cover letter highlighting your specific overlapping skills.

## Prerequisites

- Python 3.10+
- An OpenAI API Key (or OpenRouter API Key)

## Setup Instructions

1. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

4. **Environment Variables:**
   Configure your `.env` file in the root directory. If you are using OpenRouter, your file should look like this:
   ```env
   OPENROUTER_API_KEY="your_api_key_here"
   OPENAI_API_KEY="${OPENROUTER_API_KEY}"
   OPENAI_BASE_URL="https://openrouter.ai/api/v1"
   TARGET_ROLE="Software Engineer"
   ```

## How to Use

1. **Add Your CV**: Update the `my_cv.txt` file with your own resume/CV information.
2. **Configure Target Role**: Ensure `TARGET_ROLE` in your `.env` matches the job title you are looking for.
3. **Configure Boards**: Open `boards.txt` and ensure the job boards you want to scan are listed (e.g., `https://justremote.co`).
4. **Run the Application**:
   ```bash
   python main.py
   ```
5. **Select Boards**: The script will prompt you in the terminal to select which board to scan, or press Enter to scan all of them.
6. **Monitor the Browser**: A browser window will pop up. The script's LLM agent will autonomously navigate the site, search for your role, extract job links, and evaluate them.
7. **Review Cover Letters**: For any jobs that are a match, the script will save a customized cover letter in the `outputs/` directory (e.g., `outputs/company-name_job-title.md`).