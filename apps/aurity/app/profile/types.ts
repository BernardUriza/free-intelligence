/**
 * Profile page types
 */

export interface DiskUsage {
  used: string;
  total: string;
  percent: number;
}

export interface ClearMemoryResponse {
  message: string;
}

export interface ProfileUser {
  sub?: string;
  name?: string;
  email?: string;
  email_verified?: boolean;
  nickname?: string;
  picture?: string;
  updated_at?: string;
  roles?: string[];
}
