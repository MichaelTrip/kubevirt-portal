"""Constants used throughout the application."""

# Kubernetes Labels
LABEL_KUBEVIRT_VM = "kubevirt.io/vm"

# Annotations
ANNOTATION_METALLB_ADDRESS_POOL = "metallb.universe.tf/address-pool"
ANNOTATION_EXTERNAL_DNS_HOSTNAME = "external-dns.alpha.kubernetes.io/hostname"
ANNOTATION_LIVE_MIGRATION = "kubevirt.io/allow-pod-bridge-network-live-migration"

# KubeVirt API
KUBEVIRT_API_GROUP = "kubevirt.io"
KUBEVIRT_API_VERSION = "v1"
RESOURCE_VIRTUAL_MACHINES = "virtualmachines"
RESOURCE_VIRTUAL_MACHINE_INSTANCES = "virtualmachineinstances"

# Default Values
DEFAULT_STORAGE_CLASS = "longhorn-rwx"
DEFAULT_STORAGE_ACCESS_MODE = "ReadWriteMany"
DEFAULT_SERVICE_TYPE = "LoadBalancer"
DEFAULT_NETWORK_INTERFACE = "enp1s0"
DEFAULT_IPV6_ADDRESS = "fd10:0:2::2/120"
DEFAULT_IPV6_GATEWAY = "fd10:0:2::1"
DEFAULT_ADDRESS_POOL = "default"
DEFAULT_EXTERNAL_DNS_DOMAIN = "k8s-lan.example.com"
DEFAULT_METALLB_POOL = "default"

# Validation Patterns
VM_NAME_PATTERN = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
DNS_NAME_PATTERN = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
TAG_KEY_PATTERN = r"^[a-zA-Z0-9]([-._a-zA-Z0-9]*[a-zA-Z0-9])?(/[a-zA-Z0-9]([-._a-zA-Z0-9]*[a-zA-Z0-9])?)?$"

# Limits
MAX_CPU_CORES = 32
MIN_CPU_CORES = 1
MAX_MEMORY_GB = 128
MIN_MEMORY_GB = 1
MAX_STORAGE_GB = 4096
MIN_STORAGE_GB = 1
MAX_VM_NAME_LENGTH = 63
MAX_TAG_KEY_LENGTH = 253
MAX_TAG_VALUE_LENGTH = 63

# Service Port Limits
MIN_PORT = 1
MAX_PORT = 65535

# Git
GIT_COMMIT_MESSAGE_CREATE = "Add VM configuration for {vm_name}"
GIT_COMMIT_MESSAGE_UPDATE = "Update VM configuration for {vm_name}"
GIT_COMMIT_MESSAGE_DELETE = "Delete VM configuration for {vm_name}"

# File Extensions
YAML_EXTENSION = ".yaml"
JINJA_EXTENSION = ".j2"

# Template Profiles
PROFILE_DEFAULT = "default"
PROFILE_DEVELOPMENT = "development"
PROFILE_PRODUCTION = "production"
