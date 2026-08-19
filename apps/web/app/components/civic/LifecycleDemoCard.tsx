"use client";

import {
  CheckCircle2,
  CircleDot,
  FlaskConical,
  Hammer,
  Lightbulb,
  Loader2,
  Send,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Card } from "@/app/components/ui/Card";
import { Select } from "@/app/components/ui/Input";
import { adminSetVerification, fetchSegmentEvidenceStats, submitReport } from "@/lib/api";
import { getAdminKey } from "@/lib/admin-key";
import type { ReportResult, SegmentEvidence } from "@/lib/types";

interface Step {
  id: number;
  label: string;
  detail: string;
  outcome: "ok" | "warn" | "err";
}

function lastRouteSegmentIds(): number[] {
  try {
    const raw = sessionStorage.getItem("mf:last-route-segments");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((n): n is number => Number.isFinite(n)) : [];
  } catch {
    return [];
  }
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function LifecycleDemoCard() {
  const [segmentIds, setSegmentIds] = useState<number[]>([]);
  const [segmentId, setSegmentId] = useState<number | null>(null);
  const [evidence, setEvidence] = useState<SegmentEvidence | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [adminKey, setAdminKey] = useState<string>("");
  const [lastReport, setLastReport] = useState<ReportResult | null>(null);

  useEffect(() => {
    const ids = typeof sessionStorage === "undefined" ? [] : lastRouteSegmentIds();
    setSegmentIds(ids);
    if (ids.length > 0) setSegmentId(ids[0]);
    setAdminKey(getAdminKey());
  }, []);

  const loadEvidence = useCallback((id: number) => {
    fetchSegmentEvidenceStats(id)
      .then(setEvidence)
      .catch(() => setEvidence(null));
  }, []);

  useEffect(() => {
    if (segmentId !== null) loadEvidence(segmentId);
  }, [segmentId, loadEvidence]);

  const streetlight = useMemo(
    () => (evidence ? evidence.by_type.streetlight_not_working : null),
    [evidence],
  );

  const stepId = useRef(0);
  const addStep = (label: string, detail: string, outcome: Step["outcome"] = "ok") => {
    stepId.current += 1;
    setSteps((prev) => [...prev, { id: stepId.current, label, detail, outcome }]);
  };

  const reportFailure = async () => {
    if (segmentId === null || busy) return;
    setBusy("report");
    try {
      const stamp = new Date().toISOString().slice(11, 19);
      const result = await submitReport({
        segment_id: segmentId,
        category: "streetlight_not_working",
        description: `Streetlight not working on this segment (live demo ${stamp})`,
        evidence_image: null,
      });
      setLastReport(result);
      addStep(
        "Report accepted",
        `Report #${result.report_id} accepted as REPORTED; the evidence engine surfaces it as a user_report observation.`,
      );
      loadEvidence(segmentId);
    } catch (e) {
      addStep(
        "Report rejected",
        e instanceof Error ? e.message : "The API did not accept the report.",
        "err",
      );
    } finally {
      setBusy(null);
    }
  };

  const verifyRepair = async () => {
    if (segmentId === null || !lastReport || busy) return;
    if (!adminKey) {
      addStep(
        "Verification unavailable",
        "No admin key stored — enter one on the Review Queue page to enable municipal verification.",
        "warn",
      );
      return;
    }
    setBusy("verify");
    try {
      await adminSetVerification(lastReport.report_id, "verify", adminKey);
      addStep(
        "Repair verified",
        `Report #${lastReport.report_id} flipped to VERIFIED — the evidence engine now treats it as confirmed repair work.`,
      );
      loadEvidence(segmentId);
    } catch (e) {
      addStep(
        "Verification failed",
        e instanceof Error ? e.message : "The API did not verify the report.",
        "err",
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="space-y-3">
      <div className="mb-3">
        <h3 className="flex items-center gap-2 text-base font-semibold text-foreground">
          <FlaskConical className="size-4 text-primary" aria-hidden />
          Streetlight lifecycle demo
        </h3>
        <p className="mt-0.5 text-xs text-text-muted">
          Submits real reports through the live API and reads back the evidence engine — nothing
          simulated in the browser.
        </p>
      </div>

      {segmentIds.length === 0 ? (
        <p className="rounded-xl border border-border/60 bg-surface/50 px-3 py-4 text-center text-xs text-text-muted">
          Plan a route on the map first — the demo attaches to segments from your last planned
          route.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              aria-label="Segment to demo"
              value={String(segmentId ?? "")}
              onChange={(e) => setSegmentId(Number(e.target.value))}
              className="w-auto min-w-48"
            >
              {segmentIds.slice(0, 12).map((id) => (
                <option key={id} value={id}>
                  Segment #{id}
                </option>
              ))}
            </Select>
            <span className="text-[11px] text-text-muted">
              from last planned route · live evidence:{" "}
              {evidence ? `${evidence.total_observations} observations` : "…"}
            </span>
          </div>

          {evidence && (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-surface/50 p-3">
                <p className="text-[10px] tracking-wide text-text-muted uppercase">Freshness</p>
                <p className="mt-0.5 text-lg font-bold text-foreground">
                  {pct(evidence.overall_freshness)}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-surface/50 p-3">
                <p className="text-[10px] tracking-wide text-text-muted uppercase">Confidence</p>
                <p className="mt-0.5 text-lg font-bold text-foreground">
                  {pct(evidence.overall_confidence)}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-surface/50 p-3">
                <p className="text-[10px] tracking-wide text-text-muted uppercase">Conflicts</p>
                <p className="mt-0.5 text-lg font-bold text-foreground">
                  {evidence.conflicts.length > 0
                    ? evidence.conflicts.map((c) => c.replace(/_/g, " ")).join(", ")
                    : "none"}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-surface/50 p-3">
                <p className="text-[10px] tracking-wide text-text-muted uppercase">
                  Streetlight not working
                </p>
                <p className="mt-0.5 text-lg font-bold text-foreground">
                  {streetlight
                    ? `${streetlight.count} obs · ${pct(streetlight.confidence)}`
                    : "0 obs"}
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={reportFailure} disabled={busy !== null}>
              {busy === "report" ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Send className="size-4" aria-hidden />
              )}
              Report streetlight failure
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={verifyRepair}
              disabled={busy !== null || !lastReport}
            >
              {busy === "verify" ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Hammer className="size-4" aria-hidden />
              )}
              Verify repair (municipality)
            </Button>
            {lastReport ? (
              <span className="flex items-center gap-1 text-[11px] text-text-muted">
                <CircleDot className="size-3.5 text-warning" aria-hidden />
                Report #{lastReport.report_id} · {lastReport.verification_state}
              </span>
            ) : null}
          </div>

          {steps.length > 0 && (
            <ul className="space-y-1.5 border-t border-border/60 pt-3">
              {steps.map((s) => (
                <li
                  key={s.id}
                  className={`flex items-start gap-2 rounded-xl px-3 py-2 text-xs ${
                    s.outcome === "err"
                      ? "bg-danger/8 text-danger"
                      : s.outcome === "warn"
                        ? "bg-warning/8 text-warning"
                        : "bg-surface/50 text-text-secondary"
                  }`}
                >
                  {s.outcome === "err" ? (
                    <Lightbulb className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                  ) : s.outcome === "warn" ? (
                    <ShieldCheck className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                  ) : (
                    <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-success" aria-hidden />
                  )}
                  <span>
                    <span className="font-semibold text-foreground">{s.label}: </span>
                    {s.detail}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <p className="text-[11px] leading-relaxed text-text-muted">
            Live demo flow: report a failure (REPORTED) → the engine folds it into the segment
            evidence → verify the repair (VERIFIED). Replan the route on the map to see the risk
            estimate change. Demo-seeded observations stay labeled{" "}
            <code className="rounded bg-surface-hover px-1">demo_seed</code> and are never treated
            as real.
          </p>
        </>
      )}
    </Card>
  );
}
