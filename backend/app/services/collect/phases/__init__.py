"""Collection phase handlers.

Each handler encapsulates a single phase of the collection pipeline,
keeping the orchestrator focused purely on coordination.
"""

from app.services.collect.phases.base import PhaseContext, PhaseHandler
from app.services.collect.phases.phase_1_collect import PhaseCollectHandler
from app.services.collect.phases.phase_2_fetch_authors import PhaseFetchAuthorsHandler
from app.services.collect.phases.phase_3_fetch_institutions import PhaseFetchInstitutionsHandler
from app.services.collect.phases.phase_4_normalize_schools import PhaseNormalizeSchoolsHandler
from app.services.collect.phases.phase_5_normalize_authors import PhaseNormalizeAuthorsHandler
from app.services.collect.phases.phase_6_tech_belong import PhaseTechBelongHandler
from app.services.collect.phases.phase_7_sync_serving import PhaseSyncServingHandler
from app.services.collect.phases.phase_8_fetch_works import PhaseFetchWorksHandler
from app.services.collect.phases.phase_9_topic_tags import PhaseTopicTagsHandler
from app.services.collect.phases.phase_10_school_stats import PhaseSchoolStatsHandler
from app.services.collect.phases.phase_11_build_stats import PhaseBuildStatsHandler

__all__ = [
    "PhaseContext",
    "PhaseHandler",
    "PhaseCollectHandler",
    "PhaseFetchAuthorsHandler",
    "PhaseFetchInstitutionsHandler",
    "PhaseNormalizeSchoolsHandler",
    "PhaseNormalizeAuthorsHandler",
    "PhaseTechBelongHandler",
    "PhaseSyncServingHandler",
    "PhaseFetchWorksHandler",
    "PhaseTopicTagsHandler",
    "PhaseSchoolStatsHandler",
    "PhaseBuildStatsHandler",
]
