
export interface OrderLineOut {
  product_variant_id: number;
  product_name: string;
  product_slug: string | null;
  variant_name: string;
  image_url: string | null;
  quantity: number;
  unit_price_cents: number;
}
