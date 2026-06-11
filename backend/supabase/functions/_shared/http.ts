// Shared HTTP helpers for every Munch edge function.
//
// Why this exists: all functions return JSON in one envelope with one header
// set, so the iOS APIClient can decode a single, uniform error contract.
// Centralizing it here keeps per-function boilerplate at zero and makes the
// contract impossible to drift per-endpoint.

/** Uniform success/error envelope returned by every Munch edge function. */
export interface ApiResponse<T> {
  ok: boolean;
  data: T | null;
  /** Machine-readable error code (e.g. "validation_failed"); null on success. */
  error: string | null;
}

/** Build a JSON Response carrying the Munch envelope. */
export function jsonResponse<T>(body: ApiResponse<T>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

/** Successful payload, status 200. */
export function ok<T>(data: T): Response {
  return jsonResponse<T>({ ok: true, data, error: null });
}

/** Error with a machine-readable code and an HTTP status. */
export function fail(code: string, status: number): Response {
  return jsonResponse<never>({ ok: false, data: null, error: code }, status);
}
