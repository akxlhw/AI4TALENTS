"""
Academic Domain — Public Service exports.

Endpoints should ONLY import from specific service modules listed below
or from this package for well-known services.

Allowed for Endpoint use:
  - talent_service.TalentService
  - search.search_service.SearchService
  - venue_service.VenueService
  - collect_service.CollectService
  - recommend.recommend_service.RecommendService
  - jd_match.jd_match_service.JDMatchService
  - collaboration_service.CollaborationService

INTERNAL ONLY — must NOT be imported by Endpoints:
  - embedding.embedding_service.EmbeddingService
  - sync.*
  - normalizers.*
  - collect.orchestrator.CollectionOrchestrator
  - openalex_client.OpenAlexClient
"""
