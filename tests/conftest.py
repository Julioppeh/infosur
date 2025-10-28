"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path
import tempfile
import os

from info_sur.app import create_app
from info_sur.database import Base, engine


@pytest.fixture
def app():
    """Create application for testing."""
    # Use a temporary database for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['DATABASE_PATH'] = str(Path(tmpdir) / 'test.db')
        app = create_app()
        app.config['TESTING'] = True

        yield app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()
