// Keycloak browser login (OIDC auth-code + PKCE), then the DR-0030 bridge: exchange the Keycloak
// token for an arvel bearer PAT that the bearer-guarded admin APIs accept. Dev defaults point at the
// local Keycloak; override with VITE_KEYCLOAK_URL / VITE_KEYCLOAK_CLIENT if needed.
import { token } from "./api";

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL ?? "http://localhost:8080/realms/arvel";
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT ?? "arvel-admin";
const VERIFIER_KEY = "kc_pkce_verifier";

function redirectUri(): string {
  return `${location.origin}/callback`;
}

function base64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomVerifier(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64url(bytes);
}

async function challengeFor(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64url(new Uint8Array(digest));
}

export async function startKeycloakLogin(): Promise<void> {
  const verifier = randomVerifier();
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    response_type: "code",
    scope: "openid",
    code_challenge: await challengeFor(verifier),
    code_challenge_method: "S256",
  });
  location.href = `${KEYCLOAK_URL}/protocol/openid-connect/auth?${params}`;
}

export async function completeKeycloakLogin(code: string): Promise<void> {
  const verifier = sessionStorage.getItem(VERIFIER_KEY) ?? "";
  sessionStorage.removeItem(VERIFIER_KEY);

  // 1. code → Keycloak access token (PKCE, public client, no secret)
  const tokenRes = await fetch(`${KEYCLOAK_URL}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code,
      redirect_uri: redirectUri(),
      code_verifier: verifier,
    }),
  });
  if (!tokenRes.ok) throw new Error("Keycloak token exchange failed");
  const { access_token } = (await tokenRes.json()) as { access_token: string };

  // 2. Keycloak token → arvel bearer PAT (DR-0030 bridge; syncs the mapped RBAC roles)
  const bridgeRes = await fetch("/api/admin/oidc/token", {
    method: "POST",
    headers: { Authorization: `Bearer ${access_token}`, Accept: "application/json" },
  });
  if (!bridgeRes.ok) throw new Error(`Bridge exchange failed (${bridgeRes.status})`);
  const { token: bearer } = (await bridgeRes.json()) as { token: string };
  token.set(bearer);
}
