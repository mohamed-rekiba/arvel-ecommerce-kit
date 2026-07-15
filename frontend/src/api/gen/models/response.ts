import type { QueuedCookie } from './queuedCookie';
import type { ResponseHeaders } from './responseHeaders';

export interface Response {
  content?: unknown;
  status?: number;
  headers?: ResponseHeaders;
  cookies?: QueuedCookie[];
  forgotten_cookies?: string[];
}
