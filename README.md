# AI Job Scout

Student: Haritz Eizagirre

An automated AI assistant designed to streamline the job search process using LangGraph, Playwright, and OpenAI. The tool visits live job posting URLs, evaluates the job descriptions against your personal CV using an LLM, and automatically drafts highly tailored cover letters for the roles that are a good match.

## Current Features

- **Live Web Scraping**: Uses Playwright to navigate to job URLs in a visible browser window, allowing you to bypass captchas or login walls manually if needed.
- **Smart Adapter Pattern**: Automatically selects the best extraction strategy based on the URL:
  - **LinkedIn Adapter**: Fast extraction using specific CSS selectors.
  - **InfoJobs Adapter**: Fast extraction for InfoJobs listings.
  - **Generic AI Adapter**: A smart fallback for unknown company career pages. It extracts the raw page text and uses OpenAI to structure the job title, company, and description.
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
   ```

## How to Use

1. **Add Your CV**: Update the `my_cv.txt` file with your own resume/CV information.
2. **Add Job URLs**: Open `urls.txt` and paste the URLs of the job postings you want to apply for (one URL per line).
3. **Run the Application**:
   ```bash
   python main.py
   ```
4. **Monitor the Browser**: A browser window will pop up. The script will wait on each page to let it load. If you hit a login wall (like on LinkedIn), quickly log in manually. The script will continue extracting once the page is loaded.
5. **Review Cover Letters**: The script will output its evaluations to the console. For any jobs that are a match, it will save a customized cover letter in the `outputs/` directory (e.g., `outputs/company-name_job-title.md`).