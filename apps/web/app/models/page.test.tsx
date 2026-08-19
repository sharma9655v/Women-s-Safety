import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelsPage from "./page";
import type { CVHealth, CVListResponse, ModelsCurrent } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchModelsCurrent: vi.fn(),
  fetchCvHealth: vi.fn(),
  fetchCvModels: vi.fn(),
  predictCv: vi.fn(),
}));

vi.mock("lucide-react", () => {
  const react = require("react");
  const Icon = (props: Record<string, unknown>) =>
    react.createElement("span", { ...props, "data-testid": "icon" });
  const icons: Record<string, typeof Icon> = {};
  for (const name of [
    "BrainCircuit",
    "Cpu",
    "FileImage",
    "FlaskConical",
    "Loader2",
    "Lock",
    "TriangleAlert",
  ]) {
    icons[name] = Icon;
  }
  return icons;
});

import { fetchCvHealth, fetchCvModels, fetchModelsCurrent } from "@/lib/api";

const MODELS: ModelsCurrent = {
  risk_model: "rules-v1 (deterministic)",
  evidence_model: "evidence-fusion-v1",
  dataset_versions: ["osm-evidence-2026-07"],
  ml_gate: {
    open: false,
    verified_observations: 42,
    span_days: 12,
    min_verified_observations: 1000,
    min_span_days: 90,
  },
  cv_models: [
    {
      name: "streetlight-classifier",
      version: "0.3.1",
      kind: "cv_classifier",
      framework: "tflite",
      checkpoint_path: "models/registry/streetlight-classifier-v0.3.1.tflite",
      input_schema: {},
      output_schema: {},
      status: "VALIDATION_REQUIRED",
      metrics: {},
      dataset_version: "osm-evidence-2026-07",
      integration: "not_integrated",
    },
  ],
};

const HEALTH: CVHealth = {
  backend: "cv_mock",
  loaded: false,
  models: [],
  is_real_inference: false,
  note: "Development mock backend.",
};

const REGISTRY: CVListResponse = {
  models: MODELS.cv_models,
  backend: "cv_mock",
  loaded: false,
  is_real_inference: false,
};

beforeEach(() => {
  vi.mocked(fetchModelsCurrent).mockResolvedValue(MODELS);
  vi.mocked(fetchCvHealth).mockResolvedValue(HEALTH);
  vi.mocked(fetchCvModels).mockResolvedValue(REGISTRY);
});

describe("ModelsPage", () => {
  it("shows the closed validation gate with real thresholds", async () => {
    render(<ModelsPage />);
    expect(await screen.findByText("Gate closed — ML not used in routing")).toBeTruthy();
    expect(screen.getByText("42")).toBeTruthy();
    expect(screen.getByText("/ 1000")).toBeTruthy();
  });

  it("labels the demo backend honestly instead of claiming real inference", async () => {
    render(<ModelsPage />);
    expect(await screen.findByText("Demo (no real model)")).toBeTruthy();
    expect(screen.queryByText("Real inference")).toBeNull();
  });

  it("shows the validation-in-progress notice for unvalidated checkpoints", async () => {
    render(<ModelsPage />);
    expect(await screen.findByText(/Model validation in progress/)).toBeTruthy();
    expect(screen.getByText("Validation required")).toBeTruthy();
    expect(screen.getByText(/not approved for any production use/)).toBeTruthy();
  });
});
