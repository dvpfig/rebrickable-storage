"""
Rebrickable API client for fetching LEGO set inventories and metadata.

This module provides a client for interacting with the Rebrickable API v3,
including rate limiting, error handling, and retry logic.
"""

import time
import requests
from typing import Dict, List, Optional
from datetime import datetime


class APIError(Exception):
    """Base exception for API errors."""
    pass


class RateLimitError(APIError):
    """Exception for rate limit errors."""
    pass


class RebrickableAPI:
    """Client for Rebrickable API v3."""
    
    BASE_URL = "https://rebrickable.com/api/v3"
    
    def __init__(self, api_key: str, timeout: int = 10):
        """
        Initialize API client.
        
        Args:
            api_key: Rebrickable API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"key {api_key}"})
        
        # Rate limiting: 10 requests per second max
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def validate_key(self) -> bool:
        """
        Validate API key by making a test request.
        
        Returns:
            True if key is valid, False otherwise
        """
        try:
            # Use a simple endpoint to test the key
            url = f"{self.BASE_URL}/lego/colors/"
            self._rate_limit()
            response = self.session.get(url, timeout=self.timeout, params={"page_size": 1})
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                return False
            else:
                # Other errors - treat as invalid for safety
                return False
                
        except requests.RequestException:
            # Network errors - can't validate, treat as invalid
            return False
    
    def get_set_parts(self, set_number: str, include_spares: bool = True) -> List[Dict]:
        """
        Get parts list for a LEGO set.
        
        Args:
            set_number: Set number (e.g., "31147-1")
            include_spares: Whether to include spare parts
            
        Returns:
            List of part dictionaries with keys:
                - part_num: Part number
                - color_id: Color ID
                - color_name: Color name
                - quantity: Quantity in set
                - is_spare: Whether this is a spare part
                
        Raises:
            APIError: If request fails
            RateLimitError: If rate limit exceeded
        """
        url = f"{self.BASE_URL}/lego/sets/{set_number}/parts/"
        
        all_parts = []
        page = 1
        
        while True:
            self._rate_limit()
            
            params = {
                "page": page,
                "page_size": 1000,  # Max page size
                "inc_part_details": 1
            }
            
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                data = self._handle_response(response)
                
                # Extract parts from response
                results = data.get("results", [])
                
                for item in results:
                    part_data = {
                        "part_num": item["part"]["part_num"],
                        "color_id": item["color"]["id"],
                        "color_name": item["color"]["name"],
                        "quantity": item["quantity"],
                        "is_spare": item.get("is_spare", False)
                    }
                    
                    # Filter spares if requested
                    if include_spares or not part_data["is_spare"]:
                        all_parts.append(part_data)
                
                # Check if there are more pages
                if data.get("next") is None:
                    break
                    
                page += 1
                
            except requests.RequestException as e:
                raise APIError(f"Network error fetching parts for set {set_number}: {str(e)}")
        
        return all_parts
    
    def get_set_info(self, set_number: str) -> Dict:
        """
        Get basic information about a set.
        
        Args:
            set_number: Set number (e.g., "31147-1")
        
        Returns:
            Dictionary with set_num, name, year, num_parts
            
        Raises:
            APIError: If request fails
            RateLimitError: If rate limit exceeded
        """
        url = f"{self.BASE_URL}/lego/sets/{set_number}/"
        
        self._rate_limit()
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            data = self._handle_response(response)
            
            return {
                "set_num": data["set_num"],
                "name": data["name"],
                "year": data.get("year"),
                "num_parts": data.get("num_parts", 0)
            }
            
        except requests.RequestException as e:
            raise APIError(f"Network error fetching info for set {set_number}: {str(e)}")
    
    def get_part_info(self, part_num: str) -> Optional[Dict]:
        """
        Get information about a specific part including image URL.
        
        Args:
            part_num: Part number (e.g., "3001")
        
        Returns:
            Dictionary with part_num, name, part_img_url, or None if not found
            
        Raises:
            APIError: If request fails (except 404)
            RateLimitError: If rate limit exceeded (429)
        """
        url = f"{self.BASE_URL}/lego/parts/{part_num}/"
        
        self._rate_limit()
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            # Handle 404 gracefully - part doesn't exist
            if response.status_code == 404:
                return None
            
            data = self._handle_response(response)
            
            return {
                "part_num": data["part_num"],
                "name": data.get("name", ""),
                "part_img_url": data.get("part_img_url", "")
            }
            
        except requests.RequestException as e:
            raise APIError(f"Network error fetching info for part {part_num}: {str(e)}")
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _handle_response(self, response: requests.Response) -> Dict:
        """
        Handle API response and errors.
        
        Args:
            response: Response object from requests
            
        Returns:
            Parsed JSON data
        
        Raises:
            APIError: For 4xx/5xx errors
            RateLimitError: For 429 errors
        """
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.")
        
        elif response.status_code == 404:
            raise APIError(f"Resource not found (404): {response.url}")
        
        elif response.status_code == 401:
            raise APIError("Unauthorized (401): Invalid API key")
        
        elif response.status_code == 403:
            raise APIError("Forbidden (403): Access denied")
        
        elif 400 <= response.status_code < 500:
            raise APIError(f"Client error ({response.status_code}): {response.text}")
        
        elif 500 <= response.status_code < 600:
            raise APIError(f"Server error ({response.status_code}): {response.text}")
        
        else:
            raise APIError(f"Unexpected status code ({response.status_code}): {response.text}")
