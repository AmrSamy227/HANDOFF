const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiErrorResponse extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiErrorResponse";
    this.status = status;
    this.data = data;
  }
}

interface CustomRequestInit extends RequestInit {
  _isRetry?: boolean;
  _skipRefresh?: boolean;
}

// Single-flight refresh token promise to prevent multiple refresh loops
let activeRefreshPromise: Promise<void> | null = null;

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
  return match ? decodeURIComponent(match[3]) : null;
}

async function getCsrfToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  let token = getCookie("csrftoken");
  if (!token) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/csrf/`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        token = data.csrfToken || getCookie("csrftoken");
      }
    } catch {
      // Ignore initial CSRF fetch errors
    }
  }
  return token;
}

async function handleRefresh(): Promise<void> {
  if (!activeRefreshPromise) {
    activeRefreshPromise = (async () => {
      try {
        const csrfToken = await getCsrfToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (csrfToken) {
          headers["X-CSRFToken"] = csrfToken;
        }

        const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh/`, {
          method: "POST",
          headers,
          credentials: "include",
        });

        if (!res.ok) {
          throw new Error("Session expired or refresh token invalid.");
        }
      } finally {
        activeRefreshPromise = null;
      }
    })();
  }
  return activeRefreshPromise;
}

async function request<T>(endpoint: string, options: CustomRequestInit = {}): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
  const method = (options.method || "GET").toUpperCase();

  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Attach CSRF token for unsafe methods (POST, PUT, PATCH, DELETE)
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && typeof window !== "undefined") {
    const csrfToken = await getCsrfToken();
    if (csrfToken && !headers.has("X-CSRFToken")) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  const config: RequestInit = {
    ...options,
    headers,
    credentials: "include", // Strictly use HttpOnly cookies
  };

  const response = await fetch(url, config);

  // Handle 401 Unauthorized for non-auth endpoints with single-flight automatic refresh
  const isAuthEndpoint =
    endpoint.includes("/auth/login/") ||
    endpoint.includes("/auth/register/") ||
    endpoint.includes("/auth/refresh/") ||
    endpoint.includes("/auth/csrf/");

  if (response.status === 401 && !options._isRetry && !options._skipRefresh && !isAuthEndpoint) {
    try {
      await handleRefresh();
      // Retry original request once after successful refresh
      return await request<T>(endpoint, { ...options, _isRetry: true });
    } catch {
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("handoff-auth-expired"));
      }
      throw new ApiErrorResponse("Session expired. Please sign in again.", 401, null);
    }
  }

  let data: unknown = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let errorMessage = "An unexpected error occurred.";
    if (data) {
      if (typeof data === "string") {
        errorMessage = data;
      } else if (typeof data === "object" && data !== null) {
        const errorRecord = data as Record<string, unknown>;
        if (typeof errorRecord.detail === "string") {
          errorMessage = errorRecord.detail;
        } else if (typeof errorRecord.message === "string") {
          errorMessage = errorRecord.message;
        } else if (Array.isArray(errorRecord.non_field_errors)) {
          errorMessage = errorRecord.non_field_errors.join(", ");
        } else {
          const firstKey = Object.keys(errorRecord)[0];
          if (firstKey) {
            const val = errorRecord[firstKey];
            if (Array.isArray(val)) {
              errorMessage = `${firstKey}: ${val.join(", ")}`;
            } else {
              errorMessage = `${firstKey}: ${val}`;
            }
          }
        }
      }
    }
    throw new ApiErrorResponse(errorMessage, response.status, data);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, options?: CustomRequestInit) => request<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body?: unknown, options?: CustomRequestInit) =>
    request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(endpoint: string, body?: unknown, options?: CustomRequestInit) =>
    request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(endpoint: string, options?: CustomRequestInit) => request<T>(endpoint, { ...options, method: "DELETE" }),
};
