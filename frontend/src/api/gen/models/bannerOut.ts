
export interface BannerOut {
  id: number;
  title: string;
  subtitle: string | null;
  chip: string | null;
  cta_label: string | null;
  cta_to: string;
  image_url: string | null;
  mobile_image_url: string | null;
}
