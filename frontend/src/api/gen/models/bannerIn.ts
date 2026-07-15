import type { BannerInTranslations } from './bannerInTranslations';

export interface BannerIn {
  translations: BannerInTranslations;
  cta_to?: string;
  sort?: number;
  active?: boolean;
}
