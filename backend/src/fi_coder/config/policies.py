from __future__ import annotations

from typing import Dict, List

# Required parameters for hardening
REPO_ROOT_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence"
FI_CODER_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence/backend/src/fi_coder"
QWEN_CODE_BINARY = "qwen-code"

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class TaskSchema(BaseModel):
    name: str
    description: str
    purpose: str
    parameters_schema: Dict[str, Any]
    scope_rules: Optional[Dict[str, Any]] = None

# Rebuild for forward references
TaskSchema.model_rebuild()

# Task catalog with schemas
TASK_CATALOG: Dict[str, TaskSchema] = {
    "lint": TaskSchema(
        name="lint",
        description="Run linting on the frontend",
        purpose="Code quality check",
        parameters_schema={"repo_root_path": {"type": "string", "required": True}},
    ),
    "typecheck": TaskSchema(
        name="typecheck",
        description="Run type checking on backend",
        purpose="Type safety validation",
        parameters_schema={"repo_root_path": {"type": "string", "required": True}},
    ),
    "test": TaskSchema(
        name="test",
        description="Run backend tests",
        purpose="Unit and integration testing",
        parameters_schema={"repo_root_path": {"type": "string", "required": True}},
    ),
    "qwen-code": TaskSchema(
        name="qwen-code",
        description="Run qwen-code with custom args",
        purpose="General AI-assisted development",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "args": {"type": "string", "required": True}
        },
        scope_rules={"allow_custom_args": False},  # No custom args for security
    ),
    "fix_lint": TaskSchema(
        name="fix_lint",
        description="Correct linting errors in targeted modules",
        purpose="Automated lint error fixing",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
        scope_rules={"allowed_modules": ["admin", "auth", "dashboard", "medical", "components"]},
    ),
    "refactor": TaskSchema(
        name="refactor",
        description="Apply scoped refactoring operations",
        purpose="Code refactoring assistance",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "scope": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
        scope_rules={"allowed_scopes": ["hooks", "components", "utils"]},
    ),
    "fix_and_test": TaskSchema(
        name="fix_and_test",
        description="Fix issues and run tests in modules",
        purpose="Combined fixing and testing",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "analyze_code": TaskSchema(
        name="analyze_code",
        description="Analyze code without changes",
        purpose="Code analysis",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "pipeline_fix_lint_test": TaskSchema(
        name="pipeline_fix_lint_test",
        description="Fix lint errors then run tests",
        purpose="Chained workflow",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    # Code Quality & Maintenance
    "fix_imports": TaskSchema(
        name="fix_imports",
        description="Fix and optimize import statements",
        purpose="Clean up imports and remove unused ones",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "add_type_hints": TaskSchema(
        name="add_type_hints",
        description="Add missing type hints to functions and variables",
        purpose="Improve code type safety",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "remove_dead_code": TaskSchema(
        name="remove_dead_code",
        description="Identify and remove unused code",
        purpose="Clean up codebase",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "standardize_naming": TaskSchema(
        name="standardize_naming",
        description="Standardize variable and function naming conventions",
        purpose="Improve code consistency",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True},
            "convention": {"type": "string", "default": "snake_case"}
        },
    ),
    # Testing & Validation
    "generate_unit_tests": TaskSchema(
        name="generate_unit_tests",
        description="Generate comprehensive unit tests for functions",
        purpose="Improve test coverage",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True},
            "coverage_target": {"type": "number", "default": 80}
        },
    ),
    "fix_test_failures": TaskSchema(
        name="fix_test_failures",
        description="Analyze and fix failing tests",
        purpose="Ensure test suite passes",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "test_pattern": {"type": "string", "default": "*"}
        },
    ),
    "add_integration_tests": TaskSchema(
        name="add_integration_tests",
        description="Add integration tests for critical paths",
        purpose="Test component interactions",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    # Documentation
    "update_docstrings": TaskSchema(
        name="update_docstrings",
        description="Update and improve function docstrings",
        purpose="Better code documentation",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True},
            "style": {"type": "string", "default": "google"}
        },
    ),
    "generate_api_docs": TaskSchema(
        name="generate_api_docs",
        description="Generate API documentation from code",
        purpose="Create comprehensive API docs",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "output_format": {"type": "string", "default": "markdown"}
        },
    ),
    "add_code_comments": TaskSchema(
        name="add_code_comments",
        description="Add explanatory comments to complex code",
        purpose="Improve code readability",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    # Dependencies & Security
    "audit_dependencies": TaskSchema(
        name="audit_dependencies",
        description="Audit dependencies for security vulnerabilities",
        purpose="Identify security risks",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True}
        },
    ),
    "update_dependencies": TaskSchema(
        name="update_dependencies",
        description="Update dependencies to latest compatible versions",
        purpose="Keep dependencies current",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "allow_major": {"type": "boolean", "default": False}
        },
    ),
    "check_security_issues": TaskSchema(
        name="check_security_issues",
        description="Scan code for security vulnerabilities",
        purpose="Identify security issues",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "severity_level": {"type": "string", "default": "medium"}
        },
    ),
    # Performance & Optimization
    "optimize_performance": TaskSchema(
        name="optimize_performance",
        description="Identify and fix performance bottlenecks",
        purpose="Improve application performance",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    "reduce_bundle_size": TaskSchema(
        name="reduce_bundle_size",
        description="Optimize bundle size for frontend",
        purpose="Improve load times",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "target_size": {"type": "string", "default": "500KB"}
        },
    ),
    "memory_leak_detection": TaskSchema(
        name="memory_leak_detection",
        description="Detect and fix memory leaks",
        purpose="Prevent memory issues",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True}
        },
    ),
    # CI/CD & Deployment
    "setup_ci_pipeline": TaskSchema(
        name="setup_ci_pipeline",
        description="Set up CI/CD pipeline configuration",
        purpose="Automate deployment process",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "platform": {"type": "string", "default": "github"}
        },
    ),
    "docker_optimization": TaskSchema(
        name="docker_optimization",
        description="Optimize Docker configuration for production",
        purpose="Improve container performance",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True}
        },
    ),
    "environment_config": TaskSchema(
        name="environment_config",
        description="Review and optimize environment configuration",
        purpose="Ensure proper config management",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True}
        },
    ),
    # Code Analysis & Quality Assurance
    "static_analysis": TaskSchema(
        name="static_analysis",
        description="Run comprehensive static analysis on codebase",
        purpose="Identify code quality issues and potential bugs",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True},
            "tools": {"type": "string", "default": "pylint,flake8,mypy"}
        },
    ),
    "complexity_analysis": TaskSchema(
        name="complexity_analysis",
        description="Analyze code complexity and suggest simplifications",
        purpose="Improve code maintainability",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "modules": {"type": "string", "required": True},
            "max_complexity": {"type": "number", "default": 10}
        },
    ),
    "duplicate_code_detection": TaskSchema(
        name="duplicate_code_detection",
        description="Find and eliminate code duplication",
        purpose="Reduce maintenance burden",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "min_lines": {"type": "number", "default": 6}
        },
    ),
    # Database & Data Operations
    "database_migration": TaskSchema(
        name="database_migration",
        description="Generate and apply database migrations",
        purpose="Keep database schema in sync",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "migration_type": {"type": "string", "default": "auto"}
        },
    ),
    "data_validation": TaskSchema(
        name="data_validation",
        description="Validate data integrity and consistency",
        purpose="Ensure data quality",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "data_source": {"type": "string", "required": True}
        },
    ),
    # API & Integration
    "api_testing": TaskSchema(
        name="api_testing",
        description="Generate and run API integration tests",
        purpose="Validate API functionality",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "api_spec": {"type": "string", "required": True}
        },
    ),
    "contract_testing": TaskSchema(
        name="contract_testing",
        description="Test API contracts between services",
        purpose="Ensure service compatibility",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "service_a": {"type": "string", "required": True},
            "service_b": {"type": "string", "required": True}
        },
    ),
    # DevOps & Infrastructure
    "infrastructure_as_code": TaskSchema(
        name="infrastructure_as_code",
        description="Generate infrastructure as code templates",
        purpose="Automate infrastructure provisioning",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "platform": {"type": "string", "default": "terraform"}
        },
    ),
    "monitoring_setup": TaskSchema(
        name="monitoring_setup",
        description="Set up monitoring and alerting",
        purpose="Improve system observability",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "monitoring_tool": {"type": "string", "default": "prometheus"}
        },
    ),
    # AI/ML Operations
    "model_validation": TaskSchema(
        name="model_validation",
        description="Validate ML model performance and accuracy",
        purpose="Ensure model quality",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "model_path": {"type": "string", "required": True},
            "validation_dataset": {"type": "string", "required": True}
        },
    ),
    "feature_engineering": TaskSchema(
        name="feature_engineering",
        description="Generate feature engineering code",
        purpose="Improve ML model inputs",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "data_schema": {"type": "string", "required": True}
        },
    ),
}

