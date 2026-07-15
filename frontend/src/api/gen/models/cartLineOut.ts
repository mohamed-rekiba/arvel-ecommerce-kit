
export interface CartLineOut {
  id: number;
  product_variant_id: number;
  product_name: string;
  variant_name: string;
  image_url: string | null;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
}
