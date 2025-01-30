# Feature Flags Implementation and Navigation Updates

## Description
This PR implements feature flags for controlling access to certain functionality, particularly the Cluster VMs page. The implementation provides a flexible way to manage feature visibility and access control.

## Changes from CHANGELOG v1.3.1

### Added
- Feature flag for Cluster VMs page visibility
- Conditional navigation menu items based on feature flags
- Route protection for disabled features

### Changed
- Updated navigation menu to respect feature flags
- Improved user feedback for disabled features

## Implementation Details
- Environment variable based feature flags
- Protected routes for disabled features
- Enhanced user feedback when attempting to access disabled features
- Updated navigation menu that dynamically shows/hides based on feature flags

## Testing Done
- [x] Verified feature flag functionality in development environment
- [x] Tested all navigation paths with features enabled/disabled
- [x] Confirmed proper feedback messages for disabled features
- [x] Validated environment variable handling

## Related Issues
Implements comprehensive feature flag system for improved feature management
