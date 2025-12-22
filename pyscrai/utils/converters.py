"""
Converters module - Data conversion helpers for PyScrAI Universalis.
"""

from typing import Any, Dict
from datetime import datetime


def datetime_to_str(dt: datetime) -> str:
    """Convert datetime to ISO format string."""
    return dt.isoformat()


def str_to_datetime(s: str) -> datetime:
    """Convert ISO format string to datetime."""
    return datetime.fromisoformat(s)


def mongo_doc_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB document to plain dict, removing _id field.
    
    Args:
        doc: MongoDB document with potential _id field
    
    Returns:
        Dict without MongoDB-specific fields
    """
    result = dict(doc)
    if "_id" in result:
        del result["_id"]
    return result


def dict_to_mongo_doc(data: Dict[str, Any], simulation_id: str) -> Dict[str, Any]:
    """
    Prepare a dict for MongoDB insertion.
    
    Args:
        data: Data dict to prepare
        simulation_id: Simulation identifier
    
    Returns:
        Dict ready for MongoDB insertion
    """
    result = dict(data)
    result["simulation_id"] = simulation_id
    return result

