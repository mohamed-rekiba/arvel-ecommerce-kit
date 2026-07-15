
export interface AdminUserOut {
  id: number;
  name: string;
  email: string;
  email_verified: boolean;
  roles: string[];
  avatar_url?: string | null;
}
