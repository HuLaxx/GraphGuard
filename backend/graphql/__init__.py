# Backend GraphQL Module
"""
GraphQL API for GraphGuard fraud detection dashboard.
Reference: Specification.md Lines 2730-3100
"""

from .resolvers import schema, get_schema, Query, Mutation

__all__ = [
    "schema",
    "get_schema",
    "Query",
    "Mutation"
]
