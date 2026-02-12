
import os
from typing import Dict, List, Optional

class APIKeyManager:
    """
    Unified API Key Manager for rotating credentials.
    Parses comma-separated keys from config/env and manages rotation state.
    """
    
    def __init__(self):
        # Default index from environment (useful for subprocesses receiving index)
        # Defaults to 0 for initial process
        try:
            self._index = int(os.getenv('_KEY_SET_INDEX', '0'))
        except ValueError:
            self._index = 0
            
        self._keys: Dict[str, List[str]] = {}

    def register(self, name: str, raw_value: Optional[str]) -> None:
        """
        Register an API key variable, supporting comma-separated values.
        
        Args:
            name: Internal identifier for the key (e.g., 'FMP')
            raw_value: Raw string from environment/config (e.g., 'key1,key2')
        """
        if not raw_value:
            self._keys[name] = []
            return
        
        # Split by comma and strip whitespace to support multiple keys
        # Example: "key1, key2" -> ["key1", "key2"]
        self._keys[name] = [k.strip() for k in raw_value.split(',') if k.strip()]

    def get(self, name: str) -> Optional[str]:
        """
        Get the current key for the given name based on active rotation index.
        Thread-safe for read operations (index is atomic int).
        """
        candidates = self._keys.get(name, [])
        if not candidates:
            return None
        
        # Round-robin selection: index % length
        # This ensures we always get a valid key even if index increments indefinitely
        return candidates[self._index % len(candidates)]
    
    def rotate(self) -> int:
        """
        Rotate to the next set of keys.
        Returns the new index.
        """
        self._index += 1
        return self._index

    @property
    def current_index(self) -> int:
        """Get current rotation index."""
        return self._index
    
    def validate_has_key(self, name: str) -> bool:
        """
        Check if at least one key exists for the given name.
        Useful for startup validation.
        """
        return len(self._keys.get(name, [])) > 0

    def get_key_count(self, name: str) -> int:
        """Get number of keys configured for a specific provider."""
        return len(self._keys.get(name, []))
