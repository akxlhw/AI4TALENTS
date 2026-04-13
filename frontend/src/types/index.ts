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
  research_interests?: string[]
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

// Tech Element - 技术要素
export interface TechElement {
  tech_element_id: number
  element_code: string
  element_name: string
  element_name_en?: string | null
  directions?: TechDirection[]
}

// Tech Direction - 技术方向
export interface TechDirection {
  tech_direction_id: number
  direction_code: string
  direction_name: string
  tech_element_id: number
}

// Search Talent Result - 搜索结果人才
export interface SearchTalent {
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
  topic_tags: string[]
  openalex_topics: string[]  // OpenAlex研究主题（具体研究方向）
}

// Search Filter Params - 搜索筛选参数
export interface SearchFilterParams {
  role_type?: string
  school_id?: number
  country_code?: string
  tech_element_id?: number
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

// Venue Binding - 技术要素与顶会顶刊的绑定
export interface VenueBinding {
  binding_id: number
  venue_id: number
  tech_element_id: number
  is_enabled: boolean
  venue?: VenueItem
  author_count?: number
  work_count?: number
  last_collect_at?: string
}

// Tech Element Collect - 技术要素采集配置
export interface TechElementCollect {
  tech_element_id: number
  element_code: string
  element_name: string
  element_name_en: string | null
  collect_sources: Array<{ id: string; name: string; type: string }> | null
  last_collect_at: string | null
  is_enabled: boolean
  venue_count: number
}

// Collect Task - 采集任务
export interface CollectTask {
  task_id: number
  task_code: string
  tech_element_id: number
  tech_element_name: string | null
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
  research_interests?: string
}

// JD Features - JD解析特征
export interface JDFeatures {
  skills: string[]
  experience: string
  research_areas: string[]
  role_type: string
  education_level?: string
}

// Match Config - 匹配配置
export interface MatchConfig {
  weights?: {
    skill?: number
    research?: number
    experience?: number
    education?: number
  }
  filters?: Record<string, unknown>
  limit?: number
}

// Match Result Item - 匹配结果项
export interface MatchResultItem {
  talent_id: number
  name: string
  title: string
  school_name: string
  overall_score: number
  skill_score: number
  research_score: number
  experience_score: number
  match_reasons: string[]
  highlight_skills: string[]
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

// Recommend Result Item - 推荐结果项
export interface RecommendResultItem {
  talent_id: number
  name: string
  title: string
  school_name: string
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
