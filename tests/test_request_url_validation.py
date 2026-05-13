"""
Test URL validation in Request
"""
import pytest


class TestRequestURLValidation:
    """Test Request URL validation"""
    
    def test_empty_url_rejected(self):
        """Test that empty URL is rejected"""
        from crawlo.network import Request
        
        with pytest.raises(ValueError, match="URL cannot be empty"):
            Request(url="")
    
    def test_whitespace_url_rejected(self):
        """Test that whitespace-only URL is rejected"""
        from crawlo.network import Request
        
        with pytest.raises(ValueError, match="URL cannot be empty"):
            Request(url="   ")
    
    def test_none_url_rejected(self):
        """Test that None URL is rejected"""
        from crawlo.network import Request
        
        with pytest.raises((ValueError, TypeError)):
            Request(url=None)
    
    def test_invalid_url_in_from_dict(self):
        """Test that invalid URL in from_dict is rejected"""
        from crawlo.network import Request
        
        with pytest.raises(ValueError, match="Invalid URL in request data"):
            Request.from_dict({'url': None, 'method': 'GET'})
    
    def test_empty_url_in_from_dict(self):
        """Test that empty URL in from_dict is rejected"""
        from crawlo.network import Request
        
        with pytest.raises(ValueError):
            Request.from_dict({'url': '', 'method': 'GET'})
    
    def test_placeholder_url_rejected(self):
        """Test that placeholder URL like 'url...' is rejected"""
        from crawlo.network import Request
        
        # This should fail URL scheme validation
        with pytest.raises(ValueError, match="URL 缺少 HTTP"):
            Request(url="url...")
    
    def test_valid_url_accepted(self):
        """Test that valid URL is accepted"""
        from crawlo.network import Request
        
        request = Request(url="http://example.com")
        assert request.url == "http://example.com"
    
    def test_https_url_accepted(self):
        """Test that HTTPS URL is accepted"""
        from crawlo.network import Request
        
        request = Request(url="https://example.com/path?query=value")
        assert request.url.startswith("https://")
