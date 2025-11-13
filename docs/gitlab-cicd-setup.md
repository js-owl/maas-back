# GitLab CI/CD Setup Guide

This guide explains how to configure GitLab CI/CD for the Manufacturing Service Backend with flexible proxy support.

## 🔧 Environment Variables Configuration

### Required GitLab CI/CD Variables

Set these in GitLab: **Settings > CI/CD > Variables**

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `LINUX_PROXY_URL` | Corporate proxy for apt packages during Docker build | `http://proxy.company.com:8080/` | No* |
| `CI_REGISTRY_USER` | GitLab Container Registry username | `gitlab-ci-token` | Yes |
| `CI_REGISTRY_PASSWORD` | GitLab Container Registry password | `$CI_JOB_TOKEN` | Yes |

*Leave empty for environments without corporate proxy

### Optional Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DOCKER_REGISTRY` | Custom Docker registry URL | `registry.company.com` | No |
| `DEPLOY_TOKEN` | Token for deployment | `glpat-xxxxxxxxxxxx` | No |

## 🚀 Pipeline Stages

### 1. Test Stage
- Runs unit and integration tests
- Generates coverage reports
- Validates code quality

### 2. Build Stage
- Builds Docker image with appropriate proxy configuration
- Pushes to GitLab Container Registry
- Handles both proxy and non-proxy environments

### 3. Deploy Stage
- Deploys to staging (automatic on develop branch)
- Deploys to production (manual on main branch)

## 🌐 Proxy Configuration Scenarios

### Scenario 1: No Corporate Proxy (Default)
```yaml
# .gitlab-ci.yml
build:
  script:
    - docker build -t $IMAGE_NAME:$IMAGE_TAG .
    # LINUX_PROXY_URL not set or empty
```

### Scenario 2: Corporate Proxy Required
```yaml
# .gitlab-ci.yml
build:
  variables:
    LINUX_PROXY_URL: "http://proxy.company.com:8080/"
  script:
    - docker build --build-arg LINUX_PROXY_URL="$LINUX_PROXY_URL" -t $IMAGE_NAME:$IMAGE_TAG .
```

### Scenario 3: Environment-Specific Proxy
```yaml
# .gitlab-ci.yml
build_staging:
  variables:
    LINUX_PROXY_URL: "http://staging-proxy:8080/"
  script:
    - docker build --build-arg LINUX_PROXY_URL="$LINUX_PROXY_URL" -t $IMAGE_NAME:staging .

build_production:
  variables:
    LINUX_PROXY_URL: "http://prod-proxy:8080/"
  script:
    - docker build --build-arg LINUX_PROXY_URL="$LINUX_PROXY_URL" -t $IMAGE_NAME:prod .
```

## 🔒 Security Considerations

### 1. Variable Protection
- Mark sensitive variables as "Protected" and "Masked"
- Use `CI_JOB_TOKEN` for registry authentication when possible

### 2. Proxy Credentials
If your proxy requires authentication:
```bash
# Set in GitLab CI/CD Variables (masked)
LINUX_PROXY_URL=http://username:password@proxy.company.com:8080/
```

### 3. Registry Access
```yaml
# Use GitLab's built-in registry authentication
before_script:
  - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
```

## 🐳 Docker Build Optimization

### Multi-stage Build (Optional Enhancement)
```dockerfile
# Build stage
FROM python:3.11-slim as builder
ARG LINUX_PROXY_URL
# ... proxy configuration ...
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
# ... rest of configuration ...
```

### Build Cache
```yaml
# .gitlab-ci.yml
build:
  script:
    - docker build --cache-from $IMAGE_NAME:latest -t $IMAGE_NAME:$IMAGE_TAG .
```

## 📊 Monitoring and Debugging

### Build Logs
The Dockerfile includes helpful logging:
```bash
# With proxy
Configuring apt proxy: http://proxy.company.com:8080/

# Without proxy  
No proxy configured - using direct internet access
```

### Common Issues

1. **Proxy Authentication Failed**
   - Check proxy URL format: `http://user:pass@proxy:port/`
   - Verify credentials in GitLab variables

2. **Build Timeout**
   - Corporate proxies can be slow
   - Consider increasing GitLab CI timeout

3. **Registry Push Failed**
   - Verify `CI_REGISTRY_USER` and `CI_REGISTRY_PASSWORD`
   - Check registry permissions

## 🔄 Branch Strategy

### Recommended Git Flow
- `main` → Production deployments (manual)
- `develop` → Staging deployments (automatic)
- `feature/*` → Test only
- `hotfix/*` → Emergency production fixes

### Pipeline Triggers
```yaml
# Only run on specific branches
only:
  - main
  - develop

# Manual production deployment
deploy_production:
  when: manual
  only:
    - main
```

## 📝 Example Complete Configuration

See `.gitlab-ci.yml.example` for a complete pipeline configuration that includes:
- Multi-environment support
- Security scanning
- Coverage reporting
- Flexible proxy handling
- Production-ready deployment

## 🆘 Troubleshooting

### Debug Commands
```bash
# Test Docker build locally
docker build --build-arg LINUX_PROXY_URL="http://your-proxy:8080/" -t test-build .

# Check proxy configuration in container
docker run --rm test-build cat /etc/apt/apt.conf.d/99proxy

# Test without proxy
docker build --build-arg LINUX_PROXY_URL="" -t test-build .
```

### Support
For issues with GitLab CI/CD configuration, check:
1. GitLab CI/CD logs
2. Docker build output
3. Network connectivity from GitLab runners
4. Proxy server accessibility
