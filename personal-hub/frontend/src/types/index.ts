// User types
export interface User {
  id: number;
  email: string;
  name: string;
  avatar_url: string | null;
  roles: string[];
  is_admin: boolean;
  is_active: boolean;
  last_login: string | null;
}

export interface UserListItem {
  id: number;
  email: string;
  name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  roles: Role[];
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface Role {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Module types
export interface Module {
  id: number;
  module_id: string;
  name: string;
  description: string | null;
  version: string;
  tags: string[];
  icon: string | null;
  nav_order: number;
  ui_path: string | null;
  api_base_path: string | null;
  health_path: string | null;
  permissions_required: string[];
  services: Record<string, string>;
  is_enabled: boolean;
  status: ModuleStatus;
  health_message: string | null;
  last_health_check: string | null;
}

export type ModuleStatus = "unknown" | "healthy" | "unhealthy" | "starting" | "stopped" | "error";

export interface ModuleListResponse {
  items: Module[];
  total: number;
}

// Audit log types
export interface AuditLog {
  id: number;
  action: string;
  user_id: number | null;
  user_email: string | null;
  resource_type: string | null;
  resource_id: string | null;
  description: string | null;
  details: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Profile types
export interface Profile {
  displayName: string;
  tagline: string;
  bio: string;
  avatarUrl: string;
  location?: string;
  email?: string;
}

export interface Theme {
  accentColor: string;
  primaryGradient: string;
  secondaryGradient?: string;
  darkMode: boolean;
}

export interface SocialLinks {
  github?: string;
  linkedin?: string;
  twitter?: string;
  website?: string;
  [key: string]: string | undefined;
}

export interface Skill {
  category: string;
  items: SkillItem[];
}

export interface SkillItem {
  name: string;
  level: number;
}

export interface FeaturedProject {
  name: string;
  description: string;
  tags: string[];
  link: string;
}

export interface ProfileConfig {
  profile: Profile;
  theme: Theme;
  socialLinks: SocialLinks;
  skills: Skill[];
  featuredProjects: FeaturedProject[];
  seo?: {
    title: string;
    description: string;
    keywords: string[];
  };
}

// Admin stats
export interface AdminStats {
  total_users: number;
  active_users: number;
  total_modules: number;
  enabled_modules: number;
  recent_logins: number;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// API Response types
export interface ApiError {
  detail: string;
  status?: number;
}
