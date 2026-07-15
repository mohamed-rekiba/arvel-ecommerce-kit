
export interface QueuedCookie {
  name: string;
  value: string;
  max_age?: number | null;
  path?: string;
  domain?: string | null;
  secure?: boolean | null;
  http_only?: boolean;
  same_site?: string;
}
