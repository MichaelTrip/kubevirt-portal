# KubeVirt Portal - Local Development Setup

## Prerequisites

- Python 3.9 or higher
- Git
- A Kubernetes cluster with KubeVirt installed (optional for testing templates)
- A Git repository for storing VM configurations

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/MichaelTrip/kubevirt-portal.git
cd kubevirt-portal
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env  # If example exists, or create new:
nano .env
```

Add the following configuration:

```env
# Required: Git Configuration
GIT_REPO_URL=https://github.com/your-username/your-vm-configs-repo.git
GIT_USERNAME=your-github-username
GIT_TOKEN=your-personal-access-token

# Optional: Directory Configuration
YAML_SUBDIRECTORY=virtualmachines/
GIT_CLONE_DIR=/tmp/kubevirt-portal/clones

# Optional: Feature Flags
EXTERNAL_DNS_ENABLED=false
METALLB_ENABLED=false
CLUSTER_VMS_ENABLED=false
DEBUG=true

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
WTF_CSRF_ENABLED=false
```

### 5. Create Git Configuration Repository

If you don't have a Git repository for VM configurations yet:

```bash
# Create new repository
mkdir vm-configs
cd vm-configs
git init
mkdir virtualmachines
touch virtualmachines/.gitkeep
git add .
git commit -m "Initial commit"

# Push to your Git hosting service (GitHub, GitLab, etc.)
git remote add origin https://github.com/your-username/vm-configs.git
git push -u origin main
```

### 6. Run the Application

```bash
# Make sure virtual environment is activated
python run.py
```

The application will start on `http://127.0.0.1:5000`

## Development Workflow

### Project Structure

```
kubevirt-portal/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── routes.py                # API routes
│   ├── forms.py                 # WTForms definitions
│   ├── utils.py                 # Utility functions (NEW - refactored)
│   ├── k8s_utils.py            # Kubernetes utilities
│   ├── constants.py            # Application constants (NEW)
│   ├── schemas.py              # Pydantic validation schemas (NEW)
│   ├── template_manager.py    # Template management (NEW)
│   ├── git_manager.py          # Git operations (NEW)
│   └── templates/
│       ├── base/               # Base templates (NEW)
│       │   ├── vm-base.yaml.j2
│       │   └── service-base.yaml.j2
│       ├── profiles/           # Template profiles (NEW)
│       │   ├── default.yaml
│       │   ├── development.yaml
│       │   └── production.yaml
│       ├── snippets/           # Reusable template snippets (NEW)
│       │   ├── network-config.yaml.j2
│       │   └── storage-config.yaml.j2
│       ├── vm.yaml.j2          # Legacy VM template
│       ├── service.yaml.j2     # Legacy Service template
│       └── *.html              # Web UI templates
├── config.py                   # Configuration
├── requirements.txt            # Python dependencies
├── run.py                      # Application entry point
└── .env                        # Environment variables (create this)
```

### Running Tests

Currently, no tests are implemented. To add tests:

```bash
# Install testing dependencies
pip install pytest pytest-cov

# Create tests directory
mkdir tests
touch tests/__init__.py
touch tests/test_schemas.py
touch tests/test_template_manager.py
touch tests/test_git_manager.py

# Run tests
pytest tests/ -v
```

### Template Development

The new template system uses profiles for different VM configurations:

1. **Edit Base Templates** (`app/templates/base/`):
   - `vm-base.yaml.j2` - VirtualMachine resource
   - `service-base.yaml.j2` - Service resource

2. **Create Custom Profiles** (`app/templates/profiles/`):
   ```yaml
   # app/templates/profiles/custom.yaml
   name: custom
   description: Custom VM profile
   
   defaults:
     cpu_cores: 2
     memory: 4
     storage_size: 20
     storage_class: your-storage-class
     service_type: LoadBalancer
   
   templates:
     vm: base/vm-base.yaml.j2
     service: base/service-base.yaml.j2
   
   validation:
     max_cpu_cores: 16
     max_memory_gb: 64
   ```

3. **Test Templates**:
   ```python
   from app.template_manager import TemplateManager
   from app.schemas import VMConfigSchema
   
   # Create test config
   config = VMConfigSchema(
       vm_name="test-vm",
       cpu_cores=2,
       memory=4,
       storage_size=20,
       storage_class="longhorn-rwx",
       image_url="https://example.com/image.qcow2",
       service_ports=[{
           "port_name": "ssh",
           "port": 22,
           "protocol": "TCP",
           "targetPort": 22
       }]
   )
   
   # Render template
   tm = TemplateManager()
   yaml_output = tm.render_complete_config(config.to_template_dict())
   print(yaml_output)
   ```

### Validation Development

The new validation system uses Pydantic schemas in `app/schemas.py`:

```python
# Test validation
from app.schemas import VMConfigSchema
from pydantic import ValidationError

try:
    config = VMConfigSchema(
        vm_name="invalid name with spaces",  # Will fail
        cpu_cores=2,
        memory=4,
        # ... other fields
    )
except ValidationError as e:
    print(e.errors())
```

## Troubleshooting

### Common Issues

#### 1. Git Authentication Fails

**Error**: `Authentication failed`

**Solution**:
- Ensure your Personal Access Token (PAT) has correct permissions
- For GitHub: Settings → Developer settings → Personal access tokens → Generate new token
- Required scopes: `repo` (full control)
- Token should not have spaces or special characters in `.env` file

