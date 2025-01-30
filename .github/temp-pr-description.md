# Debug Logging Enhancements and Dependency Updates

## Description
This PR implements optional debug logging functionality and updates critical dependencies for improved security and performance.

## Changes from CHANGELOG [Unreleased]

### Added
- Optional debug logging with DEBUG environment variable
- Improved logging configuration based on DEBUG setting
- Warning filters for cryptography deprecation messages

### Changed
- Updated paramiko to 3.5.0 and cryptography to 42.0.0
- Improved logging initialization sequence
- Better handling of environment variables

## Implementation Details
- Environment variable based debug control
- Enhanced logging configuration system
- Updated dependency management
- Improved warning handling for deprecated features

## Testing Done
- [x] Verified debug logging functionality
- [x] Tested with both DEBUG enabled and disabled
- [x] Confirmed warning filters are working
- [x] Validated updated dependencies

## Related Issues
Implements improved debugging capabilities and security updates
