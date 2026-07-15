
export interface AdminUserDetailOut {
  id: number;
  name: string;
  email: string;
  email_verified: boolean;
  roles: string[];
  orders_count: number;
  total_spent_cents: number;
  addresses_count?: number;
  avatar_url?: string | null;
}
