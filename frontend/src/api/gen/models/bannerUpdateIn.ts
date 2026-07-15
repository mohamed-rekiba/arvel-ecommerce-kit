import type { BannerUpdateInTranslations } from './bannerUpdateInTranslations';

export interface BannerUpdateIn {
  translations?: BannerUpdateInTranslations;
  cta_to?: string | null;
  sort?: number | null;
  active?: boolean | null;
}
