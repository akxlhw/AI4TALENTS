/**
 * API response types
 */

// Common types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Health check
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  service: {
    name: string
    version: string
    environment: string
  }
  database: {
    status: string
  }
}

// Overview statistics
export interface OverviewStats {
  universities_count: number
  professors_count: number
  students_count: number
  updated_at: string
}

// Country
export interface Country {
  country_code: string
  country_name: string
  schools_count: number
}

// School
export interface School {
  school_id: string
  name: string
  country_code: string
  country_name: string
  description?: string
  professors_count: number
  students_count: number
  total_talents: number
}

export interface SchoolDetail extends School {
  homepage_url?: string
  created_at: string
  updated_at: string
}

// Talent
export interface Talent {
  talent_id: string
  name: string
  role_type: 'professor' | 'student' | 'graduate' | 'unknown'
  role_display: string
  school_id: string
  school_name: string
  research_areas: string[]
  works_count: number
  cited_by_count: number
  last_active_year?: number
}

export interface TalentDetail extends Talent {
  orcid?: string
  description?: string
  representative_works: Work[]
  collaborations: Collaboration[]
  created_at: string
  updated_at: string
}

// Work (Publication)
export interface Work {
  work_id: string
  title: string
  publication_year?: number
  venue?: string
  cited_by_count: number
}

// Collaboration
export interface Collaboration {
  collaborator_id: string
  collaborator_name: string
  collaboration_count: number
}

// User & Permissions
export interface User {
  user_id: number
  username: string
  email: string
  role: string
  display_name: string | null
  department: string | null
}

export interface UserPermission {
  user_id: string
  accessible_schools: string[]
}

// ============================================
// v1.1 新增类型定义
// ============================================

// Tech Domain - 技术领域
export interface TechDomain {
  tech_domain_id: number
  domain_code: string
  domain_name: string
  domain_name_en?: string | null
  directions?: TechDirection[]
}

// Tech Direction - 技术方向
export interface TechDirection {
  tech_direction_id: number
  direction_code: string
  direction_name: string
  tech_domain_id: number
}

// Hot Research Topic - 热门研究方向（首页展示）
export interface HotResearchTopic {
  topic_name: string
  talent_count: number
}

// Search Talent Result - 搜索结果人才
export interface SearchTalent {
  talent_id: number
  name: string
  name_en: string | null
  role_type: string
  school_id: number | null
  school_name: string | null
  // Primary institutions (v1.5)
  education_school_id: number | null
  education_school_name: string | null
  company_school_id: number | null
  company_school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  topic_tags: string[]
  openalex_topics: string[]  // OpenAlex研究主题（具体研究方向）
  similarity_score?: number  // 语义搜索相似度分数
  match_sources?: string[]   // 匹配来源：fulltext, semantic_research, semantic_papers
}

// Search Filter Params - 搜索筛选参数
export interface SearchFilterParams {
  role_type?: string
  school_id?: number
  country_code?: string
  tech_domain_id?: number
  tech_direction_id?: number
  min_works?: number
  min_citations?: number
  is_graduated?: string
  confirm_status?: string
  keyword?: string
}

// Favorite Talent - 收藏的人才
export interface FavoriteTalent {
  favorite_id: number
  talent_id: number
  name: string
  name_en: string | null
  role_type: string
  school_id: number | null
  school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  notes: string | null
  followup_status: string
  created_at: string
}

// Talent Pool - 人才池
export interface TalentPool {
  pool_id: number
  pool_name: string
  pool_type: string
  owner_user_id: number
  scope_desc: string | null
  pool_status: string
  member_count: number
  created_at: string
}

// Followup Status - 跟进状态
export interface FollowupStatus {
  value: string
  label: string
}

// ============================================
// 采集配置相关类型
// ============================================

// Venue Item - 顶会顶刊
export interface VenueItem {
  venue_id: number
  venue_code: string
  venue_name: string
  venue_name_en: string | null
  venue_type: 'conference' | 'journal' | 'workshop'
  openalex_source_id: string | null
  is_enabled: boolean
}

// Venue Binding - 技术领域与顶会顶刊的绑定
export interface VenueBinding {
  binding_id: number
  venue_id: number
  tech_domain_id: number
  is_enabled: boolean
  venue?: VenueItem
  author_count?: number
  work_count?: number
  last_collect_at?: string
}

// Tech Domain Collect - 技术领域采集配置
export interface TechDomainCollect {
  tech_domain_id: number
  domain_code: string
  domain_name: string
  domain_name_en: string | null
  collect_sources: Array<{ id: string; name: string; type: string }> | null
  last_collect_at: string | null
  is_enabled: boolean
  venue_count: number
}

