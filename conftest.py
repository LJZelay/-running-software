"""pytest configuration and test runner setup."""

import sys
import os

# Add project root to path so tests can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "domain: mark test as a domain layer test"
    )
    config.addinivalue_line(
        "markers", "application: mark test as an application layer test"
    )
    config.addinivalue_line(
        "markers", "external: mark test as an external interface test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
