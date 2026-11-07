import { supabase } from './supabase';
export async function request<T>(
  path: string,
  persona: string,
  method = 'GET',
  body?: unknown,
): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const headers: Record<string, string> = { 'X-Demo-Persona': persona };
  if (session) headers.Authorization = `Bearer ${session.access_token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'API unavailable. Check the FastAPI server.' }));
    const detail = error.detail;
    throw new Error(
      typeof detail === 'string'
        ? detail
        : detail?.message
          ? `${detail.message} ${(detail.blockers || []).join(' ')}`
          : Array.isArray(detail)
            ? detail.map((e) => e.msg).join('; ')
            : `Request failed (${response.status})`,
    );
  }
  return response.json();
}
