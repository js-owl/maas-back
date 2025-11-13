# GitLab CI/CD Setup for MAAS Backend API

This repository includes a complete GitLab CI/CD pipeline configuration for automated testing, building, and deploying the MAAS Backend API.

## 🚀 Quick Start

1. **Set up GitLab Variables** (Project Settings > CI/CD > Variables):
   See [GITLAB_VARIABLES.md](GITLAB_VARIABLES.md) for complete list of required variables.
   
   **Essential variables:**
   ```
   NEXUS_BUILD_REGISTRY - Registry for pulling base images
   NEXUS_BUILD_USER - Build registry username
   NEXUS_BUILD_PASSWORD - Build registry password (masked)
   NEXUS_PUSH_REGISTRY - Registry for pushing built images
   NEXUS_PUSH_USER - Push registry username
   NEXUS_PUSH_PASSWORD - Push registry password (masked)
   SSH_PRIVATE_KEY - SSH key for deployment (masked)
   SSH_HOST - Remote server hostname
   SSH_USER - SSH username
   REMOTE_PROJECT_PATH - Remote server path
   ```

2. **Push to GitLab** - The pipeline will automatically run on:
   - Merge requests (tests only)
   - Git tags (full build and deployment)

## 📁 File Structure

```
├── .gitlab-ci.yml              # Main CI/CD pipeline configuration
├── Dockerfile.prod             # Multistage production Dockerfile
├── Dockerfile.deploy           # Deploy tools image
├── docker-compose.yml          # Development deployment
├── docker-compose.production.yml # Production deployment with Traefik
├── docker-compose.development.yml # Development environment
├── .env.production             # Production environment variables
├── .env.development            # Development environment variables
├── GITLAB_VARIABLES.md         # Required GitLab CI/CD variables
├── CI-CD-README.md             # This documentation
└── scripts/
    └── deploy.sh               # Manual deployment script (legacy)
```

## 🔄 Current Pipeline Stages

### 1. Build Stage
- **Multistage Docker Build**: Creates optimized production image
- **Registry Push**: Pushes to private Docker registry
- **Caching**: Uses GitLab cache and Docker layer caching

### 2. Deploy Stage
- **SSH Deployment**: Automated deployment to remote server using `docker-compose.production.yml`
- **Traefik Integration**: Production deployment with reverse proxy and SSL
- **Health Verification**: Ensures application is running correctly
- **Rollback Support**: Easy rollback to previous version

## 🐳 Docker Configuration

### Local Development
```bash
# Start development environment
docker-compose up

# Or explicitly use development configuration
docker-compose -f docker-compose.development.yml --env-file .env.development up

# Build production image locally
docker build -f Dockerfile.prod -t maas-backend:local .

# Test production image
docker run -p 8000:8000 maas-backend:local
```

### Production Deployment
The production deployment is fully automated via GitLab CI/CD:

```bash
# Create and push a git tag to trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

The pipeline will:
1. Build optimized production image
2. Push to private registry
3. Deploy to remote server via SSH using `docker-compose.production.yml`
4. Verify deployment health and Traefik integration

## 🚀 Future Enhancements

### Testing & Quality
- **Unit Tests**: Automated pytest execution with coverage reporting
- **Integration Tests**: End-to-end API testing with real server
- **Code Quality**: Flake8, Black, isort, mypy checks
- **Performance Testing**: Load testing with Locust

### Security Scanning
- **Trivy Docker Image Scanning**: Container vulnerability scanning
- **Bandit Python Security**: Code security analysis
- **Dependency Scanning**: Package vulnerability checks
- **SAST/DAST Tools**: Static and dynamic application security testing

### Monitoring & Observability
- **Prometheus Metrics**: Application metrics collection
- **Grafana Dashboards**: Performance and health monitoring
- **Log Aggregation**: Centralized logging with ELK stack
- **APM Tools**: Application performance monitoring

### Advanced Deployment Options
- **Kubernetes Deployment**: K8s manifests and Helm charts
- **Blue-Green Deployment**: Zero-downtime deployments
- **Canary Releases**: Gradual rollout strategy
- **Multi-Environment**: Staging, production, and feature environments

### Infrastructure as Code
- **Terraform**: Infrastructure provisioning
- **Ansible**: Configuration management
- **GitOps**: Git-based infrastructure management

### Quality Gates
- **SonarQube**: Code quality and security analysis
- **Compliance Scanning**: Security and compliance checks

## 🔧 Current Configuration

### GitLab CI/CD Variables
See [GITLAB_VARIABLES.md](GITLAB_VARIABLES.md) for complete variable configuration.

### Docker Configuration
- **Production**: Uses `Dockerfile.prod` with multistage build
- **Development**: Uses `Dockerfile.local` with hot reload
- **Deploy Tools**: Uses `Dockerfile.deploy` for CI/CD deployment

### Deployment Configuration
- **Method**: SSH-based deployment to remote server
- **Compose File**: Uses `docker-compose.production.yml` with Traefik integration
- **Health Check**: HTTP endpoint verification via Traefik
- **Rollback**: Manual via `docker compose -f docker-compose.production.yml down/up`

## 🚨 Current Security Features

- **Code Security**: Bandit scans Python code for security issues
- **Dependency Management**: Secure package installation with private registries
- **Non-root User**: Container runs as non-root user (configurable)
- **Health Checks**: Built-in application health monitoring

## 📈 Current Performance Features

- **Multistage Build**: Optimized Docker images with minimal size
- **Caching**: GitLab cache and Docker layer caching for faster builds
- **Health Checks**: Application health verification
- **Resource Optimization**: Minimal runtime dependencies

## 🔍 Troubleshooting

### Common Issues

1. **GitLab CI/CD Variables**
   - Verify all required variables are set
   - Check masked variables are properly configured
   - Test registry access manually

2. **Pipeline Failures**
   - Check GitLab CI/CD logs
   - Verify SSH key format and permissions
   - Test SSH connection manually

3. **Deployment Issues**
   ```bash
   # Check container logs on remote server
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.production.yml logs"
   
   # Check container status
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.production.yml ps"
   
   # Check Traefik routing
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.production.yml logs backend"
   ```

### Health Checks
```bash
# API health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/version
```

## 📝 Best Practices

1. **Branch Strategy**
   - `main`: Production-ready code
   - `develop`: Integration branch
   - `feature/*`: Feature development

2. **Versioning**
   - Use semantic versioning for tags
   - Tag releases for production deployments

3. **Security**
   - Keep dependencies updated
   - Review security scan results
   - Use least privilege for deployments

4. **Monitoring**
   - Set up alerts for critical metrics
   - Monitor error rates and response times
   - Regular log analysis

## 🤝 Contributing

1. Create feature branch from `develop`
2. Make changes and test locally
3. Create merge request
4. Pipeline will run automatically
5. Review and merge after approval

## 📞 Support

For issues with the CI/CD pipeline:
1. Check GitLab CI/CD logs
2. Review this documentation
3. Test locally with Docker Compose
4. Contact DevOps team for infrastructure issues
