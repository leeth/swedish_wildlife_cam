"""
HTTP client abstraction with retry logic and error handling.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import requests
import time
from urllib.parse import urljoin
import json


class HttpClient(ABC):
    """Abstract HTTP client for API operations."""
    
    @abstractmethod
    def post(self, url: str, data: Dict[str, Any] = None, files: Dict[str, Any] = None, 
             headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a POST request."""
        pass
    
    @abstractmethod
    def get(self, url: str, params: Dict[str, Any] = None, 
            headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a GET request."""
        pass


class RetryHttpClient(HttpClient):
    """HTTP client with retry logic and error handling."""
    
    def __init__(self, base_url: str = "", max_retries: int = 3, 
                 retry_delay: float = 1.0, backoff_factor: float = 2.0):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic."""
        full_url = urljoin(self.base_url, url)
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, full_url, **kwargs)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    raise HttpError(f"Request failed after {self.max_retries + 1} attempts: {e}")
                
                # Calculate delay with exponential backoff
                delay = self.retry_delay * (self.backoff_factor ** attempt)
                time.sleep(delay)
                
                # Log retry attempt
                print(f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay:.1f}s: {e}")
    
    def post(self, url: str, data: Dict[str, Any] = None, files: Dict[str, Any] = None, 
             headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a POST request with retry logic."""
        try:
            response = self._make_request('POST', url, data=data, files=files, 
                                        headers=headers, timeout=timeout)
            return response.json()
        except json.JSONDecodeError as e:
            raise HttpError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise HttpError(f"POST request failed: {e}")
    
    def get(self, url: str, params: Dict[str, Any] = None, 
            headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a GET request with retry logic."""
        try:
            response = self._make_request('GET', url, params=params, 
                                        headers=headers, timeout=timeout)
            return response.json()
        except json.JSONDecodeError as e:
            raise HttpError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise HttpError(f"GET request failed: {e}")


class SimpleHttpClient(HttpClient):
    """Simple HTTP client without retry logic."""
    
    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.session = requests.Session()
    
    def post(self, url: str, data: Dict[str, Any] = None, files: Dict[str, Any] = None, 
             headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a POST request."""
        try:
            full_url = urljoin(self.base_url, url)
            response = self.session.post(full_url, data=data, files=files, 
                                       headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HttpError(f"POST request failed: {e}")
        except json.JSONDecodeError as e:
            raise HttpError(f"Invalid JSON response: {e}")
    
    def get(self, url: str, params: Dict[str, Any] = None, 
            headers: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a GET request."""
        try:
            full_url = urljoin(self.base_url, url)
            response = self.session.get(full_url, params=params, 
                                      headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HttpError(f"GET request failed: {e}")
        except json.JSONDecodeError as e:
            raise HttpError(f"Invalid JSON response: {e}")


class HttpError(Exception):
    """HTTP operation error."""
    pass


def create_http_client(client_type: str = "retry", **kwargs) -> HttpClient:
    """Factory function to create HTTP clients."""
    if client_type == "retry":
        return RetryHttpClient(**kwargs)
    elif client_type == "simple":
        return SimpleHttpClient(**kwargs)
    else:
        raise ValueError(f"Unsupported HTTP client type: {client_type}")