# Legacy command templates (for backward compatibility)
COMMAND_TEMPLATES: Dict[str, str] = {
    "lint": "pnpm lint --filter aurity",
    "typecheck": "pyright backend/",
    "test": "python -m pytest tests/ -v",
    "qwen-code": "qwen-code {args}",
    "fix_lint": "node /opt/homebrew/lib/node_modules/@qwen-code/qwen-code/cli.js \"fix lint errors in {modules}\"",
    "refactor": "qwen-code \"refactor {scope} in {modules}\"",
    "fix_and_test": "qwen-code \"fix issues in {modules} and run tests\"",
    "analyze_code": "qwen-code \"analyze code in {modules} without changes\"",
    "pipeline_fix_lint_test": "qwen-code \"fix lint errors, then run tests in {modules}\"",
    # Code Quality & Maintenance
    "fix_imports": "qwen-code \"fix and optimize import statements in {modules}, remove unused imports\"",
    "add_type_hints": "qwen-code \"add comprehensive type hints to functions and variables in {modules}\"",
    "remove_dead_code": "qwen-code \"identify and remove unused code, functions, and variables in {modules}\"",
    "standardize_naming": "cd {repo_root_path} && qwen-code \"standardize naming conventions to {convention} in {modules}\"",
    # Testing & Validation
    "generate_unit_tests": "cd {repo_root_path} && qwen-code \"generate comprehensive unit tests for {modules} aiming for {coverage_target}% coverage\"",
    "fix_test_failures": "cd {repo_root_path} && qwen-code \"analyze and fix failing tests matching pattern {test_pattern}\"",
    "add_integration_tests": "cd {repo_root_path} && qwen-code \"add integration tests for critical paths in {modules}\"",
    # Documentation
    "update_docstrings": "cd {repo_root_path} && qwen-code \"update and improve docstrings in {modules} using {style} style\"",
    "generate_api_docs": "cd {repo_root_path} && qwen-code \"generate comprehensive API documentation in {output_format} format\"",
    "add_code_comments": "cd {repo_root_path} && qwen-code \"add explanatory comments to complex code sections in {modules}\"",
    # Dependencies & Security
    "audit_dependencies": "cd {repo_root_path} && qwen-code \"audit all dependencies for security vulnerabilities and outdated packages\"",
    "update_dependencies": "cd {repo_root_path} && qwen-code \"update dependencies to latest compatible versions, allow major updates: {allow_major}\"",
    "check_security_issues": "cd {repo_root_path} && qwen-code \"scan codebase for security vulnerabilities at {severity_level} level and above\"",
    # Performance & Optimization
    "optimize_performance": "cd {repo_root_path} && qwen-code \"identify and fix performance bottlenecks in {modules}\"",
    "reduce_bundle_size": "cd {repo_root_path} && qwen-code \"optimize frontend bundle size to target {target_size}\"",
    "memory_leak_detection": "cd {repo_root_path} && qwen-code \"detect and fix memory leaks in {modules}\"",
    # CI/CD & Deployment
    "setup_ci_pipeline": "cd {repo_root_path} && qwen-code \"set up CI/CD pipeline configuration for {platform} platform\"",
    "docker_optimization": "cd {repo_root_path} && qwen-code \"optimize Docker configuration for production deployment\"",
    "environment_config": "cd {repo_root_path} && qwen-code \"review and optimize environment configuration management\"",
    # Code Analysis & Quality Assurance
    "static_analysis": "cd {repo_root_path} && qwen-code \"run comprehensive static analysis on {modules} using tools: {tools}\"",
    "complexity_analysis": "cd {repo_root_path} && qwen-code \"analyze code complexity in {modules} and suggest simplifications for functions with complexity > {max_complexity}\"",
    "duplicate_code_detection": "cd {repo_root_path} && qwen-code \"find and eliminate code duplication with minimum {min_lines} lines\"",
    # Database & Data Operations
    "database_migration": "cd {repo_root_path} && qwen-code \"generate and apply database migrations of type {migration_type}\"",
    "data_validation": "cd {repo_root_path} && qwen-code \"validate data integrity and consistency for {data_source}\"",
    # API & Integration
    "api_testing": "cd {repo_root_path} && qwen-code \"generate and run API integration tests for {api_spec}\"",
    "contract_testing": "cd {repo_root_path} && qwen-code \"test API contracts between {service_a} and {service_b}\"",
    # DevOps & Infrastructure
    "infrastructure_as_code": "cd {repo_root_path} && qwen-code \"generate infrastructure as code templates for {platform} platform\"",
    "monitoring_setup": "cd {repo_root_path} && qwen-code \"set up monitoring and alerting using {monitoring_tool}\"",
    # AI/ML Operations
    "model_validation": "cd {repo_root_path} && qwen-code \"validate ML model at {model_path} using {validation_dataset}\"",
    "feature_engineering": "cd {repo_root_path} && qwen-code \"generate feature engineering code for {data_schema}\"",
}

