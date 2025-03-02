# github_actions_ai.py
import os
import re
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, validator
from langchain.llms import AzureOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import argparse

load_dotenv()

class WorkflowSchema(BaseModel):
    on: dict
    jobs: dict

    @validator('on')
    def valid_triggers(cls, value):
        allowed = ['push', 'pull_request', 'workflow_dispatch']
        if not any(k in allowed for k in value.keys()):
            raise ValueError("Invalid trigger event")
        return value

    @validator('jobs')
    def valid_jobs(cls, value):
        if not all(isinstance(v, dict) for v in value.values()):
            raise ValueError("Jobs must be dictionary of job configurations")
        return value

def login_to_github(context, username, password):
    page = context.new_page()
    page.goto("https://github.com/login")
    page.fill("input[name=login]", username)
    page.fill("input[name=password]", password)
    page.click("input[name=commit]")
    page.wait_for_url("https://github.com/")
    return page

def navigate_to_actions(page, repo_name):
    page.goto(f"https://github.com/{repo_name}/actions")
    page.wait_for_selector(".js-new-workflow")

def generate_yaml_prompt(query):
    prompt = PromptTemplate(
        input_variables=["query"],
        template="""Generate valid GitHub Actions YAML for:
        {query}
        Output only the YAML content without explanation."""
    )
    return prompt

def create_azure_llm():
    return AzureOpenAI(
        model_name="gpt-4o",
        openai_api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
        openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
        openai_api_version="2024-10-21"
    )

def main():
    parser = argparse.ArgumentParser(description="GitHub Actions AI")
    parser.add_argument("--repo", required=True, help="Repository name (user/repo)")
    parser.add_argument("--query", required=True, help="Workflow requirements description")
    parser.add_argument("--branch", default="main", help="Target branch")
    args = parser.parse_args()

    # Setup
    username = os.getenv("GITHUB_USERNAME")
    password = os.getenv("GITHUB_PASSWORD")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_KEY")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        try:
            # Authentication
            page = login_to_github(context, username, password)

            # Navigate to Actions
            navigate_to_actions(page, args.repo)

            # Generate YAML
            llm = create_azure_llm()
            prompt = generate_yaml_prompt(args.query)
            chain = LLMChain(llm=llm, prompt=prompt)
            yaml_content = chain.run(args.query)

            # Validate YAML
            workflow = WorkflowSchema.parse_raw(yaml_content)

            # Create workflow
            page.click(".js-new-workflow")
            page.fill('input[placeholder="Workflow name"]', "AI-Generated Workflow")
            page.frameLocator("iframe").fill("div Monaco-editor.no-user-select", yaml_content)
            
            # Commit changes
            page.click('button:text("Start commit")')
            page.click('button[js-controller="BranchCommitButton"]')
            page.wait_for_load_state("networkidle")

            print(f"Workflow created successfully for {args.repo} on {args.branch}")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()