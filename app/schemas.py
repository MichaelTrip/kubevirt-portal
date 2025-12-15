"""Pydantic models for input validation and data validation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import re
from app.constants import (
    VM_NAME_PATTERN, DNS_NAME_PATTERN, TAG_KEY_PATTERN,
    MAX_CPU_CORES, MIN_CPU_CORES, MAX_MEMORY_GB, MIN_MEMORY_GB,
    MAX_STORAGE_GB, MIN_STORAGE_GB, MAX_VM_NAME_LENGTH,
    MAX_TAG_KEY_LENGTH, MAX_TAG_VALUE_LENGTH, MIN_PORT, MAX_PORT,
    DEFAULT_STORAGE_CLASS, DEFAULT_STORAGE_ACCESS_MODE, DEFAULT_SERVICE_TYPE
)


class TagSchema(BaseModel):
    """Schema for VM tags/labels."""
    key: str = Field(..., max_length=MAX_TAG_KEY_LENGTH)
    value: str = Field(..., max_length=MAX_TAG_VALUE_LENGTH)

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        """Validate tag key follows Kubernetes label requirements."""
        if not v:
            raise ValueError("Tag key cannot be empty")
        
        # Check for reserved prefixes
        if v.startswith('kubevirt.io/'):
            raise ValueError("Tag key cannot use reserved prefix 'kubevirt.io/'")
        
        if not re.match(TAG_KEY_PATTERN, v):
            raise ValueError(
                f"Tag key '{v}' must start and end with alphanumeric characters "
                "and can contain hyphens, underscores, dots, and slashes"
            )
        return v

    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        """Validate tag value."""
        if not v:
            raise ValueError("Tag value cannot be empty")
        # Kubernetes label values must be alphanumeric with hyphens, underscores, dots
        if not re.match(r'^[a-zA-Z0-9]([-._a-zA-Z0-9]*[a-zA-Z0-9])?$', v):
            raise ValueError(
                f"Tag value '{v}' must start and end with alphanumeric characters "
                "and can contain hyphens, underscores, and dots"
            )
        return v


class ServicePortSchema(BaseModel):
    """Schema for service port configuration."""
    port_name: str = Field(..., min_length=1, max_length=63)
    port: int = Field(..., ge=MIN_PORT, le=MAX_PORT)
    protocol: str = Field(default="TCP")
    targetPort: int = Field(..., ge=MIN_PORT, le=MAX_PORT)

    @field_validator('port_name')
    @classmethod
    def validate_port_name(cls, v):
        """Validate port name follows Kubernetes naming."""
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', v):
            raise ValueError(
                f"Port name '{v}' must be lowercase alphanumeric with hyphens, "
                "starting and ending with alphanumeric characters"
            )
        return v

    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v):
        """Validate protocol is TCP or UDP."""
        if v.upper() not in ['TCP', 'UDP']:
            raise ValueError(f"Protocol must be TCP or UDP, got '{v}'")
        return v.upper()


class NetworkConfigSchema(BaseModel):
    """Schema for network configuration."""
    interface_name: str = Field(default="enp1s0")
    enable_dhcp: bool = Field(default=True)
    enable_ipv6: bool = Field(default=True)
    ipv6_address: Optional[str] = Field(default="fd10:0:2::2/120")
    ipv6_gateway: Optional[str] = Field(default="fd10:0:2::1")

    @field_validator('ipv6_address')
    @classmethod
    def validate_ipv6_address(cls, v, info):
        """Validate IPv6 address format if IPv6 is enabled."""
        if v and info.data.get('enable_ipv6'):
            # Basic IPv6 validation with CIDR
            if not re.match(r'^[0-9a-fA-F:]+/\d+$', v):
                raise ValueError(f"Invalid IPv6 address format: {v}")
        return v

    @field_validator('ipv6_gateway')
    @classmethod
    def validate_ipv6_gateway(cls, v, info):
        """Validate IPv6 gateway format if IPv6 is enabled."""
        if v and info.data.get('enable_ipv6'):
            # Basic IPv6 validation
            if not re.match(r'^[0-9a-fA-F:]+$', v):
                raise ValueError(f"Invalid IPv6 gateway format: {v}")
        return v


class VMConfigSchema(BaseModel):
    """Complete VM configuration schema with validation."""
    vm_name: str = Field(..., max_length=MAX_VM_NAME_LENGTH)
    tags: List[TagSchema] = Field(default_factory=list)
    cpu_cores: int = Field(..., ge=MIN_CPU_CORES, le=MAX_CPU_CORES)
    memory: int = Field(..., ge=MIN_MEMORY_GB, le=MAX_MEMORY_GB)
    storage_size: int = Field(..., ge=MIN_STORAGE_GB, le=MAX_STORAGE_GB)
    storage_class: str = Field(default=DEFAULT_STORAGE_CLASS)
    storage_access_mode: str = Field(default=DEFAULT_STORAGE_ACCESS_MODE)
    image_url: str = Field(..., min_length=1)
    user_data: Optional[str] = Field(default="")
    hostname: Optional[str] = Field(default="")
    address_pool: Optional[str] = Field(default="default")
    service_ports: List[ServicePortSchema] = Field(default_factory=list)
    service_type: str = Field(default=DEFAULT_SERVICE_TYPE)
    network_config: NetworkConfigSchema = Field(default_factory=NetworkConfigSchema)

    @field_validator('vm_name')
    @classmethod
    def validate_vm_name(cls, v):
        """Validate VM name follows Kubernetes naming conventions."""
        if not v:
            raise ValueError("VM name cannot be empty")
        
        if not re.match(VM_NAME_PATTERN, v):
            raise ValueError(
                f"VM name '{v}' must be lowercase alphanumeric with hyphens, "
                "starting and ending with alphanumeric characters"
            )
        
        if '__' in v:
            raise ValueError("VM name cannot contain double underscores")
        
        return v

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v):
        """Validate hostname is a valid DNS name."""
        if v and not re.match(DNS_NAME_PATTERN, v):
            raise ValueError(
                f"Hostname '{v}' must be a valid DNS name (lowercase alphanumeric "
                "with hyphens and dots)"
            )
        return v

    @field_validator('storage_access_mode')
    @classmethod
    def validate_storage_access_mode(cls, v):
        """Validate storage access mode."""
        valid_modes = ['ReadWriteMany', 'ReadWriteOnce', 'ReadOnlyMany']
        if v not in valid_modes:
            raise ValueError(f"Storage access mode must be one of {valid_modes}")
        return v

    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        """Validate service type."""
        valid_types = ['LoadBalancer', 'ClusterIP', 'NodePort']
        if v not in valid_types:
            raise ValueError(f"Service type must be one of {valid_types}")
        return v

    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v):
        """Validate image URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Image URL must start with http:// or https://")
        return v

    @field_validator('user_data')
    @classmethod
    def validate_user_data(cls, v):
        """Validate and sanitize user data."""
        if not v:
            return v
        
        # Ensure it starts with #cloud-config
        v = v.strip()
        if v and not v.startswith('#cloud-config'):
            v = '#cloud-config\n' + v
        
        # Basic YAML injection prevention
        if '{{' in v or '{%' in v:
            raise ValueError("User data cannot contain Jinja2 template syntax")
        
        return v

    @field_validator('service_ports')
    @classmethod
    def validate_service_ports(cls, v):
        """Validate service ports list."""
        if not v:
            raise ValueError("At least one service port must be defined")
        
        # Check for duplicate port names
        port_names = [port.port_name for port in v]
        if len(port_names) != len(set(port_names)):
            raise ValueError("Service port names must be unique")
        
        # Check for duplicate port numbers
        port_numbers = [port.port for port in v]
        if len(port_numbers) != len(set(port_numbers)):
            raise ValueError("Service port numbers must be unique")
        
        return v

    @model_validator(mode='after')
    def validate_config(self):
        """Cross-field validation."""
        # Ensure storage_size is reasonable for the memory size
        memory = self.memory
        storage = self.storage_size
        
        if storage < memory:
            raise ValueError(
                f"Storage size ({storage}GB) should be at least equal to memory ({memory}GB)"
            )
        
        return self

    def to_template_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for template rendering."""
        data = self.dict()
        # Convert Pydantic models to dicts for template
        data['tags'] = [tag.dict() for tag in self.tags]
        data['service_ports'] = [port.dict() for port in self.service_ports]
        data['network_config'] = self.network_config.dict()
        return data

    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = 'forbid'  # Forbid extra fields
