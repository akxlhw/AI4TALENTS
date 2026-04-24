"""
Batch query utilities for PostgreSQL parameter limit handling.

PostgreSQL has a parameter limit of 32767, so IN queries with large lists
must be processed in batches to avoid errors.

Usage:
    from app.services.common.batch_utils import batch_in_query, BATCH_SIZE

    # Simple batch query
    results = await batch_in_query(
        session,
        select(Talent).where(Talent.talent_id.in_(ids)),
        ids,
        lambda result: result.scalars().all()
    )

    # With custom result processor
    id_map = await batch_in_query(
        session,
        select(Talent.talent_id, Talent.source_record_id).where(...),
        ids,
        lambda result: {row.source_record_id: row.talent_id for row in result.all()}
    )
"""

from typing import TypeVar, Callable, Awaitable, List, Any
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

# PostgreSQL parameter limit is 32767
# Using 5000 as safe batch size for IN queries (allows for other query params)
BATCH_SIZE = 5000

T = TypeVar('T')
R = TypeVar('R')


async def batch_in_query(
    session: AsyncSession,
    query_builder: Callable[[List[Any]], Select],
    items: List[Any],
    result_processor: Callable[[Any], R],
    batch_size: int = BATCH_SIZE
) -> List[R]:
    """
    Execute a query with IN clause in batches.

    Args:
        session: AsyncSession instance
        query_builder: Function that takes a list of items and returns a Select query
        items: List of items to use in IN clause
        result_processor: Function to process each batch result
        batch_size: Number of items per batch (default: 5000)

    Returns:
        List of processed results from all batches

    Example:
        results = await batch_in_query(
            session,
            lambda batch: select(Talent).where(Talent.talent_id.in_(batch)),
            talent_ids,
            lambda result: result.scalars().all()
        )
    """
    if not items:
        return []

    all_results: List[R] = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        query = query_builder(batch)
        result = await session.execute(query)
        processed = result_processor(result)
        all_results.extend(processed)

    return all_results


async def batch_in_query_flat(
    session: AsyncSession,
    query_builder: Callable[[List[Any]], Select],
    items: List[Any],
    batch_size: int = BATCH_SIZE
) -> List[Any]:
    """
    Execute a query with IN clause in batches, returning flattened scalar results.

    Convenience wrapper for the common case of returning scalars().all()

    Args:
        session: AsyncSession instance
        query_builder: Function that takes a list of items and returns a Select query
        items: List of items to use in IN clause
        batch_size: Number of items per batch (default: 5000)

    Returns:
        List of scalar values from all batches

    Example:
        talents = await batch_in_query_flat(
            session,
            lambda batch: select(Talent).where(Talent.talent_id.in_(batch)),
            talent_ids
        )
    """
    return await batch_in_query(
        session,
        query_builder,
        items,
        lambda result: result.scalars().all(),
        batch_size
    )


async def batch_in_query_map(
    session: AsyncSession,
    query_builder: Callable[[List[Any]], Select],
    items: List[Any],
    key_func: Callable[[Any], Any],
    value_func: Callable[[Any], Any] = lambda row: row,
    batch_size: int = BATCH_SIZE
) -> dict:
    """
    Execute a query with IN clause in batches, returning a dictionary.

    Convenience wrapper for building a map from query results.

    Args:
        session: AsyncSession instance
        query_builder: Function that takes a list of items and returns a Select query
        items: List of items to use in IN clause
        key_func: Function to extract key from each row
        value_func: Function to extract value from each row (default: row itself)
        batch_size: Number of items per batch (default: 5000)

    Returns:
        Dictionary mapping keys to values

    Example:
        id_map = await batch_in_query_map(
            session,
            lambda batch: select(Talent.talent_id, Talent.source_record_id)
                          .where(Talent.source_record_id.in_(batch)),
            source_ids,
            key_func=lambda row: row.source_record_id,
            value_func=lambda row: row.talent_id
        )
    """
    if not items:
        return {}

    result_map: dict = {}

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        query = query_builder(batch)
        result = await session.execute(query)
        for row in result.all():
            result_map[key_func(row)] = value_func(row)

    return result_map
