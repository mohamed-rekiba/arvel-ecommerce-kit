
export interface AdminDealOut {
  id: number;
  product_id: number;
  product_name: string;
  percent_off: number;
  starts_at: string | null;
  ends_at: string | null;
  active: boolean;
  live: boolean;
}
