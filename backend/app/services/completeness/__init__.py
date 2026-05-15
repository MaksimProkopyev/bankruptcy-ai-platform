"""
Completeness service for document checklist tracking.

This module provides:
- DocumentMatcher: matches uploaded documents to checklist items
- CompletenessChecker: main service for managing checklist progress
- Pydantic schemas for request/response validation
"""

from .checker import CompletenessChecker
from .matcher import DocumentMatcher
from .schemas import (
    AutoMatchResponse,
    ChecklistItemSchema,
    ChecklistSchema,
    CompletenessInitRequest,
    CompletenessItemResponse,
    CompletenessItemUpdateRequest,
    CompletenessProgressResponse,
)

__all__ = [
    "CompletenessChecker",
    "DocumentMatcher",
    "ChecklistItemSchema",
    "ChecklistSchema",
    "CompletenessProgressResponse",
    "CompletenessItemResponse",
    "CompletenessInitRequest",
    "CompletenessItemUpdateRequest",
    "AutoMatchResponse",
]
