<div align="center">

# 🚀 KubeVirt Portal

### Git-Backed Virtual Machine Management for KubeVirt with Web Terminal

[![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-v2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![Jinja2](https://img.shields.io/badge/jinja2-v3.0.0+-red.svg)](https://jinja.palletsprojects.com/)
[![GitPython](https://img.shields.io/badge/gitpython-v3.1.40-orange.svg)](https://gitpython.readthedocs.io/)

<p align="center">
  <strong>A sophisticated web portal for managing KubeVirt VMs with Git-based configuration management</strong>
</p>

[Features](#-features) •
[Installation](#-installation) •
[Configuration](#-configuration) •
[Development](#-development)

</div>

## 🌟 Overview

KubeVirt Portal is a modern web application that combines KubeVirt with Git-based configuration management. It provides a user-friendly interface for creating and managing virtual machines in Kubernetes clusters while maintaining all configurations in version control.

## ✨ Features

### 🔧 Core Functionality
- **Git Integration**: Version-controlled VM configurations
- **Template System**: Jinja2-powered YAML generation
- **Resource Management**: CPU, memory, and storage allocation
- **Network Configuration**: Service ports and MetalLB integration
- **Web Terminal**: Built-in SSH access to VMs
- **Power Management**: Start/stop VMs directly from the UI

### 💻 VM Configuration
- CPU allocation (1-16 cores)
- Memory sizing (1-64 GB)
- Storage configuration
  - Dynamic size allocation
  - Storage class selection
  - Default Longhorn RWX support
- Network settings
  - Custom hostnames
  - Service port mapping
  - Protocol selection (TCP/UDP)
  - Web-based SSH terminal
- Power management
  - Start/stop controls
  - Status monitoring
- Cloud-init integration

### 🛠 Technical Features
- **Security**
  - Git authentication
  - Environment-based configuration
  - Secret management
- **Deployment Options**
  - Docker container
  - Kubernetes deployment
  - Resource limits and requests
- **Development Tools**
  - Debug mode
  - Comprehensive logging
  - YAML preview functionality

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster with KubeVirt
- Git repository for configurations
- kubectl CLI tool

### Kubernetes Deployment

1. Create secrets:
```bash
# Base64 encode your values
echo -n "https://github.com/yourusername/vm-configs.git" | base64
echo -n "your-username" | base64
echo -n "your-token" | base64
```

2. Deploy the application:
```bash
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

3. Access the portal:
```bash
kubectl port-forward svc/kubevirt-portal 5000:80
```

### Local Development

1. Set up environment:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
export GIT_REPO_URL="https://github.com/your/repo.git"
export GIT_USERNAME="username"
export GIT_TOKEN="token"
export YAML_SUBDIRECTORY="vms/"
```

3. Run the application:
```bash
flask run --debug
```

## 🔧 Configuration

### Environment Variables

Required:
- `GIT_REPO_URL`: VM configuration repository
- `GIT_USERNAME`: Git authentication username
- `GIT_TOKEN`: Git authentication token

Optional:
- `SECRET_KEY`: Flask secret key (default: "dev-secret-key")
- `YAML_SUBDIRECTORY`: VM configuration directory (default: "virtualmachines/")
- `GIT_CLONE_DIR`: Directory for Git repository clones (default: "/app/storage/clones")
- `EXTERNAL_DNS_ENABLED`: Enable ExternalDNS integration (default: "false")
- `METALLB_ENABLED`: Enable MetalLB integration (default: "false")
- `FLASK_DEBUG`: Enable debug mode (default: "false")

### Resource Requirements

Default limits:
- Memory: 512Mi
- CPU: 500m
- Storage: Based on PVC configuration

## 🏗 Architecture

### Components
- Flask web application
- GitPython for repository management
- Jinja2 templating engine
- WTForms for form handling

### Key Files
- `app/routes.py`: Web endpoints
- `app/utils.py`: Git operations
- `app/forms.py`: Form definitions
- `kubernetes/*.yaml`: Deployment manifests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 💬 Support

For support:
1. Check existing GitHub issues
2. Create a new issue with:
   - Clear description
   - Steps to reproduce
   - Expected behavior
