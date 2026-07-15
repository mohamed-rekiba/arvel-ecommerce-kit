import type { Translate } from './translate';

export interface CategoryOut {
  id: number;
  slug: string;
  translation: Translate;
  image_url?: string | null;
}