// Collect Task - 采集任务
export interface CollectTask {
  task_id: number
  task_code: string
  tech_domain_id: number
  tech_domain_name: string | null
  start_year: number
  end_year: number | null  // null 表示至今
  triggered_by: number | null
  triggered_at: string
  status: string
  progress_percent: number
  current_step: string | null
  total_records: number
  processed_records: number
  success_records: number
  failed_records: number
  skipped_records: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  error_details: unknown
  result_summary: {
    total_works?: number
    total_authors?: number
    normalized_authors?: number
    normalized_schools?: number
    synced_authors?: number
    created_talents?: number
    updated_talents?: number
    created_tech_tags?: number
    total_duration?: string
    venue_details?: Array<{
      venue_id: number
      venue_name: string
      status: string
      fetched: number
      saved: number
      duration: string
      error?: string
    }>
  } | null
  execution_logs: Array<{ timestamp: string; level: string; message: string; details?: unknown }> | null
  venue_snapshot: Array<{ id: string; name: string; type: string }> | null  // 创建时的顶会顶刊快照
  created_at: string
}

// ============================================
// 通用选项类型
// ============================================

// Dropdown Option - 下拉选项
export interface DropdownOption {
  value: number | string
  label: string
}

// Task Status Config - 任务状态配置
export interface TaskStatusConfig {
  label: string
  color: string
  status: 'success' | 'processing' | 'error' | 'default' | 'warning'
}

// Venue Type Config - 顶会顶刊类型配置
export interface VenueTypeConfig {
  label: string
  color: string
}

// ============================================
// v1.4 新增类型定义 - 智能推荐与岗位匹配
// ============================================

// Search Mode - 搜索模式
export type SearchMode = 'keyword' | 'fulltext' | 'semantic' | 'hybrid'

// Enhanced Search Result - 增强搜索结果
export interface EnhancedSearchResult extends SearchTalent {
  similarity_score?: number
}

// JD Features - JD解析特征 (v1.4.1: 简化为只有 research_areas)
export interface JDFeatures {
  research_areas: string[]
}

// Match Config - 匹配配置
export interface MatchConfig {
  weights?: {
    research?: number
  }
  filters?: Record<string, unknown>
  limit?: number
}

// Match Result Item - 匹配结果项 (v1.4.1: 简化, v1.5.0: 添加院校机构字段)
export interface MatchResultItem {
  talent_id: number
  name: string
  title: string
  school_name: string
  education_school_name: string | null
  company_school_name: string | null
  overall_score: number
  research_score: number
  match_reasons: string[]
}

// Match Response - 匹配响应
export interface MatchResponse {
  session_id: number
  total: number
  items: MatchResultItem[]
  took_ms: number
}

// Recommend Mode - 推荐模式 (仅支持相似推荐)
export type RecommendMode = 'similar'

// Recommend Result Item - 推荐结果项 (v1.5.0: 添加院校机构字段)
export interface RecommendResultItem {
  talent_id: number
  name: string
  title: string
  school_name: string
  education_school_name: string | null
  company_school_name: string | null
  similarity_score: number
  reasons: string[]
}

// Recommend Response - 推荐响应
export interface RecommendResponse {
  reference_talents: number[]
  total: number
  items: RecommendResultItem[]
  mode: string
  took_ms: number
}

// ============================================
// v2.0 新增类型定义 - 开源人才库
// ============================================

export interface OSDeveloper {
  developer_id: number
  github_login: string
  name?: string
  bio?: string
  location?: string
  company?: string
  avatar_url?: string
  total_stars_received: number
  primary_languages: string[]
  tech_tags: string[]
  is_visible: boolean
}

export interface OSDeveloperDetail extends OSDeveloper {
  github_id?: number
  blog_url?: string
  email?: string
  followers_count: number
  following_count: number
  public_repos_count: number
  total_forks_received: number
  repositories: OSRepository[]
  language_skills: OSLanguageSkill[]
  contributions: OSContribution[]
  similar_developers: OSDeveloper[]
}

export interface OSRepository {
  repo_id: number
  github_repo_id?: number
  full_name: string
  name: string
  language?: string
  stars_count: number
  forks_count: number
  topics: string[]
  is_fork: boolean
}

export interface OSContribution {
  contribution_id: number
  repo_id: number
  repo_full_name: string
  commits_count: number
  prs_count: number
  issues_count: number
  code_reviews_count: number
  is_owner: boolean
  is_maintainer: boolean
  is_committer: boolean
}

export interface OSLanguageSkill {
  skill_id: number
  language: string
  repo_count: number
  total_commits: number
  proficiency_score: number
}

export interface OSRepoConfig {
  repo_config_id: number
  repo_full_name: string
  display_name?: string
  description?: string
  tech_element: string
  tech_direction_id?: number
  language?: string
  stars_count: number
  is_active: boolean
  collect_enabled: boolean
  notes?: string
  created_at: string
  updated_at: string
}

export interface OSCollectTask {
  task_id: number
  task_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress_percent: number
  current_step?: string
  total_records: number
  processed_records: number
  config_json?: Record<string, unknown>
  error_message?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface OSStats {
  total_developers: number
  total_repositories: number
  total_organizations: number
  active_developers_30d: number
  language_distribution: Record<string, number>
  tech_element_distribution: Record<string, number>
}

export interface OSSearchQuery {
  q?: string
  tech_elements?: string[]
  languages?: string[]
  location?: string
  company?: string
  min_stars?: number
  sort_by?: string
  mode?: 'keyword' | 'semantic' | 'hybrid'
  page?: number
  page_size?: number
}
