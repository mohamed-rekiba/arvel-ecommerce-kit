
/**
 * Moderation state of a product review.
 */
export type ReviewStatus = typeof ReviewStatus[keyof typeof ReviewStatus];


export const ReviewStatus = {
  pending: 'pending',
  approved: 'approved',
  rejected: 'rejected',
} as const;
