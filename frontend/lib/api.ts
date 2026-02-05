/**
 * API client for backend communication.
 * Normaliza la URL: si no tiene esquema (http/https), se asume https para evitar que el navegador la trate como ruta relativa.
 */
function normalizeBaseUrl(url: string | undefined): string {
  const raw = url || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const trimmed = raw.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed;
  return `https://${trimmed.replace(/^\/+/, '')}`;
}
const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_BACKEND_URL);

/**
 * Helper function to get token from cookies (Stack Auth stores it there with tokenStore: "nextjs-cookie")
 * Stack Auth stores the token in a cookie named "stack-access" as a URL-encoded JSON array
 * The JWT token is in the second element (index 1) of the array
 */
function getTokenFromCookies(): string | null {
  if (typeof document === 'undefined') {
    console.log('[Token] Cannot access cookies (SSR)');
    return null;
  }
  
  // Stack Auth stores the token in a cookie named "stack-access"
  const cookies = document.cookie.split(';');
  console.log('[Token] Searching for stack-access cookie, total cookies:', cookies.length);
  
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (!trimmed) continue;
    
    const [name, ...valueParts] = trimmed.split('=');
    const value = valueParts.join('='); // In case value contains '='
    
    // Look for the "stack-access" cookie specifically
    if (name === 'stack-access') {
      console.log('[Token] Found stack-access cookie, value length:', value.length);
      try {
        // Decode URL-encoded value
        const decoded = decodeURIComponent(value);
        console.log('[Token] Decoded cookie value (first 100 chars):', decoded.substring(0, 100));
        
        // Parse the JSON array
        const parsed = JSON.parse(decoded);
        console.log('[Token] Parsed JSON, is array:', Array.isArray(parsed), 'length:', Array.isArray(parsed) ? parsed.length : 'N/A');
        
        // The token is in the second element (index 1) of the array
        // First element is the refresh token ID, second is the JWT access token
        if (Array.isArray(parsed) && parsed.length > 1 && typeof parsed[1] === 'string') {
          const token = parsed[1];
          console.log('[Token] Extracted token from array, starts with eyJ:', token.startsWith('eyJ'), 'length:', token.length);
          // Verify it looks like a JWT (starts with "eyJ")
          if (token.startsWith('eyJ')) {
            return token;
          } else {
            console.warn('[Token] Token does not start with eyJ, first chars:', token.substring(0, 20));
          }
        } else {
          console.warn('[Token] Array check failed - isArray:', Array.isArray(parsed), 'length > 1:', Array.isArray(parsed) && parsed.length > 1, 'type of [1]:', Array.isArray(parsed) && parsed.length > 1 ? typeof parsed[1] : 'N/A');
        }
      } catch (err) {
        console.error('[Token] Error parsing stack-access cookie:', err);
      }
    }
  }
  console.log('[Token] stack-access cookie not found');
  return null;
}

/**
 * Helper function to create a token getter that tries multiple sources
 * 1. user.accessToken (if available)
 * 2. Cookies (where Stack Auth stores it with tokenStore: "nextjs-cookie")
 * Accepts Stack's CurrentUser | CurrentInternalUser (solo algunos tienen accessToken).
 */
export function createTokenGetter(user: unknown, stackApp?: unknown) {
  return () => {
    const token =
      user !== null &&
      typeof user === 'object' &&
      'accessToken' in user &&
      typeof (user as { accessToken?: string | null }).accessToken === 'string'
        ? (user as { accessToken: string }).accessToken
        : null;
    if (token) {
      console.log('[Token] Found token in user.accessToken');
      return token;
    }
    
    // If user.accessToken is null, try to get it from cookies
    // Stack Auth stores the token in cookies when using tokenStore: "nextjs-cookie"
    const tokenFromCookies = getTokenFromCookies();
    if (tokenFromCookies) {
      console.log('[Token] Found token in cookies, length:', tokenFromCookies.length);
      return tokenFromCookies;
    }
    
    // Log for debugging
    console.warn('[Token] Access token not found in user object or cookies, user authenticated:', !!user);
    console.warn('[Token] Available cookies:', typeof document !== 'undefined' ? document.cookie.split(';').map(c => c.trim().split('=')[0]) : 'N/A (SSR)');
    
    return null;
  };
}

