export async function request<T>(path: string, persona: string, method = 'GET'): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers: { 'X-Demo-Persona': persona },
    cache: 'no-store',
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'API unavailable. Check the FastAPI server.' }));
    throw new Error(
      typeof error.detail === 'string' ? error.detail : `Request failed (${response.status})`,
    );
  }
  return response.json();
}
