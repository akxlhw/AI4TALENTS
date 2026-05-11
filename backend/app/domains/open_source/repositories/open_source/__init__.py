"""Open Source Repository - aggregated export."""
from app.domains.open_source.repositories.open_source.core import OpenSourceCoreRepository
from app.domains.open_source.repositories.open_source.advanced import OpenSourceAdvancedRepository


class OpenSourceRepository(OpenSourceCoreRepository, OpenSourceAdvancedRepository):
    """Repository for open-source talent database queries."""
    pass
