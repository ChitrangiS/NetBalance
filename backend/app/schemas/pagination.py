from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Generic[T] means PaginatedResponse[ExpenseSummary] is a valid type,
    distinct from PaginatedResponse[GroupResponse] — Pydantic and TypeScript
    both understand this pattern.

    Usage in a route:
        @router.get("/", response_model=PaginatedResponse[ExpenseSummary])
        def list_expenses(...) -> PaginatedResponse[ExpenseSummary]:
            ...
    """
    items: list[T]
    total: int            # total records matching the query (before pagination)
    page: int             # current page number (1-indexed)
    page_size: int        # items per page
    total_pages: int      # ceil(total / page_size)
    has_next: bool
    has_previous: bool


def make_paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
) -> dict:
    """
    Factory function that computes derived pagination fields.
    Called from service layer — avoids duplicating the math everywhere.
    """
    import math
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }