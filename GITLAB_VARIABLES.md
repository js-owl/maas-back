# GitLab CI/CD Variables Configuration

This document lists all required GitLab CI/CD variables for the MAAS Backend API pipeline.

## Required Variables

Set these variables in GitLab Project Settings > CI/CD > Variables:

### Registry Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `NEXUS_BUILD_REGISTRY` | Registry for pulling base images | `vortex.kronshtadt.ru:8443` | No |
| `NEXUS_BUILD_USER` | Username for build registry | `maasuser` | No |
| `NEXUS_BUILD_PASSWORD` | Password for build registry | `A8rps0Hk` | **Yes** |
| `NEXUS_PUSH_REGISTRY` | Registry for pushing built images | `nexus.maas.int.kronshtadt.ru:8443` | No |
| `NEXUS_PUSH_USER` | Username for push registry | `maasuser` | No |
| `NEXUS_PUSH_PASSWORD` | Password for push registry | `A8rps0Hk` | **Yes** |

### Docker Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `DOCKER_IMAGE` | Docker image version for build stage | `docker:28.4.0` | No |

### Proxy Configuration (Optional)

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `APT_PROXY` | APT proxy URL for package installation | `http://proxy.company.com:8080` | No |
| `PIP_INDEX_URL` | PyPI registry URL (if using private registry) | `https://maasuser:password@vortex.kronshtadt.ru:8443/repository/pypi-proxy/simple/` | **Yes** |
| `PIP_TRUSTED_HOST` | PyPI registry host for SSL (if using private registry) | `vortex.kronshtadt.ru` | No |

### Deployment Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `SSH_PRIVATE_KEY` | SSH private key for production deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` | **Yes** |
| `SSH_PORT` | SSH port for production server | `22` | No |
| `SSH_HOST` | Production server hostname | `api-server.company.com` | No |
| `SSH_USER` | SSH username for production deployment | `deploy` | No |
| `REMOTE_PROJECT_PATH` | Path on production server | `/opt/maas-backend` | No |
| `TRAEFIK_HOST` | Traefik host/domain for production | `10.33.42.18` or `api.company.com` | No |

### Development Server Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `DEV_SSH_PRIVATE_KEY` | SSH private key for development server | `-----BEGIN OPENSSH PRIVATE KEY-----...` | **Yes** |
| `DEV_SSH_PORT` | SSH port for development server | `22` | No |
| `DEV_SSH_HOST` | Development server hostname | `dev-server.company.com` | No |
| `DEV_SSH_USER` | SSH username for development server | `deploy` | No |
| `DEV_REMOTE_PROJECT_PATH` | Path on development server | `/opt/maas-backend-dev` | No |
| `DEV_TRAEFIK_HOST` | Traefik host/domain for development | `dcksv-maas-dev.int.kronshtadt.ru` | No |

## Deployment Workflow (Branch-based)

### Production Deployment
- **Trigger**: Branch `main` (deploy is manual)
- **Pipeline**: `build:production` → `deploy:production`
- **Dockerfile**: `Dockerfile.prod`
- **Compose file**: `docker-compose.prod.yml`
- **Image tags**: `${PROD_PUSH_IMAGE}:${CI_COMMIT_SHA}` and `${PROD_PUSH_IMAGE}:latest`
- **Registry policy**: Build uses BUILD bases/caches; final image pushed to PUSH; deploy pulls from PUSH
- **Server**: Production server (uses `SSH_*` variables)

### Development Deployment
- **Trigger**: Branch `dev` (deploy is manual)
- **Pipeline**: `build:development` → `deploy:development`
- **Dockerfile**: `Dockerfile.dev`
- **Compose file**: `docker-compose.dev.yml`
- **Image tags**: `${DEV_BUILD_IMAGE}:${CI_COMMIT_SHA}` and `${DEV_BUILD_IMAGE}:dev-latest`
- **Registry policy**: Build and deploy use BUILD registry only
- **Server**: Development server (uses `DEV_SSH_*` variables)

### Example Commands

**Production (main branch):**
Pipeline auto-builds on push; deploy is manual from UI.

**Development (dev branch):**
Pipeline auto-builds on push; deploy is manual from UI.

## Traefik Host Configuration

The Traefik host/domain can be configured via GitLab CI/CD variables:

- **Production**: Set `TRAEFIK_HOST` variable (defaults to `10.33.42.18` if not set)
- **Development**: Set `DEV_TRAEFIK_HOST` variable (defaults to `dcksv-maas-dev.int.kronshtadt.ru` if not set)

The CI/CD pipeline will automatically replace the environment variable placeholders in the docker-compose files during deployment.

**Example:**
- Set `TRAEFIK_HOST=api.company.com` in GitLab CI/CD variables
- The production deployment will use `api.company.com` instead of the default IP address

## How to Set Variables

1. Go to your GitLab project
2. Navigate to **Settings** > **CI/CD**
3. Expand **Variables** section
4. Click **Add variable**
5. Fill in the **Key** and **Value**
6. Check **Mask variable** for sensitive values (passwords, keys)
7. Click **Add variable**

## Security Notes

- **Always mask** passwords and private keys
- Use least-privilege credentials
- Rotate credentials regularly
- Consider using GitLab's CI/CD variable types (File, Variable)

## Testing Variables

To test if variables are set correctly, you can add a debug job to your pipeline:

```yaml
debug:variables:
  stage: test
  script:
    - echo "Build registry: $NEXUS_BUILD_REGISTRY"
    - echo "Push registry: $NEXUS_PUSH_REGISTRY"
    - echo "SSH host: $SSH_HOST"
    - echo "Remote path: $REMOTE_PROJECT_PATH"
  only:
    - tags
```

## Troubleshooting

### Common Issues

1. **Authentication failures**: Check username/password combinations
2. **SSH connection issues**: Verify SSH key format and permissions
3. **Registry access denied**: Ensure credentials have proper permissions
4. **Deployment failures**: Check remote server path and permissions

### Debug Commands

```bash
# Test registry access
docker login $NEXUS_BUILD_REGISTRY -u $NEXUS_BUILD_USER

# Test SSH connection
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "echo 'SSH connection successful'"

# Check remote directory
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "ls -la $REMOTE_PROJECT_PATH"
```
