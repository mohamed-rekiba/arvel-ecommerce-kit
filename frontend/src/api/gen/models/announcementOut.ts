import type { CouponType } from './couponType';

export interface AnnouncementOut {
  code: string;
  type: CouponType;
  value: number;
}
