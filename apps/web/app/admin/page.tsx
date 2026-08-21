"use client";

import { Check, ClipboardCheck, KeyRound, Loader2, MessagesSquare, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Pill } from "@/app/components/ui/Pill";
import { getAdminKey, setAdminKey } from "@/lib/admin-key";
import {
  adminModerateCommunityPost,
  adminSetVerification,
  fetchAdminReports,
  fetchCommunity,
} from "@/lib/api";
import type { AdminReport, CommunityPost } from "@/lib/types";

function stateColor(state: string): string {
  if (state === "VERIFIED") return "bg-success/12 text-success";
  if (state === "REJECTED") return "bg-danger/12 text-danger";
  return "bg-warning/12 text-warning";
}

export default function AdminPage() {
  const [adminKey, setAdminKeyState] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return getAdminKey();
  });
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const queue = adminKey
      ? fetchAdminReports(adminKey).then((rows) => setReports(rows))
      : Promise.resolve().then(() => setReports([]));
    const feed = fetchCommunity()
      .then((rows) => setPosts(rows))
      .catch(() => setPosts([]));
    Promise.all([queue, feed])
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "The admin queue is unavailable.");
      })
      .finally(() => setLoading(false));
  }, [adminKey]);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (reportId: number, state: "verify" | "reject") => {
    if (!adminKey) return;
    setBusy(`report:${reportId}`);
    try {
      await adminSetVerification(reportId, state, adminKey);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  };

  const decidePost = async (postId: string, state: "verify" | "reject") => {
    if (!adminKey) return;
    setBusy(`post:${postId}`);
    try {
      await adminModerateCommunityPost(postId, state, adminKey);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <ClipboardCheck className="size-5 text-primary" aria-hidden />
            Review <span className="text-primary">Queue</span>
          </h1>
          <p className="text-sm text-text-muted">
            Moderated verification of community reports. Reports are listed without descriptions or
            reporter identity; decisions are sticky and audited.
          </p>
        </header>

        <Card>
          <CardHeader
            title="Admin access"
            subtitle="Required for the X-Admin-Key header. Stored only in this browser."
          />
          <div className="flex items-center gap-2">
            <KeyRound className="size-4 text-text-muted" aria-hidden />
            <input
              type="password"
              value={adminKey}
              onChange={(e) => {
                setAdminKeyState(e.target.value);
                setAdminKey(e.target.value);
              }}
              placeholder="Admin key"
              className="h-10 flex-1 rounded-xl border border-border bg-surface px-3 text-sm text-foreground outline-none transition-colors focus:border-primary"
            />
            <button
              type="button"
              onClick={load}
              className="h-10 cursor-pointer rounded-xl bg-primary px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-hover"
            >
              Load queue
            </button>
          </div>
        </Card>

        {error ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-danger">{error}</p>
        ) : null}

        {loading ? (
          <div className="grid gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="glass h-16 animate-pulse rounded-2xl" />
            ))}
          </div>
        ) : !adminKey ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-text-muted">
            Enter the admin key to load the queue.
          </p>
        ) : reports.length === 0 ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-text-muted">
            No reports in the queue.
          </p>
        ) : (
          <ul className="space-y-2">
            {reports.map((r) => (
              <li
                key={r.report_id}
                className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface p-3.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-foreground">
                    #{r.report_id}
                    <Pill active={false} onClick={() => {}}>
                      {r.category.replace(/_/g, " ")}
                    </Pill>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${stateColor(r.verification_state)}`}
                    >
                      {r.verification_state}
                    </span>
                  </p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    Segment {r.segment_id} · confidence {Math.round((r.confidence ?? 0) * 100)}% ·{" "}
                    {new Date(r.reported_at).toLocaleString()}
                  </p>
                </div>
                {r.verification_state !== "VERIFIED" ? (
                  <button
                    type="button"
                    onClick={() => decide(r.report_id, "verify")}
                    disabled={busy === `report:${r.report_id}`}
                    aria-label={`Verify report ${r.report_id}`}
                    className="flex h-9 cursor-pointer items-center gap-1 rounded-xl bg-success/12 px-3 text-xs font-semibold text-success transition-colors hover:bg-success/20 disabled:cursor-wait disabled:opacity-60"
                  >
                    {busy === `report:${r.report_id}` ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <Check className="size-3.5" aria-hidden />
                    )}
                    Verify
                  </button>
                ) : null}
                {r.verification_state !== "REJECTED" ? (
                  <button
                    type="button"
                    onClick={() => decide(r.report_id, "reject")}
                    disabled={busy === `report:${r.report_id}`}
                    aria-label={`Reject report ${r.report_id}`}
                    className="flex h-9 cursor-pointer items-center gap-1 rounded-xl bg-danger/12 px-3 text-xs font-semibold text-danger transition-colors hover:bg-danger/20 disabled:cursor-wait disabled:opacity-60"
                  >
                    {busy === `report:${r.report_id}` ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <X className="size-3.5" aria-hidden />
                    )}
                    Reject
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        <Card>
          <CardHeader
            title="Community posts"
            subtitle="Anonymous posts awaiting review. Public feed shows PENDING and VERIFIED only."
          />
          {posts.length === 0 ? (
            <p className="py-3 text-center text-sm text-text-muted">No community posts.</p>
          ) : (
            <ul className="space-y-2">
              {posts.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface p-3.5"
                >
                  <MessagesSquare className="size-4 shrink-0 text-primary" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-foreground">
                      {p.kind.replace(/_/g, " ")}
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${stateColor(p.status)}`}
                      >
                        {p.status}
                      </span>
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-text-secondary">{p.text}</p>
                    <p className="mt-0.5 text-[10px] text-text-muted">
                      {p.location} · {new Date(p.created_at).toLocaleString()}
                    </p>
                  </div>
                  {p.status === "PENDING" ? (
                    <>
                      <button
                        type="button"
                        onClick={() => decidePost(p.id, "verify")}
                        disabled={busy === `post:${p.id}`}
                        aria-label={`Verify post ${p.id}`}
                        className="flex h-9 cursor-pointer items-center gap-1 rounded-xl bg-success/12 px-3 text-xs font-semibold text-success transition-colors hover:bg-success/20 disabled:cursor-wait disabled:opacity-60"
                      >
                        {busy === `post:${p.id}` ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden />
                        ) : (
                          <Check className="size-3.5" aria-hidden />
                        )}
                        Verify
                      </button>
                      <button
                        type="button"
                        onClick={() => decidePost(p.id, "reject")}
                        disabled={busy === `post:${p.id}`}
                        aria-label={`Reject post ${p.id}`}
                        className="flex h-9 cursor-pointer items-center gap-1 rounded-xl bg-danger/12 px-3 text-xs font-semibold text-danger transition-colors hover:bg-danger/20 disabled:cursor-wait disabled:opacity-60"
                      >
                        {busy === `post:${p.id}` ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden />
                        ) : (
                          <X className="size-3.5" aria-hidden />
                        )}
                        Reject
                      </button>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
