"""
Venue service layer.
顶会顶刊配置业务逻辑层
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.venue import Venue, VenueTechBinding
from app.domains.academic.repositories.tech_domain_repository import TechDomainRepository
from app.domains.academic.repositories.venue_repository import VenueRepository, VenueTechBindingRepository
from app.domains.academic.schemas.venue import (
    VenueCreate,
    VenueTechBindingBatchCreate,
    VenueTechBindingCreate,
    VenueUpdate,
)


class VenueService:
    """Service for venue configuration operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.venue_repo = VenueRepository(session)
        self.binding_repo = VenueTechBindingRepository(session)
        self.tech_domain_repo = TechDomainRepository(session)

    async def create_venue(self, data: VenueCreate) -> Venue:
        """Create a new venue with validation."""
        # Check if code exists
        existing = await self.venue_repo.get_by_code(data.venue_code)
        if existing:
            raise ValueError("Venue code already exists")

        # Check if openalex_source_id exists
        if data.openalex_source_id:
            existing = await self.venue_repo.get_by_openalex_id(data.openalex_source_id)
            if existing:
                raise ValueError("OpenAlex Source ID already exists")

        venue = Venue(**data.model_dump())
        venue = await self.venue_repo.create(venue)
        await self.session.commit()
        return venue

    async def update_venue(self, venue_id: int, data: VenueUpdate) -> Venue:
        """Update venue with validation."""
        venue = await self.venue_repo.get_by_id(venue_id)
        if not venue:
            raise ValueError("Venue not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(venue, key, value)

        venue = await self.venue_repo.update(venue)
        await self.session.commit()
        return venue

    async def delete_venue(self, venue_id: int) -> bool:
        """Delete venue with binding check."""
        # Check if has bindings
        bindings = await self.binding_repo.get_by_venue(venue_id)
        if bindings:
            raise ValueError(
                f"Cannot delete venue with {len(bindings)} bindings. Delete bindings first."
            )

        success = await self.venue_repo.delete(venue_id)
        if success:
            await self.session.commit()
        return success

    async def create_binding(self, data: VenueTechBindingCreate) -> VenueTechBinding:
        """Create venue-tech domain binding with validation."""
        # Check venue exists
        venue = await self.venue_repo.get_by_id(data.venue_id)
        if not venue:
            raise ValueError("Venue not found")

        # Check tech domain exists
        tech_domain = await self.tech_domain_repo.get_domain_by_id(data.tech_domain_id)
        if not tech_domain:
            raise ValueError("Tech domain not found")

        # Check if binding already exists
        existing = await self.binding_repo.get_by_venue_and_tech(data.venue_id, data.tech_domain_id)
        if existing:
            raise ValueError("Binding already exists")

        binding = VenueTechBinding(**data.model_dump())
        binding = await self.binding_repo.create(binding)
        await self.session.commit()
        return binding

    async def update_binding(self, binding_id: int, data: dict) -> VenueTechBinding:
        """Update binding."""
        binding = await self.binding_repo.get_by_id(binding_id)
        if not binding:
            raise ValueError("Binding not found")

        for key, value in data.items():
            setattr(binding, key, value)

        binding = await self.binding_repo.update(binding)
        await self.session.commit()
        return binding

    async def delete_binding(self, binding_id: int) -> bool:
        """Delete binding."""
        success = await self.binding_repo.delete(binding_id)
        if success:
            await self.session.commit()
        return success

    async def batch_update_bindings(self, data: VenueTechBindingBatchCreate) -> dict:
        """
        Batch update tech domain bindings.

        Enables specified venue_ids, disables others for the tech domain.
        Also updates TechDomain.collect_sources field.
        """
        # Check tech domain exists
        tech_domain = await self.tech_domain_repo.get_domain_by_id(data.tech_domain_id)
        if not tech_domain:
            raise ValueError("Tech domain not found")

        # Get all bindings for this tech domain
        all_bindings = await self.binding_repo.get_by_tech_domain(data.tech_domain_id)
        selected_venue_ids = set(data.venue_ids)

        # Update binding status
        updated_bindings = []
        for binding in all_bindings:
            new_enabled = binding.venue_id in selected_venue_ids
            if binding.is_enabled != new_enabled:
                binding.is_enabled = new_enabled
                updated_bindings.append(binding)

        await self.session.commit()

        # Update TechDomain.collect_sources field
        enabled_bindings = await self.binding_repo.get_list_with_venue(
            data.tech_domain_id, is_enabled=True
        )
        collect_sources = [
            {
                "id": b.venue.openalex_source_id or b.venue.venue_code,
                "name": b.venue.venue_name,
                "type": b.venue.venue_type,
            }
            for b in enabled_bindings
            if b.venue
        ]
        tech_domain.collect_sources = collect_sources
        await self.session.commit()

        # Return stats
        enabled_count = len([b for b in all_bindings if b.is_enabled])
        return {
            "total_bindings": len(all_bindings),
            "enabled_bindings": enabled_count,
            "updated_count": len(updated_bindings),
        }

    async def migrate_collect_sources(self, tech_domain_id: int, dry_run: bool = False) -> dict:
        """
        Migrate TechDomain.collect_sources JSON to Venue table.

        Creates venues and bindings from collect_sources data.
        """
        tech_domain = await self.tech_domain_repo.get_domain_by_id(tech_domain_id)
        if not tech_domain:
            raise ValueError("Tech domain not found")

        collect_sources = tech_domain.collect_sources or []
        if not collect_sources:
            return {
                "tech_domain_id": tech_domain_id,
                "tech_domain_name": tech_domain.domain_name,
                "venues_found": 0,
                "venues_created": 0,
                "bindings_created": 0,
                "venues": [],
                "message": "No collect_sources to migrate",
            }

        venues_created = 0
        bindings_created = 0
        venue_infos = []

        for source in collect_sources:
            source_id = source.get("id")
            source_name = source.get("name", source_id)
            source_type = source.get("type", "conference")

            if not source_id:
                continue

            # Check if venue exists
            venue = await self.venue_repo.get_by_openalex_id(source_id)
            if not venue:
                venue = await self.venue_repo.get_by_code(source_id)

            if not venue and not dry_run:
                # Create new venue
                venue = Venue(
                    venue_code=source_id,
                    venue_name=source_name,
                    openalex_source_id=source_id,
                    venue_type=source_type,
                    is_enabled=True,
                )
                venue = await self.venue_repo.create(venue)
                venues_created += 1

            if venue:
                venue_infos.append(
                    {
                        "venue_id": venue.venue_id,
                        "venue_code": venue.venue_code,
                        "venue_name": venue.venue_name,
                        "openalex_source_id": venue.openalex_source_id,
                        "is_new": venues_created > 0,
                    }
                )

                # Create binding if not exists
                if not dry_run:
                    existing_binding = await self.binding_repo.get_by_venue_and_tech(
                        venue.venue_id, tech_domain_id
                    )
                    if not existing_binding:
                        binding = VenueTechBinding(
                            venue_id=venue.venue_id,
                            tech_domain_id=tech_domain_id,
                            priority=0,
                            is_enabled=True,
                        )
                        await self.binding_repo.create(binding)
                        bindings_created += 1

        if not dry_run:
            await self.session.commit()

        return {
            "tech_domain_id": tech_domain_id,
            "tech_domain_name": tech_domain.domain_name,
            "venues_found": len(collect_sources),
            "venues_created": venues_created,
            "bindings_created": bindings_created,
            "venues": venue_infos,
            "message": f"Migration {'simulated' if dry_run else 'completed'}: {venues_created} venues, {bindings_created} bindings",
        }
