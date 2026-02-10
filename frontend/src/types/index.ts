export interface Category {
  id: number;
  name: string;
  slug: string;
  color: string;
  icon: string | null;
  description: string | null;
  sort_order: number;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
}

export interface EventData {
  id: string;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  start_time: string | null;
  end_time: string | null;
  timezone: string | null;
  is_all_day: boolean;
  category_id: number | null;
  category: { id: number; name: string; slug: string; color: string; icon: string | null } | null;
  impact_level: number | null;
  popularity_score: number | null;
  country_code: string | null;
  region: string | null;
  is_recurring: boolean;
  recurrence_rule: string | null;
  data_source_id: number | null;
  external_id: string | null;
  source_url: string | null;
  image_url: string | null;
  created_by_user_id: string | null;
  is_approved: boolean;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description: string | null;
  start: string;
  end: string | null;
  allDay: boolean;
  color: string | null;
  category_id: number | null;
  category_name: string | null;
  impact_level: number | null;
  popularity_score: number | null;
  country_code: string | null;
  source_url: string | null;
  rrule: string | null;
}

export interface PaginatedEvents {
  items: EventData[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface DataSource {
  id: number;
  name: string;
  source_type: string;
  base_url: string | null;
  is_active: boolean;
  last_synced_at: string | null;
  sync_interval: number | null;
}

export interface EventCreateData {
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  start_time?: string;
  end_time?: string;
  timezone?: string;
  is_all_day?: boolean;
  category_id?: number;
  impact_level?: number;
  country_code?: string;
  region?: string;
  is_recurring?: boolean;
  recurrence_rule?: string;
  source_url?: string;
  image_url?: string;
  tag_ids?: number[];
}
