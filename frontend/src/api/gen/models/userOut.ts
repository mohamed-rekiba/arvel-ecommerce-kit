
export interface UserOut {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  email_verified: boolean;
  avatar_url: string | null;
  locale: string;
}
