"use client";
/** Tiny SWR-style hook with deduping, polling, and error retries. */

import { useEffect, useRef, useState } from "react";

interface QueryOptions<T> {
  dedupeMs?: number;
  revalidateMs?: number;
  retry?: number;
  onError?: (err: Error) => void;
}

export function useQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  opts: QueryOptions<T> = {},
): { data: T | undefined; error: Error | undefined; isLoading: boolean; mutate: () => Promise<void> } {
  const { dedupeMs = 1000, revalidateMs = 0, retry = 2, onError } = opts;
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const inFlight = useRef<Promise<T> | null>(null);
  const lastFetch = useRef(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const execute = async (force?: boolean): Promise<void> => {
    const now = Date.now();
    if (!force && inFlight.current) return inFlight.current.then(() => {});
    if (!force && now - lastFetch.current < dedupeMs) return;

    const attempt = async (attemptNum: number): Promise<T> => {
      try {
        const result = await fetcher();
        return result;
      } catch (e) {
        if (attemptNum < retry) {
          await new Promise((r) => setTimeout(r, 300 * (attemptNum + 1)));
          return attempt(attemptNum + 1);
        }
        throw e;
      }
    };

    const p = attempt(0);
    inFlight.current = p;
    setIsLoading(true);
    try {
      const result = await p;
      setData(result);
      setError(undefined);
      lastFetch.current = Date.now();
    } catch (e) {
      setError(e as Error);
      onError?.(e as Error);
    } finally {
      setIsLoading(false);
      inFlight.current = null;
    }
  };

  const mutate = async () => execute(true);

  useEffect(() => {
    execute();
    if (revalidateMs > 0) {
      timer.current = setInterval(() => execute(false), revalidateMs);
    }
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [key]);

  return { data, error, isLoading, mutate };
}