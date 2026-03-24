"""
API v1 router.
Aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, overview, countries, schools, talents, search, auth, permissions, audit, favorites, tech_element, talent_pool


api_router = APIRouter()

# Health endpoints
api_router.include_router(health.router)

# Authentication endpoints
api_router.include_router(auth.router)

# User & Permission management endpoints
api_router.include_router(permissions.router)

# Audit log endpoints
api_router.include_router(audit.router)

# Overview endpoints
api_router.include_router(overview.router)

# Countries endpoints
api_router.include_router(countries.router)

# Schools endpoints
api_router.include_router(schools.router)

# Talents endpoints
api_router.include_router(talents.router)

# Tech Element endpoints
api_router.include_router(tech_element.router)

# Talent Pool endpoints
api_router.include_router(talent_pool.router)

# Search endpoints
api_router.include_router(search.router)

# Favorites endpoints
api_router.include_router(favorites.router)
