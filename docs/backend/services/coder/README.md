# FI Coder - Advanced Task Orchestrator

FI Coder is a sophisticated task orchestration system for development workflows, featuring background execution, comprehensive monitoring, advanced metrics, and extensive automation capabilities.

## 🚀 Epic Features

### Advanced Orchestration
- **Priority-based task queuing** with high/normal/low priority levels
- **Concurrent execution** with configurable worker pools
- **Pipeline support** for complex workflow orchestration
- **Task cancellation** and graceful shutdown
- **Execution fingerprinting** for reproducibility

### Comprehensive Monitoring
- **Real-time metrics collection** (execution times, success rates, queue depth)
- **Health monitoring** with component-level status checks
- **Performance alerting** with configurable thresholds
- **Structured logging** with timezone-aware timestamps and redaction
- **Metrics retention** with automatic cleanup

### Security & Reliability
- **Parameter validation** against task schemas
- **Shell injection prevention** with secure command execution
- **Path traversal protection** and working directory restrictions
- **Environment sanitization** for secure subprocess execution
- **Audit trails** with execution fingerprints

### Extensible Task Catalog
- **40+ specialized tasks** across development lifecycle
- **qwen-code integration** for AI-assisted development
- **Custom task creation** with schema validation
- **Pipeline composition** for complex workflows

## Task Catalog

### Available Tasks

#### Core Development Tasks
- `lint`: Run linting on the frontend
- `typecheck`: Run type checking on backend
- `test`: Run backend tests
- `qwen-code`: Run qwen-code with custom args

#### Specialized qwen-code Tasks

##### Code Quality & Maintenance
- `fix_lint`: Fix lint errors in specified modules
- `fix_imports`: Fix and optimize import statements, remove unused imports
- `add_type_hints`: Add comprehensive type hints to functions and variables
- `remove_dead_code`: Identify and remove unused code, functions, and variables
- `standardize_naming`: Standardize naming conventions (snake_case, camelCase, etc.)

##### Testing & Validation
- `fix_and_test`: Fix issues and run tests in modules
- `generate_unit_tests`: Generate comprehensive unit tests aiming for target coverage
- `fix_test_failures`: Analyze and fix failing tests
- `add_integration_tests`: Add integration tests for critical paths

##### Documentation
- `update_docstrings`: Update and improve function docstrings (Google/NumPy style)
- `generate_api_docs`: Generate API documentation from code (Markdown/HTML)
- `add_code_comments`: Add explanatory comments to complex code sections

##### Dependencies & Security
- `audit_dependencies`: Audit dependencies for security vulnerabilities
- `update_dependencies`: Update dependencies to latest compatible versions
- `check_security_issues`: Scan code for security vulnerabilities by severity level

##### Performance & Optimization
- `optimize_performance`: Identify and fix performance bottlenecks
- `reduce_bundle_size`: Optimize frontend bundle size to target size
- `memory_leak_detection`: Detect and fix memory leaks

##### CI/CD & Deployment
- `setup_ci_pipeline`: Set up CI/CD pipeline configuration (GitHub/GitLab)
- `docker_optimization`: Optimize Docker configuration for production
- `environment_config`: Review and optimize environment configuration

##### Code Analysis & Quality Assurance
- `static_analysis`: Run comprehensive static analysis (pylint, flake8, mypy)
- `complexity_analysis`: Analyze code complexity and suggest simplifications
- `duplicate_code_detection`: Find and eliminate code duplication

##### Database & Data Operations
- `database_migration`: Generate and apply database migrations
- `data_validation`: Validate data integrity and consistency

##### API & Integration
- `api_testing`: Generate and run API integration tests
- `contract_testing`: Test API contracts between services

##### DevOps & Infrastructure
- `infrastructure_as_code`: Generate infrastructure as code templates
- `monitoring_setup`: Set up monitoring and alerting

##### AI/ML Operations
- `model_validation`: Validate ML model performance and accuracy
- `feature_engineering`: Generate feature engineering code

### Specialized qwen-code Tasks

These tasks use qwen-code as a deterministic engine for specific intents:

- **fix_lint**: Corrects linting errors in targeted modules
- **refactor**: Applies scoped refactoring operations
- **fix_and_test**: Automated fixes followed by test validation
- **analyze_code**: Code analysis in dry-run mode
- **pipeline_fix_lint_test**: Chained fix → test workflow

## API Usage

### Create Task

```python
POST /internal/fi_coder/tasks
{
  "name": "fix_lint",
  "parameters": {
    "repo_root_path": "/path/to/repo",
    "modules": "admin components"
  }
}
```

### Create Pipeline

```python
POST /internal/fi_coder/pipelines
[
  {
    "name": "fix_lint",
    "parameters": {"modules": "auth"}
  },
  {
    "name": "test",
    "parameters": {}
  }
]
```

Pipelines execute tasks in parallel. For sequential dependencies, submit tasks individually and monitor completion.

### Get Task Status

```python
GET /internal/fi_coder/tasks/{task_id}
```

### List Tasks

```python
GET /internal/fi_coder/tasks?status=running
```

### Get Logs

```python
GET /internal/fi_coder/tasks/{task_id}/logs?tail=50
```

### Cancel Task

```python
DELETE /internal/fi_coder/tasks/{task_id}
```

### Get System Status

```python
GET /internal/fi_coder/status
```

### Get Metrics

```python
GET /internal/fi_coder/metrics
```

Returns comprehensive metrics including:
- Orchestrator performance (tasks/sec, success rate, queue depth)
- System-wide counters and gauges
- Historical metric series

### Health Check

```python
GET /internal/fi_coder/health
```

Returns system health status with component-level checks:
- Orchestrator health (workers, queue, success rate)
- Overall system status (healthy/degraded/unhealthy)

### Get Alerts

```python
GET /internal/fi_coder/alerts
```

Returns active performance alerts and warnings.

### Launch Task

```bash
# Basic tasks
python -m fi_coder.cli.main launch lint
python -m fi_coder.cli.main launch test

# Specialized qwen-code tasks
python -m fi_coder.cli.main launch fix_lint --modules "admin components"
python -m fi_coder.cli.main launch refactor --scope "hooks" --modules "dashboard"
python -m fi_coder.cli.main launch fix_and_test --modules "auth bryntum"
python -m fi_coder.cli.main launch analyze_code --modules "medical"
python -m fi_coder.cli.main launch pipeline_fix_lint_test --modules "all"
```

### List Tasks

```bash
python -m fi_coder.cli.main list --status running
```

### Get Status

```bash
python -m fi_coder.cli.main status <task_id>
```

### Get Logs

```bash
python -m fi_coder.cli.main logs <task_id> --tail 20
```

### Cancel Task

```bash
python -m fi_coder.cli.main cancel <task_id>
```

## Adding New Tasks

1. Add to `TASK_CATALOG` in `config/policies.py`
2. Update `allowed_commands` in `SECURITY_POLICY`
3. Test the command template

## Daemon Mode

To run as a daemon:

```python
from fi_coder.service import FiCoderService

service = FiCoderService()
# Service runs in background threads
```

## Security

- Commands are restricted to allowlist
- Parameters validated for injection
- Environment sanitized
- Logs redacted for secrets