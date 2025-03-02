# GitHub Actions AI

This project automates the creation of GitHub Actions workflows using AI. It leverages Azure OpenAI and Playwright to generate and validate YAML configurations based on user queries.

## Prerequisites

- Python 3.7+
- GitHub account
- Azure OpenAI account

## Setup

1. **Clone the repository**:
   ```sh
   git clone https://github.com/vikashegde21/github-ai-agent.git
   cd github-ai-agent
   ```

2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory with the following content:
   ```properties
   GITHUB_USERNAME="your_github_username"
   GITHUB_PASSWORD="your_github_password"
   GITHUB_TOKEN="your_github_token"
   OPENAI_API_KEY="your_openai_api_key"
   AZURE_OPENAI_ENDPOINT="https://your_azure_openai_endpoint"
   ```

## Usage

Run the script with the required arguments:
```sh
python github_actions_ai.py --repo <user/repo> --query "<workflow requirements>" --branch <branch_name>
```

### Example
```sh
python github_actions_ai.py --repo vikashegde21/github-ci-agent- --query "Run Python tests on push to main branch" --branch main
```

## How It Works

1. **Authentication**: Logs into GitHub using the provided credentials.
2. **Navigation**: Navigates to the GitHub Actions page of the specified repository.
3. **YAML Generation**: Uses Azure OpenAI to generate a GitHub Actions YAML file based on the provided query.
4. **Validation**: Validates the generated YAML against a predefined schema.
5. **Workflow Creation**: Creates a new workflow in the repository with the generated YAML content.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License.
