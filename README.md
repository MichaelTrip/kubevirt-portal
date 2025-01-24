# KubeVirt Portal

A web-based management interface for KubeVirt virtual machines in Kubernetes clusters. Built with Python and Flask.

## Overview

KubeVirt Portal provides a user-friendly web interface to manage virtual machines running on Kubernetes using KubeVirt. This tool simplifies the process of creating, monitoring, and managing virtual machines in your Kubernetes environment.

## Features

- Web-based VM management interface
- Virtual machine lifecycle management (create, start, stop, delete)
- VM resource monitoring
- Integration with Kubernetes native features
- User-friendly dashboard

## Prerequisites

- Kubernetes cluster (v1.16+)
- KubeVirt installed on the cluster
- Modern web browser
- kubectl CLI tool

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MichaelTrip/kubevirt-portal.git
cd kubevirt-portal
```

2. Deploy to your Kubernetes cluster:

First, encode your secrets:
```bash
# Replace these with your actual values
echo -n "https://github.com/yourusername/your-vm-configs.git" | base64
echo -n "your-github-username" | base64
echo -n "your-github-token" | base64
echo -n "your-secret-key" | base64
```

Update the base64 encoded values in `kubernetes/secret.yaml` with your actual values.

Then apply the Kubernetes manifests:
```bash
# Create namespace (optional)
kubectl create namespace kubevirt-portal

# Apply manifests
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

# Verify deployment
kubectl get pods -l app=kubevirt-portal
kubectl get svc kubevirt-portal
```

To access the application:

1. For testing, you can use port-forwarding:
```bash
kubectl port-forward svc/kubevirt-portal 8080:80
```
Then access the portal at `http://localhost:8080`

2. For production, set up an Ingress or LoadBalancer service according to your cluster configuration.

## Usage

Access the portal through your web browser:

1. Start the application:
```bash
docker run -p 5000:5000 kubevirt-portal
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Use the web interface to:
   - View list of VMs
   - Create new VMs
   - Edit existing VM configurations
   - Delete VMs

## Development

### Setting up the Development Environment

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:

The following environment variables are required and should be set in your `.env` file or environment:

Required variables:
- `GIT_REPO_URL`: URL of the Git repository where VM configurations will be stored
- `GIT_USERNAME`: Username for Git authentication
- `GIT_TOKEN`: Authentication token for Git access

Optional variables:
- `SECRET_KEY`: Flask secret key (defaults to 'dev-secret-key')
- `YAML_SUBDIRECTORY`: Directory within the Git repo where VM YAML files are stored (defaults to 'vms/')

Example `.env` file:
```bash
FLASK_APP=run.py
FLASK_ENV=development
GIT_REPO_URL=https://github.com/yourusername/your-vm-configs.git
GIT_USERNAME=yourusername
GIT_TOKEN=your-git-personal-access-token
SECRET_KEY=your-secret-key
YAML_SUBDIRECTORY=vms/
```

4. Start the development server:
```bash
flask run
```

### Building the Docker Image

1. Build the image:
```bash
docker build -t kubevirt-portal .
```

2. Run the container:
```bash
docker run -p 5000:5000 kubevirt-portal
```

### Development Guidelines

1. Code Style
   - Follow PEP 8 guidelines
   - Use meaningful variable and function names
   - Add docstrings to functions and classes

2. Testing
   - Write unit tests for new features
   - Ensure all tests pass before submitting PR
   - Run tests with: `python -m pytest`

3. Git Workflow
   - Create feature branches from main
   - Keep commits atomic and well-described
   - Rebase on main before submitting PR

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you have any questions or need help with KubeVirt Portal, please open an issue in the GitHub repository.