MODEL_POLICY = {
    "model": "qwen-code-default",
    "temperature": 0.0,  # Deterministic
    "max_tokens": 4096,
    "seed": 42,  # For reproducibility
}
WORKSPACE_POLICY = {
    "fingerprint_git": True,
    "fingerprint_files": True,
    "exclude_patterns": [".git", "__pycache__", "node_modules"],
}
SCOPE_POLICY = {
    "allowed_paths": [REPO_ROOT_PATH],
    "forbid_absolute_outside_repo": True,
    "forbid_traversal": True,
    "forbid_directories": ["storage", "logs", "data"],
}
CLI_ENTRY_POLICY = {
    "canonical_entrypoint": "python -m fi_coder.cli.main",
    "help_without_imports": True,
}
SECURITY_POLICY = {
    "allowed_commands": list(TASK_CATALOG.keys()),
    "working_directory_whitelist": [REPO_ROOT_PATH],
    "environment_sanitization": True,
    "allowlist_executables": ["qwen-code", "pnpm", "python", "pytest", "pyright"],
}

# Execution policy
EXECUTION_POLICY = {
    "max_concurrent_tasks": 4,
    "default_timeout_seconds": 300,  # 5 minutes
    "pipeline_timeout_seconds": 1800,  # 30 minutes
    "retry_attempts": 0,  # No retries by default
}

# Logging policy
LOGGING_POLICY = {
    "log_directory": "logs/fi_coder",
    "max_log_size_mb": 10,
    "retention_days": 7,
    "redact_patterns": [
        r"sk-[a-zA-Z0-9]{20,}",  # API keys
        r"Bearer\s+[a-zA-Z0-9]{40,}",  # JWT
        r"(?i)(password|secret|key)\s*[:=]\s*\S+",  # Secrets
    ],
}

# Storage policy
STORAGE_POLICY = {
    "state_file": "storage/fi_coder/tasks.json",
    "backup_on_change": True,
}

# API policy
API_POLICY = {
    "base_path": "/internal/fi_coder",
    "require_auth": True,
}

# CLI policy
CLI_POLICY = {
    "module_name": "fi_coder.cli.main",
}

# Security policy
SECURITY_POLICY = {
    "allowed_commands": list(TASK_CATALOG.keys()),
    "working_directory_whitelist": [REPO_ROOT_PATH],
    "environment_sanitization": True,
    "allowlist_executables": ["qwen-code", "pnpm", "python", "pytest", "pyright"],
}