/** Shift V1 API client. The session lives in an httpOnly cookie on the same origin. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const { method = 'GET', body, signal } = options;
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
    credentials: 'same-origin',
    signal,
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Shift is not responding. Check that the API server is running.' }));
    const detail = error.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((e: { msg: string }) => e.msg.replace(/^Value error, /, '')).join('; ')
          : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export const market = <T>(path: string, options?: Parameters<typeof api>[1]) =>
  api<T>(`/market${path}`, options);
