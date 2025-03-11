# GitHub Actions AI Pipeline Generator

An intelligent system that generates, analyzes, and optimizes GitHub Actions workflows using AI. The tool provides comprehensive analysis reports and security recommendations for your CI/CD pipelines.

## Features

- 🤖 AI-powered workflow generation from natural language descriptions
- 🔒 Security compliance checking
- ⚡ Pipeline efficiency analysis
- 📊 Build quality assessment
- 📈 Performance metrics and recommendations
- 🔍 Automated best practices validation

## Prerequisites

- Python 3.7+
- Azure OpenAI API access or claude
- Environment variables configured

## Installation

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
   Create a `.env` file:
   ```properties
   AZURE_OPENAI_ENDPOINT="your_azure_openai_endpoint"
   AZURE_OPENAI_KEY="your_azure_openai_key"
   ```

## Usage

Generate and analyze a workflow:
```sh
python github_actions_ai.py --query "your workflow description"
```

Example queries:
- "Create a Python testing workflow with multiple Python versions"
- "Build and deploy a Django application"
- "Run linting and security checks on PR"

## Output

The tool generates:
1. **GitHub Actions Workflow** (`.github/workflows/`)
   - Automatically named based on the query
   - Valid YAML syntax
   - Best practices implemented

2. **Analysis Report** (`reports/`)
   - Build quality metrics
   - Security compliance
   - Efficiency analysis
   - Performance estimates
   - Recommendations

## Analysis Features

### Security Checks
- Action version validation
- Unsafe pattern detection
- Permission analysis
- Security best practices

### Efficiency Analysis
- Pipeline metrics
- Resource utilization
- Build time estimation
- Optimization suggestions

### Quality Gates
- Linting configuration
- Test coverage
- Type checking
- Dependency auditing

## Contributing

Contributions welcome! Areas for improvement:
- Additional workflow templates
- Enhanced security checks
- More analysis metrics
- Custom reporting formats

## License

MIT License
