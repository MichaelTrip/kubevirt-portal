"""Template management with profile support and validation."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, TemplateError
from app.constants import PROFILE_DEFAULT

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages Jinja2 templates with profile support and YAML validation."""

    def __init__(self, template_dir: Path = None, profiles_dir: Path = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir: Path to templates directory
            profiles_dir: Path to profiles directory
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'
        if profiles_dir is None:
            profiles_dir = template_dir / 'profiles'

        self.template_dir = template_dir
        self.profiles_dir = profiles_dir
        
        # Initialize Jinja2 environment with custom filters
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )
        
        # Add custom filters
        self.env.filters['validate_dns_name'] = self._validate_dns_name
        
        # Load profiles
        self.profiles = self._load_profiles()
        
        logger.info(f"TemplateManager initialized with {len(self.profiles)} profiles")

    def _load_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load all profile configurations from the profiles directory."""
        profiles = {}
        
        if not self.profiles_dir.exists():
            logger.warning(f"Profiles directory not found: {self.profiles_dir}")
            return profiles

        for profile_file in self.profiles_dir.glob('*.yaml'):
            try:
                with open(profile_file, 'r') as f:
                    profile_data = yaml.safe_load(f)
                    profile_name = profile_data.get('name', profile_file.stem)
                    profiles[profile_name] = profile_data
                    logger.debug(f"Loaded profile: {profile_name}")
            except Exception as e:
                logger.error(f"Error loading profile {profile_file}: {e}")

        # Ensure default profile exists
        if PROFILE_DEFAULT not in profiles:
            profiles[PROFILE_DEFAULT] = self._get_default_profile()
            logger.warning("Using built-in default profile")

        return profiles

    def _get_default_profile(self) -> Dict[str, Any]:
        """Return a built-in default profile configuration."""
        return {
            'name': 'default',
            'description': 'Built-in default profile',
            'defaults': {},
            'templates': {
                'vm': 'base/vm-base.yaml.j2',
                'service': 'base/service-base.yaml.j2'
            }
        }

    def _validate_dns_name(self, value: str) -> str:
        """Jinja2 filter to validate DNS names."""
        import re
        from app.constants import DNS_NAME_PATTERN
        
        if not re.match(DNS_NAME_PATTERN, value):
            raise ValueError(f"Invalid DNS name: {value}")
        return value

    def get_profile(self, profile_name: str = PROFILE_DEFAULT) -> Dict[str, Any]:
        """
        Get a profile by name.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Profile configuration dictionary
        """
        if profile_name not in self.profiles:
            logger.warning(f"Profile '{profile_name}' not found, using default")
            profile_name = PROFILE_DEFAULT
        
        return self.profiles[profile_name]

    def merge_with_profile(
        self, 
        context: Dict[str, Any], 
        profile_name: str = PROFILE_DEFAULT
    ) -> Dict[str, Any]:
        """
        Merge context with profile defaults.
        
        Args:
            context: User-provided context
            profile_name: Profile to use for defaults
            
        Returns:
            Merged context with profile defaults
        """
        profile = self.get_profile(profile_name)
        defaults = profile.get('defaults', {})
        
        # Deep merge: context overrides defaults
        merged = defaults.copy()
        merged.update(context)
        
        return merged

    def render_vm_template(
        self, 
        context: Dict[str, Any], 
        profile_name: str = PROFILE_DEFAULT
    ) -> str:
        """
        Render VM template with context.
        
        Args:
            context: Template context (should be from VMConfigSchema.to_template_dict())
            profile_name: Profile to use
            
        Returns:
            Rendered YAML string
            
        Raises:
            TemplateError: If template rendering fails
        """
        profile = self.get_profile(profile_name)
        template_name = profile.get('templates', {}).get('vm', 'base/vm-base.yaml.j2')
        
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(context)
            
            # Validate rendered YAML
            self._validate_yaml(rendered)
            
            return rendered
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rendering VM template: {e}")
            raise

    def render_service_template(
        self, 
        context: Dict[str, Any], 
        profile_name: str = PROFILE_DEFAULT
    ) -> str:
        """
        Render Service template with context.
        
        Args:
            context: Template context
            profile_name: Profile to use
            
        Returns:
            Rendered YAML string
            
        Raises:
            TemplateError: If template rendering fails
        """
        profile = self.get_profile(profile_name)
        template_name = profile.get('templates', {}).get('service', 'base/service-base.yaml.j2')
        
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(context)
            
            # Validate rendered YAML
            self._validate_yaml(rendered)
            
            return rendered
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rendering Service template: {e}")
            raise

    def render_complete_config(
        self, 
        context: Dict[str, Any], 
        profile_name: str = PROFILE_DEFAULT
    ) -> str:
        """
        Render complete VM configuration (VM + Service).
        
        Args:
            context: Template context
            profile_name: Profile to use
            
        Returns:
            Combined YAML string with VM and Service
        """
        vm_yaml = self.render_vm_template(context, profile_name)
        service_yaml = self.render_service_template(context, profile_name)
        
        return f"---\n{vm_yaml}\n---\n{service_yaml}"

    def _validate_yaml(self, yaml_content: str) -> None:
        """
        Validate that the rendered content is valid YAML.
        
        Args:
            yaml_content: YAML string to validate
            
        Raises:
            yaml.YAMLError: If YAML is invalid
        """
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML generated: {e}")
            raise

    def validate_kubernetes_resource(self, yaml_content: str) -> bool:
        """
        Validate that the YAML contains valid Kubernetes resources.
        
        Args:
            yaml_content: YAML string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            doc = yaml.safe_load(yaml_content)
            
            if not isinstance(doc, dict):
                logger.error("YAML document is not a dictionary")
                return False
            
            # Check required Kubernetes fields
            required_fields = ['apiVersion', 'kind', 'metadata']
            for field in required_fields:
                if field not in doc:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate metadata has name
            if 'name' not in doc.get('metadata', {}):
                logger.error("Missing metadata.name")
                return False
            
            return True
        except yaml.YAMLError as e:
            logger.error(f"YAML validation error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return False

    def list_profiles(self) -> list:
        """
        List all available profiles.
        
        Returns:
            List of profile names
        """
        return list(self.profiles.keys())

    def get_profile_info(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Profile information dictionary or None if not found
        """
        profile = self.profiles.get(profile_name)
        if profile:
            return {
                'name': profile.get('name'),
                'description': profile.get('description', 'No description'),
                'defaults': profile.get('defaults', {}),
                'validation': profile.get('validation', {})
            }
        return None
