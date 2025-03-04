#***Ignore this file ***




# github_actions_ai.py
import os
import yaml
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel, SecretStr, validator
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from playwright.sync_api import sync_playwright
import csv
#from PyPDF2 import PdfReader
import logging
import argparse

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

class GitHubWorkflowAgent:
    def __init__(self):
        self.model = AzureChatOpenAI(
            model='gpt-4o',
            api_version='2024-10-21',
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            api_key=SecretStr(os.getenv('OPENAI_API_KEY', '')).get_secret_value(),
        )

    def generate_yaml(self, query: str) -> str:
        prompt = PromptTemplate(
            input_variables=["query"],
            template="""Generate a valid GitHub Actions YAML workflow based on the following requirements:
            {query}
            Output only the YAML content without explanation."""
        )
        chain = LLMChain(llm=self.model, prompt=prompt)
        return chain.run(query)

    def validate_yaml(self, yaml_content: str) -> WorkflowSchema:
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
            return WorkflowSchema(**parsed_yaml)
        except Exception as e:
            logging.error(f"Invalid YAML: {str(e)}")
            raise

    def deploy_workflow(self, repo_name: str, branch: str, workflow_name: str, yaml_content: str):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # Login to GitHub
            page.goto("https://github.com/login")
            page.fill("input[name=login]", os.getenv("GITHUB_USERNAME"))
            page.fill("input[name=password]", os.getenv("GITHUB_PASSWORD"))
            page.click("input[name=commit]")
            page.wait_for_url("https://github.com/")

            # Navigate to Actions Tab
            page.goto(f"https://github.com/{repo_name}/actions")
            page.click(".js-new-workflow")

            # Create Workflow
            page.fill('input[placeholder="Workflow name"]', workflow_name)
            iframe = page.frame_locator("iframe")
            iframe.fill("div.Monaco-editor.no-user-select", yaml_content)

            # Commit Changes
            page.click('button:text("Start commit")')
            page.click('button[js-controller="BranchCommitButton"]')
            page.wait_for_load_state("networkidle")

            logging.info(f"Workflow '{workflow_name}' deployed successfully to {repo_name}:{branch}")
            context.close()
            browser.close()

def main():
    parser = argparse.ArgumentParser(description="GitHub Actions AI Agent")
    parser.add_argument("--repo", required=True, help="Repository name (user/repo)")
    parser.add_argument("--query", required=True, help="Workflow requirements description")
    parser.add_argument("--branch", default="main", help="Target branch")
    parser.add_argument("--csv", help="Path to CSV file for additional data")
    parser.add_argument("--pdf", help="Path to PDF file for additional data")
    args = parser.parse_args()

    agent = GitHubWorkflowAgent()

   
    # Generate YAML
    query = args.query + additional_data
    yaml_content = agent.generate_yaml(query)
    logging.info(f"Generated YAML:\n{yaml_content}")

    # Validate YAML
    try:
        agent.validate_yaml(yaml_content)
    except Exception as e:
        logging.error(f"Validation failed: {str(e)}")
        sys.exit(1)

    # Deploy Workflow
    agent.deploy_workflow(repo_name=args.repo, branch=args.branch, workflow_name="AI-Generated-Workflow", yaml_content=yaml_content)

if __name__ == "__main__":
    main()
