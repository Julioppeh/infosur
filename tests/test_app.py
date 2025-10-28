"""Test Flask application routes and endpoints."""
import pytest
from flask import Flask


def test_app_initialization(app):
    """Test that the app initializes correctly."""
    assert app is not None
    assert isinstance(app, Flask)


def test_index_redirect(client):
    """Test that the index redirects to /editor."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/editor' in response.location


def test_editor_page(client):
    """Test that the editor page loads."""
    response = client.get('/editor')
    assert response.status_code == 200


def test_api_list_articles_empty(client):
    """Test listing articles when database is empty."""
    response = client.get('/api/articles')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_get_template(client):
    """Test getting the template."""
    response = client.get('/api/template')
    assert response.status_code == 200
    data = response.get_json()
    assert 'template' in data
    assert isinstance(data['template'], str)


def test_api_update_template(client):
    """Test updating the template."""
    new_template = '<html><body>Test Template</body></html>'
    response = client.put(
        '/api/template',
        json={'template': new_template},
        content_type='application/json'
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'saved'


def test_api_get_nonexistent_article(client):
    """Test getting a nonexistent article returns 404."""
    response = client.get('/api/articles/999')
    assert response.status_code == 404


def test_api_delete_nonexistent_article(client):
    """Test deleting a nonexistent article returns 404."""
    response = client.delete('/api/articles/999')
    assert response.status_code == 404


def test_images_endpoint_invalid_extension(client):
    """Test that invalid file extensions are rejected."""
    response = client.get('/images/test.exe')
    assert response.status_code == 404


def test_images_endpoint_directory_traversal(client):
    """Test that directory traversal is prevented."""
    response = client.get('/images/../../../etc/passwd')
    assert response.status_code == 404


def test_serve_article_invalid_format(client):
    """Test that invalid article slug format returns 404."""
    response = client.get('/invalid-slug')
    assert response.status_code == 404


def test_serve_article_nonexistent(client):
    """Test that nonexistent article returns 404."""
    response = client.get('/test-article-20231225120000')
    assert response.status_code == 404
