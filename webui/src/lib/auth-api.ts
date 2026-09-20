// Auth API client for Keycloak-hosted signup + forgot-password flows.
//
// The web UI delegates registration and password reset to Keycloak's hosted
// pages (see Phase 0.4/0.5). The backend only exposes:
//   GET  /api/v1/auth/config   -> public Keycloak connection info (no secrets)
//   POST /api/v1/auth/exchange -> redeem a Keycloak auth code for tokens
//
// After Keycloak completes a flow it redirects back here with ?code=..., and we
// redeem that code server-side so the confidential client secret never reaches
// the browser.

export interface AuthConfig {
  kcUrl: string;
  realm: string;
  clientId: string;
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const authApi = {
  // Public Keycloak connection info — used to build hosted-flow URLs.
  getConfig: async (): Promise<AuthConfig> => {
    return getJson<AuthConfig>("/api/v1/auth/config");
  },

  // Build the Keycloak hosted-registration URL (used by signup).
  getRegisterUrl: async (): Promise<string> => {
    const cfg = await authApi.getConfig();
    return (
      `${cfg.kcUrl}/realms/${cfg.realm}` +
      `/protocol/openid-connect/auth` +
      `?client_id=${cfg.clientId}` +
      "&response_type=code" +
      "&kc_action=register"
    );
  },

  // Build the Keycloak hosted forgot-password URL (used by forgot-password).
  getForgotPasswordUrl: async (): Promise<string> => {
    const cfg = await authApi.getConfig();
    return (
      `${cfg.kcUrl}/realms/${cfg.realm}` +
      `/protocol/openid-connect/auth` +
      `?client_id=${cfg.clientId}` +
      "&response_type=code" +
      "&kc_action=forgotPassword"
    );
  },

  // Redeem a Keycloak auth code for tokens (server-side, keeps secret safe).
  exchange: async (code: string): Promise<{ token: string; user: Record<string, unknown> }> => {
    const res = await fetch("/api/v1/auth/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Exchange failed" }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return (await res.json()) as { token: string; user: Record<string, unknown> };
  },

  // ── Local email/password flows (Phase 0.4/0.5) ──────────────────────

  // Sign up with email + password; backend sends a verification OTP.
  signupLocal: async (email: string, password: string) => {
    const res = await fetch("/api/v1/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Signup failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return (await res.json()) as { status: string; email: string; token?: string };
  },

  // Verify the OTP after signup (completes account setup).
  verifyOtpLocal: async (token: string, otp: string) => {
    const res = await fetch("/api/v1/auth/verify-otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, otp }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Verify failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return (await res.json()) as { token: string; user: Record<string, unknown> };
  },

  // Request a password-reset OTP for the given email.
  forgotPasswordLocal: async (email: string) => {
    const res = await fetch("/api/v1/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return (await res.json()) as { status: string; email: string; token?: string };
  },

  // Reset the password after verifying the OTP.
  resetPasswordLocal: async (token: string, otp: string, newPassword: string) => {
    const res = await fetch("/api/v1/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, otp, new_password: newPassword }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Reset failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return (await res.json()) as { token: string; user: Record<string, unknown> };
  },
};
