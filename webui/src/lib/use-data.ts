// Data hooks: fetch real data from /api/v1, fall back to demo fixtures when
// the backend is unreachable (so every page renders fully for previews/screenshots).
"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ResumeListItem, type ResumeResult } from "./api";
import { demoDetail, demoResumes } from "./demo";

type S<T> = { data: T; loading: boolean; error: string | null; touch: () => void };

function useList(token: string | null): S<ResumeListItem[]> {
  const [data, setData] = useState<ResumeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const touch = useCallback(() => {
    setLoading(true);
    setError(null);
    if (!token) {
      setData([]);
      setLoading(false);
      return;
    }
    api.list(token)
      .then((r) => setData(r.resumes))
      .catch(() => setData(demoResumes))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { touch(); }, [touch, token]);
  return { data, loading, error, touch };
}

function useDetail(token: string | null, id: string): S<ResumeResult | null> {
  const [data, setData] = useState<ResumeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const touch = useCallback(() => {
    setLoading(true);
    setError(null);
    if (!token) {
      setData(demoDetail(id));
      setLoading(false);
      return;
    }
    api.get(id, token)
      .then((r) => setData(r))
      .catch(() => setData(demoDetail(id)))
      .finally(() => setLoading(false));
  }, [token, id]);

  useEffect(() => { touch(); }, [touch, token, id]);
  return { data, loading, error, touch };
}

export { useList, useDetail };
