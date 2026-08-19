"use client";

import { BrainCircuit, Cpu, FileImage, FlaskConical, Lock, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { fetchCvHealth, fetchCvModels, fetchModelsCurrent, predictCv } from "@/lib/api";
import type { CVHealth, CVListResponse, CVPredictResponse, ModelsCurrent } from "@/lib/types";

const STATUS_TONE: Record<string, "success" | "warning" | "info" | "default"> = {
  PRODUCTION: "success",
  AVAILABLE: "info",
  EXPERIMENTAL: "warning",
  VALIDATION_REQUIRED: "warning",
};

/** Honest status label — a checkpoint is never presented as ready for
 * routing unless the backend itself reports it as PRODUCTION. */
function statusLabel(status: string): string {
  switch (status) {
    case "PRODUCTION":
      return "Production";
    case "AVAILABLE":
      return "Available";
    case "EXPERIMENTAL":
      return "Experimental";
    case "VALIDATION_REQUIRED":
      return "Validation required";
    default:
      return status.replace(/_/g, " ");
  }
}

const MAX_IMAGE_BYTES = 3_500_000;

export default function ModelsPage() {
  const [models, setModels] = useState<ModelsCurrent | null>(null);
  const [health, setHealth] = useState<CVHealth | null>(null);
  const [registry, setRegistry] = useState<CVListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [imageData, setImageData] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [kind, setKind] = useState<"cv_classifier" | "cv_detector">("cv_classifier");
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState<CVPredictResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchModelsCurrent().catch(() => null),
      fetchCvHealth().catch(() => null),
      fetchCvModels().catch(() => null),
    ])
      .then(([m, h, r]) => {
        if (cancelled) return;
        setModels(m);
        setHealth(h);
        setRegistry(r);
      })
      .catch(() => {
        if (!cancelled) setError("Model information is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleImage = (file: File | undefined) => {
    setImageError(null);
    setPrediction(null);
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

  const runPrediction = async () => {
    if (!imageData || predicting) return;
    setPredicting(true);
    setImageError(null);
    try {
      setPrediction(await predictCv({ image_base64: imageData, kind }));
    } catch (e) {
      setImageError(e instanceof Error ? e.message : "Prediction failed. Try again.");
    } finally {
      setPredicting(false);
    }
  };

  const gate = models?.ml_gate;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <BrainCircuit className="size-5 text-primary" aria-hidden />
            AI <span className="text-primary">Models</span>
          </h1>
          <p className="text-sm text-text-muted">
            A transparent view of the computer-vision checkpoints on this deployment — what is live,
            what is gated behind validation, and what is only a development mock. Nothing here is
            ever presented as a real model output unless the backend says so.
          </p>
        </header>

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <SkeletonCard rows={3} />
            <SkeletonCard rows={3} />
            <SkeletonCard rows={3} />
          </div>
        ) : error ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-danger">{error}</p>
        ) : (
          <>
            {/* Gate + active models */}
            <Card>
              <CardHeader
                title="Model versions"
                subtitle="What routing and evidence currently use (GET /api/models/current)"
              />
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-text-secondary">Risk model</p>
                  <p className="font-semibold text-foreground">{models?.risk_model ?? "—"}</p>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-text-secondary">Evidence model</p>
                  <p className="font-semibold text-foreground">{models?.evidence_model ?? "—"}</p>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-text-secondary">Dataset versions</p>
                  <p className="font-medium text-foreground">
                    {models?.dataset_versions.length ? models.dataset_versions.join(", ") : "—"}
                  </p>
                </div>
              </div>

              <div className="mt-4 border-t border-border pt-4">
                <CardHeader
                  title="ML validation gate"
                  subtitle="The ML pipeline stays off the routing path until enough verified evidence exists."
                />
                {gate ? (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {gate.open ? (
                        <Badge tone="success">Gate open — ML scoring active</Badge>
                      ) : (
                        <Badge tone="warning">Gate closed — ML not used in routing</Badge>
                      )}
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div className="rounded-xl border border-border bg-surface px-3 py-2">
                        <p className="text-[11px] text-text-muted">Verified observations</p>
                        <p className="text-lg font-bold text-foreground">
                          {gate.verified_observations}
                          <span className="text-xs font-medium text-text-muted">
                            {" "}
                            / {gate.min_verified_observations}
                          </span>
                        </p>
                      </div>
                      <div className="rounded-xl border border-border bg-surface px-3 py-2">
                        <p className="text-[11px] text-text-muted">Evidence span</p>
                        <p className="text-lg font-bold text-foreground">
                          {gate.span_days === null ? "—" : `${gate.span_days}d`}
                          {gate.span_days !== null ? (
                            <span className="text-xs font-medium text-text-muted">
                              {" "}
                              / {gate.min_span_days}d
                            </span>
                          ) : null}
                        </p>
                      </div>
                      <div className="rounded-xl border border-border bg-surface px-3 py-2">
                        <p className="text-[11px] text-text-muted">CV models registered</p>
                        <p className="text-lg font-bold text-foreground">
                          {models?.cv_models.length ?? registry?.models.length ?? 0}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </Card>

            {/* CV backend health */}
            <Card>
              <CardHeader
                title="Computer-vision backend"
                subtitle="Health of the CV inference service (GET /api/cv/health)"
                action={
                  health ? (
                    <Badge tone={health.is_real_inference ? "success" : "warning"}>
                      {health.is_real_inference ? "Real inference" : "Demo (no real model)"}
                    </Badge>
                  ) : undefined
                }
              />
              {health ? (
                <div className="space-y-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-text-secondary">Backend</p>
                    <p className="font-semibold text-foreground">{health.backend}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-text-secondary">Loaded</p>
                    <p className="font-semibold text-foreground">{health.loaded ? "Yes" : "No"}</p>
                  </div>
                  <p className="rounded-xl border border-border bg-surface px-3 py-2 text-xs leading-relaxed text-text-muted">
                    {health.is_real_inference
                      ? "Predictions below come from a deployed model backend."
                      : "The development build reports demo predictions. Until a real model backend is deployed, results are clearly labelled and are never used for routing or safety decisions."}
                    {health.note ? ` ${health.note}` : ""}
                  </p>
                </div>
              ) : null}
            </Card>

            {/* Registry */}
            <Card>
              <CardHeader
                title="Registered checkpoints"
                subtitle="From models/registry.json via GET /api/cv/models"
              />
              {!registry || registry.models.length === 0 ? (
                <p className="py-4 text-center text-xs text-text-muted">
                  No CV checkpoints are registered on this deployment.
                </p>
              ) : (
                <ul className="space-y-2.5">
                  {registry.models.map((m) => {
                    const tone = STATUS_TONE[m.status] ?? "default";
                    const metrics = Object.entries(m.metrics ?? {});
                    return (
                      <li
                        key={`${m.name}@${m.version}`}
                        className="rounded-xl border border-border bg-surface px-3 py-3"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-foreground">
                              {m.name}
                              <span className="text-xs font-medium text-text-muted">
                                v{m.version}
                              </span>
                            </p>
                            <p className="mt-0.5 text-[11px] text-text-muted">
                              {m.kind.replace(/_/g, " ")} · {m.framework} ·{" "}
                              {m.integration.replace(/_/g, " ")}
                            </p>
                          </div>
                          <Badge tone={tone}>{statusLabel(m.status)}</Badge>
                        </div>

                        {m.status === "VALIDATION_REQUIRED" ? (
                          <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-[11px] text-warning">
                            <FlaskConical className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                            Model validation in progress — this checkpoint is not approved for any
                            production use until it passes validation.
                          </p>
                        ) : null}

                        {m.dataset_version ? (
                          <p className="mt-2 text-[11px] text-text-muted">
                            Dataset: {m.dataset_version}
                          </p>
                        ) : null}

                        {metrics.length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {metrics.map(([key, value]) => (
                              <span
                                key={key}
                                className="rounded-md bg-surface-hover px-2 py-0.5 text-[10px] text-text-secondary"
                              >
                                {key}: {typeof value === "number" ? value.toFixed(4) : value}
                              </span>
                            ))}
                          </div>
                        ) : null}

                        {m.checkpoint_path ? (
                          <p className="mt-2 truncate text-[10px] text-text-muted">
                            {m.checkpoint_path}
                          </p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>

            {/* Prediction sandbox */}
            <Card>
              <CardHeader
                title="Try a prediction"
                subtitle="Upload an image and run the selected checkpoint. Results are labelled as demo or real."
                action={
                  health ? (
                    <Badge tone={health.is_real_inference ? "success" : "warning"}>
                      <Cpu className="size-3" aria-hidden />
                      {health.is_real_inference ? "Real backend" : "Demo"}
                    </Badge>
                  ) : undefined
                }
              />
              <div className="space-y-3">
                <div className="flex flex-wrap items-end gap-3">
                  <label className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-text-secondary">Task</span>
                    <select
                      value={kind}
                      onChange={(e) => setKind(e.target.value as "cv_classifier" | "cv_detector")}
                      className="rounded-lg border border-border bg-surface px-2 py-2 text-sm text-foreground"
                    >
                      <option value="cv_classifier">Classifier</option>
                      <option value="cv_detector">Detector</option>
                    </select>
                  </label>
                  <input
                    id="cv-image"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      handleImage(e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                  <label
                    htmlFor="cv-image"
                    className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-dashed border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors duration-150 hover:border-primary/40 hover:text-foreground"
                  >
                    <FileImage className="size-4" aria-hidden />
                    {imageData ? "Change image" : "Choose image (max 3.5 MB)"}
                  </label>
                  <Button
                    size="sm"
                    loading={predicting}
                    disabled={!imageData}
                    onClick={() => void runPrediction()}
                  >
                    Run prediction
                  </Button>
                </div>

                {imageError ? (
                  <p role="alert" className="text-[11px] text-danger">
                    {imageError}
                  </p>
                ) : null}

                {prediction ? (
                  <div className="rounded-xl border border-border bg-surface px-3 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-foreground">
                        {prediction.model_name}
                        <span className="ml-1 text-xs font-medium text-text-muted">
                          v{prediction.model_version}
                        </span>
                      </p>
                      <Badge tone={prediction.is_real_inference ? "success" : "warning"}>
                        {prediction.is_real_inference ? "Real inference" : "Demo prediction"}
                      </Badge>
                    </div>
                    {prediction.confidence !== null ? (
                      <p className="mt-2 text-xs text-text-secondary">
                        Confidence:{" "}
                        <span className="font-semibold text-foreground">
                          {Math.round(prediction.confidence * 100)}%
                        </span>
                      </p>
                    ) : null}
                    {prediction.scores.length > 0 ? (
                      <p className="mt-1 text-xs text-text-secondary">
                        Scores: {prediction.scores.map((s) => s.toFixed(3)).join(", ")}
                      </p>
                    ) : null}
                    {prediction.detections.length > 0 ? (
                      <p className="mt-1 text-xs text-text-secondary">
                        Detections: {prediction.detections.length}
                      </p>
                    ) : null}
                    <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-text-muted">
                      <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      {prediction.is_real_inference
                        ? "Output from the deployed model backend."
                        : prediction.note || "Development mock output — not a real model result."}
                    </p>
                  </div>
                ) : null}
              </div>
            </Card>

            <p className="flex items-start gap-2 rounded-2xl border border-border bg-surface/50 px-4 py-3 text-xs leading-relaxed text-text-muted">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-warning" aria-hidden />
              Model outputs are evidence only and are never treated as ground truth. Routing and
              safety decisions in this app remain on the deterministic risk model until the ML gate
              opens.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
