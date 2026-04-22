"""
API v1 router.
Aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    collect,
    countries,
    data_version,
    embeddings,
    favorites,
    health,
    homepage,
    jd_match,
    metrics,
    overview,
    permissions,
    recommend,
    schools,
    search,
    system_config,
    talent_pool,
    talents,
    tech_domain,
    venue,
)

api_router = APIRouter()

# Health endpoints
api_router.include_router(health.router)

# Metrics endpoint
api_router.include_router(metrics.router)

# Authentication endpoints
api_router.include_router(auth.router)

# User & Permission management endpoints
api_router.include_router(permissions.router)

# Audit log endpoints
api_router.include_router(audit.router)

# Overview endpoints
api_router.include_router(overview.router)

# Homepage endpoints
api_router.include_router(homepage.router)

# Countries endpoints
api_router.include_router(countries.router)

# Schools endpoints
api_router.include_router(schools.router)

# Talents endpoints
api_router.include_router(talents.router)

# Tech Domain endpoints
api_router.include_router(tech_domain.router)

# Talent Pool endpoints
api_router.include_router(talent_pool.router)

# Search endpoints
api_router.include_router(search.router)

# Favorites endpoints
api_router.include_router(favorites.router)

# Collect configuration endpoints
api_router.include_router(collect.router)

# Venue configuration endpoints
api_router.include_router(venue.router)

# System configuration endpoints
api_router.include_router(system_config.router)

# Embeddings endpoints
api_router.include_router(embeddings.router)

# Data version management endpoints
api_router.include_router(data_version.router)

# JD Match endpoints (v1.4)
api_router.include_router(jd_match.router)

# Recommend endpoints (v1.4)
api_router.include_router(recommend.router)
