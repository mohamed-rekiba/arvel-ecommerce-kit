
export interface NotificationOut {
  id: string;
  type: string;
  message: string;
  read: boolean;
  created_at: string | null;
}
