#!/usr/bin/env python
"""Manages access to nuclear data files packaged with PLEIADES."""

from importlib import resources
from pathlib import Path
from typing import Dict, Optional
import functools

class NuclearDataManager:
    """Manages access to nuclear data files packaged with PLEIADES."""
    
    CATEGORIES = {
        'isotopes': ['isotopes.info', 'mass.mas20', 'neutrons.list'],
        'resonances': ['res_endf8.endf'],
        'cross_sections': ['ag-n.tot', 'au-n.tot', 'pu-n.tot', 'ta-n.tot', 'u-n.tot', 'w-n.tot']
    }
    
    @staticmethod
    @functools.lru_cache()  # Cache the path lookups
    def get_file_path(category: str, filename: str) -> Path:
        """Get the path to a data file.
        
        Args:
            category: Data category ('isotopes', 'resonances', 'cross_sections')
            filename: Name of the file
            
        Returns:
            Path to the data file
            
        Raises:
            ValueError: If category or filename is invalid
        """
        if category not in NuclearDataManager.CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        if filename not in NuclearDataManager.CATEGORIES[category]:
            raise ValueError(f"Invalid filename for category {category}: {filename}")
            
        with resources.path(f'pleiades.data.{category}', filename) as path:
            return path
    
    @staticmethod
    def list_files(category: Optional[str] = None) -> Dict[str, list]:
        """List available data files.
        
        Args:
            category: Optional category to list files for
            
        Returns:
            Dictionary of categories and their files
        """
        if category:
            if category not in NuclearDataManager.CATEGORIES:
                raise ValueError(f"Invalid category: {category}")
            return {category: NuclearDataManager.CATEGORIES[category]}
        return NuclearDataManager.CATEGORIES