export interface ApiError {
  detail: string;
}

/** Thrown when the API returns a non-2xx status. Includes statusCode for UI (e.g. 403, 400, 404). */
export class ApiResponseError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
  ) {
    super(message);
    this.name = 'ApiResponseError';
    Object.setPrototypeOf(this, ApiResponseError.prototype);
  }
}

export class ApiClient {
  private baseUrl: string;
  private getToken: () => string | null | Promise<string | null>;

  constructor(getToken: () => string | null | Promise<string | null>) {
    this.baseUrl = API_BASE_URL;
    this.getToken = getToken;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    silent: boolean = false
  ): Promise<T> {
    const tokenResult = this.getToken();
    const token = tokenResult instanceof Promise ? await tokenResult : tokenResult;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!silent) {
      console.log('[API Request] Making request to:', `${this.baseUrl}${endpoint}`);
    }

    let response: Response;
    try {
      // No usar timeout por defecto - dejar que el navegador maneje los timeouts naturales
      // Solo usar timeout para operaciones que realmente lo necesiten
      response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      });
    } catch (fetchError) {
      // "Failed to fetch" usually means:
      // 1. Backend is not running (most common)
      // 2. CORS issue
      // 3. Network error
      // 4. Timeout
      
      // Solo loguear errores si no está en modo silencioso
      if (!silent) {
        console.error('[API Request] Fetch failed:', fetchError);
        console.error('[API Request] Base URL:', this.baseUrl);
        console.error('[API Request] Endpoint:', endpoint);
        console.error('[API Request] Full URL:', `${this.baseUrl}${endpoint}`);
        console.error('[API Request] Error type:', fetchError instanceof Error ? fetchError.constructor.name : typeof fetchError);
        console.error('[API Request] Error message:', fetchError instanceof Error ? fetchError.message : String(fetchError));
        
        // Verificar si es un error de CORS
        if (fetchError instanceof TypeError && fetchError.message.includes('Failed to fetch')) {
          // Intentar verificar si el backend está accesible
          console.warn('[API Request] Posible problema de CORS o backend no accesible');
          console.warn('[API Request] Verifica que:');
          console.warn('[API Request] 1. El backend esté corriendo en', this.baseUrl);
          console.warn('[API Request] 2. CORS esté configurado correctamente en el backend');
          console.warn('[API Request] 3. No haya firewall bloqueando la conexión');
        }
      }
      
      const errorMessage = fetchError instanceof Error 
        ? (fetchError.message.includes('Failed to fetch') || fetchError.message.includes('aborted')
            ? `No se pudo conectar al backend (${this.baseUrl}). Verifica que el servidor esté corriendo y que CORS esté configurado correctamente.`
            : fetchError.message)
        : 'Error de conexión - El backend puede no estar corriendo';
      throw new Error(errorMessage);
    }

    if (!response.ok) {
      let errorDetail: string;
      try {
        const error: ApiError = await response.json();
        // Manejar si detail es un objeto o string
        if (typeof error.detail === 'string') {
          errorDetail = error.detail;
        } else if (error.detail && typeof error.detail === 'object') {
          errorDetail = JSON.stringify(error.detail);
        } else {
          errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        }
      } catch (e) {
        errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      }
      throw new ApiResponseError(errorDetail, response.status);
    }

    if (response.status === 204) {
      return null as T;
    }
    return response.json();
  }

  async get<T>(endpoint: string, silent: boolean = false): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' }, silent);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Export singleton instance (will be initialized with token getter)
let apiClient: ApiClient | null = null;

export function initApiClient(getToken: () => string | null | Promise<string | null>) {
  apiClient = new ApiClient(getToken);
  return apiClient;
}

export function getApiClient(): ApiClient {
  if (!apiClient) {
    throw new Error('API client not initialized. Call initApiClient first.');
  }
  return apiClient;
}