#### 2. Template Rendering Errors

**Error**: `TemplateNotFound` or `TemplateError`

**Solution**:
```bash
# Check template directory structure
ls -la app/templates/base/
ls -la app/templates/profiles/
ls -la app/templates/snippets/

# Ensure all required files exist
```

#### 3. Validation Errors

**Error**: `ValidationError` when creating VMs

**Solution**:
- Check `app/constants.py` for validation limits
- Review `app/schemas.py` for validation rules
- Ensure all required fields are provided
- Check field formats (e.g., VM name must be lowercase alphanumeric)

#### 4. Import Errors

**Error**: `ModuleNotFoundError: No module named 'pydantic'`

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# If still fails, try:
pip install pydantic>=2.0.0
```

#### 5. Git Clone Directory Permissions

**Error**: `PermissionError` when cloning repository

**Solution**:
```bash
# Ensure directory is writable
mkdir -p /tmp/kubevirt-portal/clones
chmod 755 /tmp/kubevirt-portal/clones

# Or change GIT_CLONE_DIR in .env to a writable location
```

### Debug Mode

Enable debug logging:

```env
# In .env
DEBUG=true
```

Run with verbose logging:

```bash
# Set logging level
export FLASK_DEBUG=1
python run.py
```

### Check Application Status

```bash
# Verify templates load correctly
python -c "from app.template_manager import TemplateManager; tm = TemplateManager(); print(tm.list_profiles())"

# Verify schemas import
python -c "from app.schemas import VMConfigSchema; print('Schemas loaded successfully')"

# Verify git manager
python -c "from app.git_manager import GitOperationManager; print('Git manager loaded successfully')"
```

## Testing the Application

### 1. Test Template Rendering (Without Git)

```python
# test_template.py
from app.template_manager import TemplateManager
from app.schemas import VMConfigSchema, ServicePortSchema

# Create test configuration
config = VMConfigSchema(
    vm_name="test-vm",
    cpu_cores=2,
    memory=4,
    storage_size=20,
    storage_class="longhorn-rwx",
    storage_access_mode="ReadWriteMany",
    image_url="https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img",
    user_data="#cloud-config\npassword: test\nchpasswd: { expire: False }",
    hostname="test-vm.example.com",
    address_pool="default",
    service_type="LoadBalancer",
    service_ports=[
        ServicePortSchema(
            port_name="ssh",
            port=22,
            protocol="TCP",
            targetPort=22
        )
    ]
)

# Render template
tm = TemplateManager()
yaml_output = tm.render_complete_config(config.to_template_dict(), profile_name='default')

# Save to file for inspection
with open('test-output.yaml', 'w') as f:
    f.write(yaml_output)

print("Template rendered successfully! Check test-output.yaml")
```

Run the test:
```bash
python test_template.py
cat test-output.yaml
```

### 2. Test Validation

```python
# test_validation.py
from app.schemas import VMConfigSchema
from pydantic import ValidationError

# Test valid configuration
try:
    valid_config = VMConfigSchema(
        vm_name="valid-vm-name",
        cpu_cores=2,
        memory=4,
        storage_size=20,
        storage_class="longhorn-rwx",
        image_url="https://example.com/image.img",
        service_ports=[{
            "port_name": "ssh",
            "port": 22,
            "protocol": "TCP",
            "targetPort": 22
        }]
    )
    print("✓ Valid configuration passed")
except ValidationError as e:
    print("✗ Validation failed:", e)

# Test invalid configuration
try:
    invalid_config = VMConfigSchema(
        vm_name="Invalid Name With Spaces",  # Should fail
        cpu_cores=2,
        memory=4,
        storage_size=20,
        storage_class="longhorn-rwx",
        image_url="https://example.com/image.img",
        service_ports=[{
            "port_name": "ssh",
            "port": 22,
            "protocol": "TCP",
            "targetPort": 22
        }]
    )
    print("✗ Invalid configuration should have failed!")
except ValidationError as e:
    print("✓ Validation correctly rejected invalid config")
    print("  Errors:", e.errors()[0]['msg'])
```

Run the test:
```bash
python test_validation.py
```

### 3. Test Web Interface

1. Start the application:
```bash
python run.py
```

2. Open browser to `http://127.0.0.1:5000`

3. Test workflows:
   - Create a new VM configuration
   - Preview the generated YAML
   - Edit an existing VM
   - Delete a VM
   - View the VM list

## Production Deployment Considerations

When deploying to production:

1. **Environment Variables**:
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Enable `WTF_CSRF_ENABLED=true`

2. **Git Repository**:
   - Use dedicated service account for Git operations
   - Restrict token permissions to specific repository
   - Consider using SSH keys instead of tokens

3. **Storage**:
   - Use persistent volume for `GIT_CLONE_DIR`
   - Regular backups of Git configuration repository

4. **Security**:
   - Run behind reverse proxy (nginx, traefik)
   - Enable HTTPS
   - Implement authentication/authorization
   - Use RBAC for Kubernetes access

5. **Monitoring**:
   - Add application logging
   - Monitor Git operations
   - Track template rendering errors

## Additional Resources

- [KubeVirt Documentation](https://kubevirt.io/user-guide/)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Getting Help

If you encounter issues:

1. Check the logs for error messages
2. Verify your `.env` configuration
3. Ensure all dependencies are installed
4. Review the troubleshooting section above
5. Open an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Your environment details (Python version, OS, etc.)
