import { apiClient } from './client'

export const academicApi = {
  schools: {
    list: (params?: { country_code?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/schools', { params }),
    get: (id: number) => apiClient.get(`/schools/${id}`),
    getTalents: (id: number, params?: { role_type?: string; page?: number }) =>
      apiClient.get(`/schools/${id}/talents`, { params }),
  },

  talents: {
    list: (params?: { school_id?: number; country_code?: string; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/talents', { params }),
    get: (id: number) => apiClient.get(`/talents/${id}`),
    getWorks: (id: number, limit?: number) =>
      apiClient.get(`/talents/${id}/works`, { params: { limit } }),
    export: (talentIds: number[], format: 'csv' | 'xlsx' = 'csv') =>
      apiClient.post(`/talents/export?format=${format}`, null, {
        params: { talent_ids: talentIds },
        responseType: 'blob',
      }),
    compare: (talentIds: number[]) =>
      apiClient.post('/talents/compare', null, {
        params: { talent_ids: talentIds },
      }),
    getCollaborations: (id: number, limit?: number) =>
      apiClient.get(`/talents/${id}/collaborations`, { params: { limit } }),
    syncCollaborations: (talentId?: number) =>
      apiClient.post('/talents/collaborations/sync', null, { params: { talent_id: talentId } }),
    getCollaborationSyncStatus: () =>
      apiClient.get('/talents/collaborations/status'),
    getGenealogy: (id: number, params?: { depth?: number; min_confidence?: number; relationship_type?: string; tier_filter?: string }) =>
      apiClient.get(`/talents/${id}/genealogy`, { params }),
    syncGenealogy: () =>
      apiClient.post('/talents/genealogy/sync'),
    getGenealogySyncStatus: () =>
      apiClient.get('/talents/genealogy/sync-status'),
    getInfluenceRanking: (params?: { tier?: string; limit?: number }) =>
      apiClient.get('/talents/genealogy/influence-ranking', { params }),
  },

  search: {
    talents: (params: { q: string; page?: number; page_size?: number }) =>
      apiClient.get('/search/talents', { params }),
  },

  favorites: {
    add: (talentId: number, notes?: string) =>
      apiClient.post('/favorites', { talent_id: talentId, notes }),
    list: (params?: { page?: number; page_size?: number; role_type?: string; keyword?: string }) =>
      apiClient.get('/favorites', { params }),
    getIds: () =>
      apiClient.get('/favorites/ids'),
    check: (talentId: number) =>
      apiClient.get(`/favorites/${talentId}/check`),
    update: (talentId: number, notes?: string) =>
      apiClient.put(`/favorites/${talentId}`, { notes }),
    remove: (talentId: number) =>
      apiClient.delete(`/favorites/${talentId}`),
  },

  techDomains: {
    list: () =>
      apiClient.get('/tech-domains'),
    get: (id: number) =>
      apiClient.get(`/tech-domains/${id}`),
    getSummary: () =>
      apiClient.get('/tech-domains/summary'),
    getOverallStats: () =>
      apiClient.get('/tech-domains/overall-stats'),
    getOverallCountries: () =>
      apiClient.get('/tech-domains/overall-countries'),
    getOverallSchools: (params?: { page?: number; page_size?: number }) =>
      apiClient.get('/tech-domains/overall-schools', { params }),
    getOverallTalents: (params?: { country_code?: string; school_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/tech-domains/overall-talents', { params }),
    getStats: (id: number) =>
      apiClient.get(`/tech-domains/${id}/stats`),
    getCountries: (id: number, directionId?: number) =>
      apiClient.get(`/tech-domains/${id}/countries`, { params: { direction_id: directionId } }),
    getSchools: (id: number, params?: { direction_id?: number; country_code?: string; page?: number; page_size?: number }) =>
      apiClient.get(`/tech-domains/${id}/schools`, { params }),
    getTalents: (id: number, params?: { direction_id?: number; country_code?: string; school_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get(`/tech-domains/${id}/talents`, { params }),
  },

  talentPools: {
    list: () =>
      apiClient.get('/talent-pools'),
    get: (id: number) =>
      apiClient.get(`/talent-pools/${id}`),
    create: (data: { pool_name: string; pool_type?: string; scope_desc?: string }) =>
      apiClient.post('/talent-pools', data),
    update: (id: number, data: { pool_name?: string; scope_desc?: string; pool_status?: string }) =>
      apiClient.put(`/talent-pools/${id}`, data),
    delete: (id: number) =>
      apiClient.delete(`/talent-pools/${id}`),
    addMember: (poolId: number, talentId: number, notes?: string) =>
      apiClient.post(`/talent-pools/${poolId}/members`, { talent_id: talentId, notes }),
    removeMember: (poolId: number, talentId: number) =>
      apiClient.delete(`/talent-pools/${poolId}/members/${talentId}`),
    getMembers: (poolId: number, params?: { page?: number; page_size?: number }) =>
      apiClient.get(`/talent-pools/${poolId}/members`, { params }),
    updateFollowupStatus: (talentId: number, status: string) =>
      apiClient.put(`/talent-pools/favorites/${talentId}/followup`, { followup_status: status }),
    getFollowupStatuses: () =>
      apiClient.get('/talent-pools/followup-statuses'),
  },

  collect: {
    listTechDomains: () =>
      apiClient.get('/collect/tech-domains'),
    listTasks: (params?: { status?: string; tech_domain_id?: number; page?: number; page_size?: number }) =>
      apiClient.get('/collect/tasks', { params }),
    getTask: (taskId: number) =>
      apiClient.get(`/collect/tasks/${taskId}`),
    triggerTask: (data: { tech_domain_id: number; start_year?: number; end_year?: number | null }) =>
      apiClient.post('/collect/tasks', data),
    cancelTask: (taskId: number) =>
      apiClient.post(`/collect/tasks/${taskId}/cancel`),
    deleteTask: (taskId: number) =>
      apiClient.delete(`/collect/tasks/${taskId}`),
    getActiveTasks: () =>
      apiClient.get('/collect/tasks/active'),
    getTaskStatuses: () =>
      apiClient.get('/collect/options/task-statuses'),
    getYearOptions: () =>
      apiClient.get('/collect/options/years'),
  },

  dataVersion: {
    listVersions: (params?: { is_published?: boolean; page?: number; page_size?: number }) =>
      apiClient.get('/data-version/versions', { params }),
    getActiveVersion: () =>
      apiClient.get('/data-version/versions/active'),
    getVersion: (versionId: number) =>
      apiClient.get(`/data-version/versions/${versionId}`),
    createVersion: (data: { version_code: string; version_name: string; version_type?: string; base_version_id?: number; source_task_id?: number; description?: string }) =>
      apiClient.post('/data-version/versions', data),
    publishVersion: (versionId: number, notes?: string) =>
      apiClient.post(`/data-version/versions/${versionId}/publish`, { notes }),
    listPublishRecords: (versionId?: number) =>
      apiClient.get('/data-version/publish-records', { params: { version_id: versionId } }),
    listCorrections: (params?: { target_type?: string; status?: string; page?: number; page_size?: number }) =>
      apiClient.get('/data-version/corrections', { params }),
    createCorrection: (data: { target_type: string; target_id: number; field_name: string; original_value?: string; corrected_value?: string; correction_type?: string; reason?: string; source?: string }) =>
      apiClient.post('/data-version/corrections', data),
    revertCorrection: (correctionId: number) =>
      apiClient.post(`/data-version/corrections/${correctionId}/revert`),
    getQualitySummary: (versionId?: number) =>
      apiClient.get('/data-version/quality/summary', { params: { version_id: versionId } }),
    getQualityMetrics: () =>
      apiClient.get('/data-version/quality/metrics'),
  },

  venues: {
    list: (params?: { venue_type?: string; is_enabled?: boolean; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/venues', { params }),
    get: (venueId: number) =>
      apiClient.get(`/venues/${venueId}`),
    getTechDomainBindings: (techDomainId: number, isEnabled?: boolean) =>
      apiClient.get(`/venues/tech-domains/${techDomainId}/bindings`, { params: { is_enabled: isEnabled } }),
    batchCreateBindings: (techDomainId: number, venueIds: number[]) =>
      apiClient.post('/venues/bindings/batch', { tech_domain_id: techDomainId, venue_ids: venueIds }),
    deleteBinding: (bindingId: number) =>
      apiClient.delete(`/venues/bindings/${bindingId}`),
    updateBindings: (techDomainId: number, venueIds: number[]) =>
      apiClient.post('/venues/bindings/batch', { tech_domain_id: techDomainId, venue_ids: venueIds }),
  },

  homepage: {
    getHighlights: () =>
      apiClient.get('/homepage/highlights'),
  },

  enhancedSearch: {
    search: (params: {
      q: string
      mode?: 'keyword' | 'fulltext' | 'semantic' | 'hybrid'
      fuzzy?: boolean
      role_type?: string
      school_id?: number
      min_citations?: number
      min_works?: number
      country_code?: string
      tech_domain_id?: number
      page?: number
      page_size?: number
    }) => apiClient.get('/search/v2/talents', { params }),
  },

  jdMatch: {
    parse: (jdText: string) =>
      apiClient.post('/jd-match/parse', { jd_text: jdText }),
    match: (data: {
      jd_text: string
      config?: {
        weights?: { skill?: number; research?: number; experience?: number; education?: number }
        filters?: Record<string, unknown>
        limit?: number
      }
    }) => apiClient.post('/jd-match/match', data),
    getSession: (sessionId: number) =>
      apiClient.get(`/jd-match/sessions/${sessionId}`),
  },

  recommend: {
    getRecommendations: (data: {
      reference_talent_ids: number[]
      limit?: number
      filters?: Record<string, unknown>
    }) => apiClient.post('/recommend/talents', data),
    getSimilar: (talentId: number, limit?: number) =>
      apiClient.get(`/recommend/talents/${talentId}/similar`, { params: { limit } }),
  },

  embeddings: {
    getStatus: () =>
      apiClient.get('/embeddings/status'),
    getProgress: () =>
      apiClient.get('/embeddings/progress'),
    generate: (force?: boolean, batchSize?: number) =>
      apiClient.post('/embeddings/generate', null, { params: { force, batch_size: batchSize } }),
    cancel: () =>
      apiClient.post('/embeddings/cancel'),
  },
}
