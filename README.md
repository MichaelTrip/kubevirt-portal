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
```bash
# Installation commands will be added here
```

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
```bash
export FLASK_APP=run.py
export FLASK_ENV=development
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
