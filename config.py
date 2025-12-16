import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    WTF_CSRF_ENABLED = False  # Disable CSRF protection

    # Git configuration
    GIT_REPO_URL = os.getenv('GIT_REPO_URL')
    GIT_USERNAME = os.getenv('GIT_USERNAME')
    GIT_TOKEN = os.getenv('GIT_TOKEN')

    # YAML configuration
    YAML_SUBDIRECTORY = os.getenv('YAML_SUBDIRECTORY', 'virtualmachines/')
    
    # Git clone directory - use /tmp for local dev, /app for Docker
    GIT_CLONE_DIR = os.getenv('GIT_CLONE_DIR', '/tmp/kubevirt-portal/clones')
    
    # Feature flags
    EXTERNAL_DNS_ENABLED = os.getenv('EXTERNAL_DNS_ENABLED', 'false').lower() == 'true'
    METALLB_ENABLED = os.getenv('METALLB_ENABLED', 'false').lower() == 'true'
    CLUSTER_VMS_ENABLED = os.getenv('CLUSTER_VMS_ENABLED', 'false').lower() == 'true'
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # External DNS configuration
    EXTERNAL_DNS_DOMAIN = os.getenv('EXTERNAL_DNS_DOMAIN', 'k8s-lan.example.com')
    
    # MetalLB configuration
    METALLB_DEFAULT_POOL = os.getenv('METALLB_DEFAULT_POOL', 'default')

    def __init__(self):
        # Validate immediately during initialization
        self.validate_config()

    def validate_config(self):
        """Validate required environment variables and raise EnvironmentError if missing"""
        required_vars = [
            ('GIT_REPO_URL', self.GIT_REPO_URL),
            ('GIT_USERNAME', self.GIT_USERNAME),
            ('GIT_TOKEN', self.GIT_TOKEN),
        ]

        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

        if missing_vars:
            error_msg = (
                f"{', '.join(missing_vars)}\n\n"
                "Please set these variables in your .env file or environment.\n"
                "Example .env file:\n"
                "GIT_REPO_URL=https://github.com/your/repo.git\n"
                "GIT_USERNAME=your-username\n"
                "GIT_TOKEN=your-token"
            )
            raise EnvironmentError(error_msg)
