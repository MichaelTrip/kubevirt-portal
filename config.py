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
    YAML_SUBDIRECTORY = os.getenv('YAML_SUBDIRECTORY', 'vms/')

    @classmethod
    def validate_config(cls):
        required_vars = [
            ('GIT_REPO_URL', cls.GIT_REPO_URL),
            ('GIT_USERNAME', cls.GIT_USERNAME),
            ('GIT_TOKEN', cls.GIT_TOKEN),
        ]

        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please set these variables in your .env file or environment."
            )
