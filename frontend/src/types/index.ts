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
  user_id: string
  username: string
  email: string
  role: 'user' | 'admin' | 'super_admin'
  created_at: string
}

export interface UserPermission {
  user_id: string
  accessible_schools: string[]
}
