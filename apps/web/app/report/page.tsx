"use client";

import { FileWarning, ImagePlus, Lock, MapPin, Send, X } from "lucide-react";
import Image from "next/image";
import { useEffect, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Select } from "@/app/components/ui/Input";
import { submitReport } from "@/lib/api";
import type { ReportResult, ReportSubmission } from "@/lib/types";

// The API caps the base64 evidence_image string at 5,000,000 chars, so a
// 3.5 MB raw file stays comfortably under the limit after data-URL inflation.
const MAX_IMAGE_BYTES = 3_500_000;

const CATEGORIES = [
  { id: "streetlight_not_working", label: "Streetlight not working" },
  { id: "poor_lighting", label: "Poor lighting" },
  { id: "harassment", label: "Harassment" },
  { id: "suspicious_activity", label: "Suspicious activity" },
  { id: "blocked_sidewalk", label: "Blocked sidewalk" },
  { id: "unsafe_transport", label: "Unsafe transport" },
  { id: "road_hazard", label: "Road hazard" },
  { id: "other", label: "Other" },
];

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

export default function ReportPage() {
  const [category, setCategory] = useState("poor_lighting");
  const [details, setDetails] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReportResult | null>(null);
  const [mounted, setMounted] = useState(false);
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [segmentIds, setSegmentIds] = useState<number[]>([]);
  useEffect(() => {
    setSegmentIds(lastRouteSegmentIds());
    setMounted(true);
  }, []);

  const canSubmit = segmentIds.length > 0 && details.trim().length >= 10;

  const handleImage = (file: File | undefined) => {
    setImageError(null);
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setImageError("Please choose an image file (PNG, JPEG, WEBP, ...).");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImageError("Image is too large — the maximum size is 3.5 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setImageData(typeof reader.result === "string" ? reader.result : null);
    reader.onerror = () => setImageError("Could not read the image file.");
    reader.readAsDataURL(file);
  };

  const submit = async () => {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: ReportSubmission = {
        segment_id: segmentIds[0],
        category,
        description: details.trim(),
        evidence_image: imageData,
      };
      const res = await submitReport(payload);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit the report.");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <Card className="max-w-sm text-center">
          <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-success/15 text-success">
            <Send className="size-5" aria-hidden />
          </span>
          <h1 className="text-lg font-bold text-foreground">Report submitted</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Reference {result.report_id} — thank you. Your report is anonymous and will be reviewed
            by our verification pipeline.
          </p>
          <Button variant="secondary" className="mt-4" onClick={() => setResult(null)}>
            Submit another report
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <span className="text-primary">Report an incident</span>
            <FileWarning className="size-5 text-emergency" aria-hidden />
          </h1>
          <p className="text-sm text-text-muted">
            Reports help build better evidence for everyone. They are never used to judge you.
          </p>
        </header>

        {mounted && segmentIds.length === 0 ? (
          <Card>
            <div className="flex items-start gap-3 p-4">
              <MapPin className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              <div className="text-xs leading-relaxed text-text-secondary">
                Reports are attached to a road segment from a route you planned.{" "}
                <a href="/live" className="font-semibold text-primary underline">
                  Plan a route first
                </a>{" "}
                and come back here — we will prefill the segment for you.
              </div>
            </div>
          </Card>
        ) : null}

        <Card className="report-form-card">
          <CardHeader
            title="Incident details"
            subtitle="Be specific about what you saw — never include names or private details."
          />
          <div className="space-y-4">
            <Select
              id="category"
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </Select>

            {mounted && segmentIds.length > 0 ? (
              <p className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-[11px] text-text-muted">
                <MapPin className="size-3.5 shrink-0" aria-hidden />
                Attached to road segment #{segmentIds[0]} from your last planned route
                {segmentIds.length > 1 ? ` (+${segmentIds.length - 1} more)` : ""}.
              </p>
            ) : null}

            <div>
              <label
                htmlFor="details"
                className="mb-1.5 block text-xs font-medium text-text-secondary"
              >
                Description
              </label>
              <textarea
                id="details"
                rows={5}
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Describe what you observed — facts only. Example: 'Streetlight not working on the south side of the lane; pedestrian path is dark after 9pm.'"
                maxLength={500}
                className="w-full resize-none rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-foreground transition-colors duration-150 placeholder:text-text-muted focus:border-primary/40 focus:outline-none"
              />
              <p className="mt-1 text-right text-[11px] text-text-muted">{details.length}/500</p>
            </div>

            <div>
              <input
                id="evidence-image"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  handleImage(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
              {imageData ? (
                <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2">
                  <Image
                    src={imageData}
                    alt="Selected evidence preview"
                    width={64}
                    height={64}
                    unoptimized
                    className="size-16 shrink-0 rounded-lg border border-border object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-foreground">Photo attached</p>
                    <p className="text-[11px] leading-relaxed text-text-muted">
                      Metadata (EXIF) is stripped and the image is encrypted on the server.
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Remove attached photo"
                    onClick={() => {
                      setImageData(null);
                      setImageError(null);
                    }}
                  >
                    <X className="size-3.5" aria-hidden /> Remove
                  </Button>
                </div>
              ) : (
                <label
                  htmlFor="evidence-image"
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-dashed border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors duration-150 hover:border-primary/40 hover:text-foreground"
                >
                  <ImagePlus className="size-4" aria-hidden />
                  Add photo evidence (optional, max 3.5 MB)
                </label>
              )}
              {imageError ? (
                <p role="alert" className="mt-1.5 text-[11px] text-danger">
                  {imageError}
                </p>
              ) : null}
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-xl border border-danger/25 bg-danger/8 px-3 py-2 text-xs text-danger"
              >
                {error}
              </p>
            ) : null}

            <div className="report-form-footer flex items-center justify-between gap-3">
              <p className="flex items-center gap-1.5 text-[11px] text-text-muted">
                <Lock className="size-3.5" aria-hidden /> Reported anonymously · never shared
                publicly
              </p>
              <Button loading={submitting} disabled={!canSubmit} onClick={submit}>
                Submit report
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
