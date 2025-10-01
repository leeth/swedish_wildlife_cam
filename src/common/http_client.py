"""
HTTP Client utilities for Odins Ravne.
"""

import time
import requests


class HttpClient:
    """Base HTTP client interface."""
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return requests.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return requests.post(url, **kwargs)


class RetryHttpClient(HttpClient):
    """HTTP client with retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize retry HTTP client."""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))
        
        raise requests.RequestException("Max retries exceeded")
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))
        
        raise requests.RequestException("Max retries exceeded")


def create_http_client(client_type: str = "retry", **kwargs) -> HttpClient:
    """Create HTTP client instance."""
    if client_type == "retry":
        return RetryHttpClient(**kwargs)
    else:
        return HttpClient()
