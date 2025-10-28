"""Test service layer functions."""
import pytest
from info_sur.services import slugify, current_timestamp


def test_slugify_basic():
    """Test basic slugify functionality."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("Test Article 123") == "test-article-123"


def test_slugify_special_characters():
    """Test slugify with special characters."""
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Test@Article#123") == "testarticle123"


def test_slugify_spanish_characters():
    """Test slugify preserves Spanish characters."""
    assert slugify("Málaga") == "málaga"
    assert slugify("España año") == "españa-año"


def test_slugify_multiple_spaces():
    """Test slugify handles multiple spaces."""
    assert slugify("Hello    World") == "hello-world"
    assert slugify("Test  -  Article") == "test-article"


def test_current_timestamp_format():
    """Test that current_timestamp returns correct format."""
    timestamp = current_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) == 14
    assert timestamp.isdigit()
