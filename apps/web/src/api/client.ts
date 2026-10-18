// Thin fetch wrapper. The web app renders server values only; it never computes metrics (invariant 6).

export type Health = { status: string; db: boolean };

export async function getJson<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return (await res.json()) as T;
}
