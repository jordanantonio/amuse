import { authClient } from './auth';
export async function request<T>(path: string, persona: string, method = 'GET'): Promise<T> {
  const headers: Record<string, string> = {};
  if (persona) {
    headers['X-Demo-Persona'] = persona;
  } else {
    const { data, error } = await authClient().auth.getSession();
    if (error || !data.session) {
      window.dispatchEvent(new Event('shift-session-expired'));
      throw new Error('Session expired. Please sign in again.');
    }
    headers.Authorization = `Bearer ${data.session.access_token}`;
  }
  const response = await fetch(`/api/v1${path}`, { method, headers, cache: 'no-store' });
  if (!response.ok) {
    if (!persona && response.status === 401) {
      window.dispatchEvent(new Event('shift-session-expired'));
    }
    const error = await response.json().catch(() => ({ detail: 'SHIFT API unavailable.' }));
    throw new Error(
      typeof error.detail === 'string' ? error.detail : `Request failed (${response.status})`,
    );
  }
  return response.json();
}
