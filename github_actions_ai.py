# github_actions_ai.py
import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import argparse
import uuid
import yaml
from langchain_core.messages import AIMessage
from typing import Optional, Dict, Any
from datetime import datetime
import json

load_dotenv()

class WorkflowSchema(BaseModel):
    name: Optional[str] = None
    on: Dict[str, Any]
    jobs: Dict[str, Dict[str, Any]]

    @field_validator('on', mode='before')
    @classmethod
    def valid_triggers(cls, value):
        # Convert the raw YAML structure to the expected format
        if isinstance(value, dict):
            # Handle nested structure (e.g., {"push": {"branches": ["main"]}})
            return value
        elif isinstance(value, str):
            # Handle simple string triggers
            return {value: {}}
        raise ValueError("Invalid trigger event")

    @field_validator('jobs')
    @classmethod
    def valid_jobs(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Jobs must be a dictionary")
        for job_config in value.values():
            if not isinstance(job_config, dict):
                raise ValueError("Each job must be a dictionary of configurations")
            if 'runs-on' not in job_config:
                raise ValueError("Each job must specify 'runs-on'")
        return value

def generate_yaml_prompt(query):
    return PromptTemplate.from_template(
        """Generate valid GitHub Actions YAML for: {query}
        Output only the YAML content without explanation."""
    )

def create_azure_llm():
    return ChatOpenAI(
        model_name="gpt-4o",
        openai_api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
        openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
        #AZURE_OPENAI_ENDPOINT="https://models.inference.ai.azure.com"
    )

def generate_workflow_filename(query):
    # Convert query to a filename-friendly format
    base_name = query.lower().replace(" ", "-")[:30]  # Take first 30 chars
    unique_id = uuid.uuid4().hex[:8]  # Add 8 char unique identifier
    return f"{base_name}-{unique_id}.yml"

def create_local_workflow_file(yaml_content, query):
    workflow_name = generate_workflow_filename(query)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_dir = os.path.join(base_dir, ".github", "workflows")
    os.makedirs(workflow_dir, exist_ok=True)
    
    file_path = os.path.join(workflow_dir, workflow_name)
    with open(file_path, "w") as file:
        file.write(yaml_content)
    print(f"New workflow file created at {file_path}")
    return file_path

def extract_yaml_content(response):
    if isinstance(response, AIMessage):
        content = response.content
        # Remove markdown code block indicators if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("yaml"):
                content = content[4:]
        return content.strip()
    return response

def fix_yaml_structure(yaml_dict):
    # Fix the 'on' field if it's parsed incorrectly
    if True in yaml_dict:
        yaml_dict['on'] = yaml_dict[True]
        del yaml_dict[True]
    return yaml_dict

def check_security_compliance(yaml_dict):
    security_issues = {
        "critical": [],
        "warning": [],
        "info": []
    }
    
    if 'jobs' in yaml_dict:
        for job_id, job in yaml_dict['jobs'].items():
            if 'steps' in job:
                for step in job['steps']:
                    # Check action versions
                    if 'uses' in step and '@' in step['uses']:
                        action = step['uses']
                        if '@master' in action or '@main' in action:
                            security_issues["critical"].append(f"⛔ Using unstable version in {action}. Specify a fixed version.")
                        elif '@v1' in action:
                            security_issues["warning"].append(f"⚠️ Consider updating {action} to latest version")
                    
                    # Check for unsafe patterns in commands
                    if 'run' in step:
                        cmd = step['run'].lower()
                        if 'curl' in cmd and not cmd.startswith('curl --fail'):
                            security_issues["warning"].append(f"⚠️ Unsafe curl usage without --fail in step '{step.get('name', 'unnamed')}'")
                        if 'wget' in cmd:
                            security_issues["warning"].append(f"⚠️ Consider using curl --fail instead of wget in step '{step.get('name', 'unnamed')}'")
                        if 'sudo' in cmd:
                            security_issues["critical"].append(f"⛔ Sudo usage detected in step '{step.get('name', 'unnamed')}'")
                        if '>' in cmd or '>>' in cmd:
                            security_issues["info"].append(f"ℹ️ File system write detected in step '{step.get('name', 'unnamed')}'")

    return security_issues

def analyze_pipeline_efficiency(yaml_dict):
    analysis = {
        "metrics": {
            "parallel_jobs": len(yaml_dict.get('jobs', {})),
            "total_steps": sum(len(job.get('steps', [])) for job in yaml_dict['jobs'].values()),
            "matrix_builds": any('matrix' in job.get('strategy', {}) for job in yaml_dict['jobs'].values()),
            "caching_used": any('cache' in step.get('uses', '') for job in yaml_dict['jobs'].values() for step in job.get('steps', [])),
        },
        "optimization_suggestions": [],
        "best_practices": []
    }
    
    # Check for optimization opportunities
    if analysis["metrics"]["total_steps"] > 10:
        analysis["optimization_suggestions"].append("🔄 Consider splitting into multiple jobs for better parallelization")
    
    if not analysis["metrics"]["caching_used"]:
        analysis["optimization_suggestions"].append("💾 Implement dependency caching to speed up builds")
    
    if not analysis["metrics"]["matrix_builds"] and analysis["metrics"]["parallel_jobs"] == 1:
        analysis["optimization_suggestions"].append("⚡ Consider using matrix strategy for parallel testing")
    
    # Check for best practices
    for job_id, job in yaml_dict['jobs'].items():
        if not job.get('timeout-minutes'):
            analysis["best_practices"].append("⏱️ Add timeout-minutes to prevent hanging jobs")
        if 'continue-on-error' not in job:
            analysis["best_practices"].append("🔄 Consider using continue-on-error for non-critical steps")

    return analysis

def analyze_build_quality(yaml_dict):
    build_analysis = {
        "quality_gates": [],
        "test_coverage": False,
        "linting": False,
        "type_checking": False,
        "dependency_audit": False,
        "estimated_success_rate": 0
    }
    
    for job in yaml_dict.get('jobs', {}).values():
        for step in job.get('steps', []):
            step_name = step.get('name', '').lower()
            step_run = step.get('run', '').lower()
            step_uses = step.get('uses', '').lower()
            
            # Check for testing frameworks
            if any(tool in f"{step_name} {step_run} {step_uses}" 
                  for tool in ['pytest', 'unittest', 'coverage']):
                build_analysis["quality_gates"].append("Unit Testing")
                
            # Check for linting
            if any(linter in f"{step_name} {step_run} {step_uses}"
                  for linter in ['flake8', 'pylint', 'black', 'ruff']):
                build_analysis["linting"] = True
                build_analysis["quality_gates"].append("Code Style")
                
            # Check for type checking
            if any(checker in f"{step_name} {step_run} {step_uses}"
                  for checker in ['mypy', 'pytype', 'pyre']):
                build_analysis["type_checking"] = True
                build_analysis["quality_gates"].append("Type Safety")
                
            # Check for dependency scanning
            if any(scanner in f"{step_name} {step_run} {step_uses}"
                  for scanner in ['dependabot', 'snyk', 'safety']):
                build_analysis["dependency_audit"] = True
                build_analysis["quality_gates"].append("Dependency Check")
                
            # Check for coverage
            if 'coverage' in f"{step_name} {step_run} {step_uses}":
                build_analysis["test_coverage"] = True
    
    # Calculate estimated success rate
    base_rate = 70  # Base success rate
    if build_analysis["linting"]: base_rate += 10
    if build_analysis["type_checking"]: base_rate += 10
    if build_analysis["test_coverage"]: base_rate += 5
    if build_analysis["dependency_audit"]: base_rate += 5
    
    build_analysis["estimated_success_rate"] = min(base_rate, 100)
    return build_analysis

def generate_report(yaml_dict, security_issues, efficiency_analysis, output_path, query):
    build_analysis = analyze_build_quality(yaml_dict)
    
    report_content = f"""# 🚀 Workflow Analysis Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📝 Query
```
{query}
```

## 🏗️ Build Quality Analysis

### Quality Gates
{chr(10).join(f"- ✅ {gate}" for gate in build_analysis["quality_gates"]) or "❌ No quality gates configured"}

### Code Quality Metrics
- 🔍 Linting: {'✅ Enabled' if build_analysis["linting"] else '❌ Not configured'}
- 🏷️ Type Checking: {'✅ Enabled' if build_analysis["type_checking"] else '❌ Not configured'}
- 📊 Test Coverage: {'✅ Enabled' if build_analysis["test_coverage"] else '❌ Not configured'}
- 🔒 Dependency Audit: {'✅ Enabled' if build_analysis["dependency_audit"] else '❌ Not configured'}

### Build Success Estimation
- 📈 Estimated Success Rate: {build_analysis["estimated_success_rate"]}%
- 🎯 Quality Score: {'🟢 High' if build_analysis["estimated_success_rate"] >= 90 else '🟡 Medium' if build_analysis["estimated_success_rate"] >= 75 else '🔴 Low'}

## 🔒 Security Analysis
{generate_security_section(security_issues)}

## ⚡ Pipeline Efficiency
{generate_efficiency_section(efficiency_analysis)}

## 📊 Implementation Details

### Current Implementation
```yaml
{yaml.dump(yaml_dict, default_flow_style=False, sort_keys=False)}
```

### Recommended Improvements
{generate_recommendations(build_analysis, efficiency_analysis)}

## 📈 Performance Metrics
- 🕒 Estimated Total Runtime: {calculate_runtime(efficiency_analysis, build_analysis)} minutes
- 💪 Resource Utilization: {calculate_resource_usage(efficiency_analysis)}
- ⚡ Pipeline Efficiency Score: {calculate_efficiency_score(efficiency_analysis, build_analysis)}/100

## 🔄 Continuous Integration Best Practices
{generate_ci_best_practices(build_analysis, efficiency_analysis)}

## 📚 References
- [GitHub Actions Security Hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Workflow Optimization Guide](https://docs.github.com/en/actions/using-workflows/about-workflows)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/best-practices-for-using-github-actions)
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    return output_path

def generate_security_section(security_issues):
    return f"""### Critical Issues
{chr(10).join(f"- {issue}" for issue in security_issues["critical"]) or "✅ No critical issues found"}

### Warnings
{chr(10).join(f"- {issue}" for issue in security_issues["warning"]) or "✅ No warnings found"}

### Information
{chr(10).join(f"- {issue}" for issue in security_issues["info"]) or "ℹ️ No additional information"}"""

def generate_efficiency_section(efficiency_analysis):
    return f"""### Pipeline Metrics
- 🔄 Parallel Jobs: {efficiency_analysis["metrics"]["parallel_jobs"]}
- 📋 Total Steps: {efficiency_analysis["metrics"]["total_steps"]}
- 🔀 Matrix Builds: {'✅ Yes' if efficiency_analysis["metrics"]["matrix_builds"] else '❌ No'}
- 💾 Caching: {'✅ Implemented' if efficiency_analysis["metrics"]["caching_used"] else '❌ Not implemented'}

### Optimization Opportunities
{chr(10).join(f"- {sugg}" for sugg in efficiency_analysis["optimization_suggestions"]) or "✅ No optimization needed"}"""

def calculate_runtime(efficiency_analysis, build_analysis):
    base_time = efficiency_analysis["metrics"]["total_steps"] * 0.5  # 30 seconds per step
    if build_analysis["test_coverage"]: base_time += 2
    if build_analysis["linting"]: base_time += 1
    if build_analysis["type_checking"]: base_time += 1
    return round(base_time, 1)

def calculate_resource_usage(efficiency_analysis):
    if efficiency_analysis["metrics"]["total_steps"] > 10:
        return "🔴 High"
    elif efficiency_analysis["metrics"]["total_steps"] > 5:
        return "🟡 Medium"
    return "🟢 Low"

def calculate_efficiency_score(efficiency_analysis, build_analysis):
    score = 60  # Base score
    if efficiency_analysis["metrics"]["matrix_builds"]: score += 10
    if efficiency_analysis["metrics"]["caching_used"]: score += 10
    if build_analysis["linting"]: score += 10
    if build_analysis["test_coverage"]: score += 10
    return min(score, 100)

def generate_recommendations(build_analysis, efficiency_analysis):
    recommendations = []
    
    if not build_analysis["linting"]:
        recommendations.append("🔍 Add code linting (e.g., flake8, pylint) for code quality")
    if not build_analysis["test_coverage"]:
        recommendations.append("📊 Implement test coverage reporting")
    if not build_analysis["type_checking"]:
        recommendations.append("🏷️ Add type checking for better code reliability")
    if not efficiency_analysis["metrics"]["caching_used"]:
        recommendations.append("💾 Implement dependency caching to reduce build times")
        
    return chr(10).join(f"- {rec}" for rec in recommendations) or "✅ All recommended practices are implemented"

def generate_ci_best_practices(build_analysis, efficiency_analysis):
    practices = [
        "✅ Keep workflow files small and focused",
        "✅ Use specific version tags for actions",
        "✅ Implement proper error handling",
        "✅ Use secrets for sensitive data",
        "✅ Regular maintenance and updates"
    ]
    return chr(10).join(f"- {practice}" for practice in practices)

def main():
    parser = argparse.ArgumentParser(description="GitHub Actions AI")
    parser.add_argument("--query", required=True, help="Workflow requirements description")
    args = parser.parse_args()

    # Generate YAML
    print("Generating GitHub Actions YAML...")
    llm = create_azure_llm()
    prompt = generate_yaml_prompt(args.query)
    
    # Create chain using pipe operator
    chain = prompt | llm
    response = chain.invoke({"query": args.query})
    yaml_content = extract_yaml_content(response)
    print("Generated YAML content:")
    print(yaml_content)

    # Validate YAML
    print("\nValidating YAML content...")
    try:
        yaml_dict = yaml.safe_load(yaml_content)
        yaml_dict = fix_yaml_structure(yaml_dict)
        print("\nFixed YAML structure:")
        print(yaml_dict)
        
        workflow = WorkflowSchema.model_validate(yaml_dict)
        print("\nYAML content validated successfully.")
        print(f"Workflow name: {workflow.name}")
        print(f"Triggers: {list(workflow.on.keys())}")
        print(f"Jobs: {list(workflow.jobs.keys())}")
    except yaml.YAMLError as e:
        print(f"Invalid YAML format: {e}")
        return
    except Exception as e:
        print(f"Validation error: {e}")
        print("\nDebug information:")
        print(f"YAML content type: {type(yaml_dict)}")
        print(f"YAML content structure: {yaml_dict}")
        return

    # Security and efficiency analysis
    print("\nPerforming security checks...")
    security_issues = check_security_compliance(yaml_dict)
    efficiency_analysis = analyze_pipeline_efficiency(yaml_dict)
    
    # Generate report
    report_name = f"workflow-analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, report_name)
    
    report_file = generate_report(yaml_dict, security_issues, efficiency_analysis, report_path, args.query)
    print(f"\nAnalysis report generated at: {report_file}")

    # Create local workflow file with query-based filename
    local_file_path = create_local_workflow_file(yaml_content, args.query)
    print(f"\nWorkflow created successfully at {local_file_path}")

if __name__ == "__main__":
    main()