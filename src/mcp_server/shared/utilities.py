"""
Utility functions for MCP server
"""
import os
import logging

logger = logging.getLogger(__name__)


def cleanup_temp_file(file_path: str) -> bool:
    """
    Delete a temporary file.

    Args:
        file_path: Path to the file to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Temporary file {file_path} deleted successfully")
            return True
        else:
            logger.warning(f"Temporary file {file_path} does not exist")
            return False
    except Exception as e:
        logger.error(f"Error deleting temporary file {file_path}: {e}")
        return False


# Export all
__all__ = ['cleanup_temp_file']
