import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CVHealth, CVListResponse, ModelsCurrent } from "@/lib/types";
import ModelsPage from "./page";
import { api } from "@/lib/api";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  localStorage.clear();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

vi.mock("lucide-react", () => {
  const react = require("react");
  const Icon = (props: Record<string, unknown>) =>
    react.createElement("span", { ...props, "data-testid": "icon" });
  const icons: Record<string, typeof Icon> = {};
  for (const name of [
    "Shield",
    "Cpu",
    "Database",
    "Loader2",
    "CheckCircle",
    "XCircle",
    "AlertTriangle",
    "FileText",
    "Download",
    "ExternalLink",
    "GitBranch",
    "Globe",
    "Eye",
    "BarChart2",
    "Brain",
    "Zap",
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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function renderWithData() {
  fetchMock
    .mockResolvedValueOnce(jsonResponse(MODELS))
    .mockResolvedValueOnce(jsonResponse(HEALTH))
    .mockResolvedValueOnce(jsonResponse(REGISTRY));

  render(<ModelsPage />);

  await waitFor(() => {
    expect(screen.getByText("ML Gate Status")).toBeTruthy();
  });
}

describe("ModelsPage", () => {
  beforeEach(() => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(MODELS))
      .mockResolvedValueOnce(jsonResponse(HEALTH))
      .mockResolvedValueOnce(jsonResponse(REGISTRY));
  });

  describe("ML Gate Status", () => {
    it("shows ML Gate Status section", async () => {
      await renderWithData();
      expect(screen.getByText("ML Gate Status")).toBeTruthy();
    });

    it("shows gate status as CLOSED when open is false", async () => {
      await renderWithData();
      expect(screen.getByText("CLOSED")).toBeTruthy();
    });

    it("shows verified observations count", async () => {
      await renderWithData();
      expect(screen.getByText("42")).toBeTruthy();
      expect(screen.getByText("Verified Obs.")).toBeTruthy();
    });

    it("shows span days", async () => {
      await renderWithData();
      expect(screen.getByText("12")).toBeTruthy();
      expect(screen.getByText("Span (days)")).toBeTruthy();
    });

    it("shows min required observations", async () => {
      await renderWithData();
      expect(screen.getByText("1000")).toBeTruthy();
      expect(screen.getByText("Min Required")).toBeTruthy();
    });

    it("shows min span days", async () => {
      await renderWithData();
      expect(screen.getByText(/Min span:\s*90/i)).toBeTruthy();
    });
  });

  describe("Active Models", () => {
    it("shows Active Models section", async () => {
      await renderWithData();
      expect(screen.getByText("Active Models")).toBeTruthy();
    });

    it("shows Risk Model card", async () => {
      await renderWithData();
      expect(screen.getByText("Risk Model")).toBeTruthy();
      const versionElements = screen.getAllByText("rules-v1 (deterministic)");
      expect(versionElements.length).toBeGreaterThan(0);
      expect(screen.getByText("Risk scoring")).toBeTruthy();
    });

    it("shows Evidence Model card", async () => {
      await renderWithData();
      expect(screen.getByText("Evidence Model")).toBeTruthy();
      const versionElements = screen.getAllByText("evidence-fusion-v1");
      expect(versionElements.length).toBeGreaterThan(0);
      expect(screen.getByText("Evidence fusion")).toBeTruthy();
    });

    it("shows dataset versions as badges", async () => {
      await renderWithData();
      expect(screen.getByText("osm-evidence-2026-07")).toBeTruthy();
    });
  });

  describe("Transparency & Reproducibility Section", () => {
    it("shows Transparency & Reproducibility section", async () => {
      await renderWithData();
      expect(screen.getByText("Transparency & Reproducibility")).toBeTruthy();
    });

    it("shows ML Gate criteria", async () => {
      await renderWithData();
      expect(screen.getByText(/ML Gate criteria public: min/i)).toBeTruthy();
    });

    it("shows Risk model version", async () => {
      await renderWithData();
      expect(screen.getByText("Risk model version:")).toBeTruthy();
    });

    it("shows Evidence model version", async () => {
      await renderWithData();
      expect(screen.getByText("Evidence model version:")).toBeTruthy();
    });

    it("shows CV models section", async () => {
      await renderWithData();
      expect(screen.getByText(/CV models only deployed after/i)).toBeTruthy();
    });

    it("shows Dataset versions tracked", async () => {
      await renderWithData();
      expect(screen.getByText(/Dataset versions tracked:/i)).toBeTruthy();
    });

    it("shows View Full Registry button", async () => {
      await renderWithData();
      expect(screen.getByRole("button", { name: /View Full Registry/i })).toBeTruthy();
    });

    it("shows Source on GitHub button", async () => {
      await renderWithData();
      expect(screen.getByRole("button", { name: /Source on GitHub/i })).toBeTruthy();
    });
  });

  describe("CV Models & Data Sources Tabs", () => {
    it("shows CV Models tab button", async () => {
      await renderWithData();
      expect(screen.getByText("CV Models")).toBeTruthy();
    });

    it("shows Data Sources tab button", async () => {
      await renderWithData();
      expect(screen.getByText("Data Sources")).toBeTruthy();
    });

    it("renders CV Models tab content when CV Models tab is active", async () => {
      await renderWithData();
      await waitFor(() => {
        expect(screen.getByText("Computer Vision Models")).toBeTruthy();
      });
      await waitFor(() => {
        const nameElements = screen.getAllByText(/streetlight-classifier/i);
        expect(nameElements.length).toBeGreaterThan(0);
        expect(screen.getByText("VALIDATION_REQUIRED")).toBeTruthy();
        expect(screen.getByText(/Checkpoint:/i)).toBeTruthy();
        expect(screen.getByText("cv_classifier")).toBeTruthy();
        expect(screen.getByText("tflite")).toBeTruthy();
      });
    });

    it("renders Data Sources tab content when Data Sources tab is clicked", async () => {
      const user = userEvent.setup();
      await renderWithData();

      const sourcesTab = screen.getByText("Data Sources");
      await user.click(sourcesTab);

      await waitFor(() => {
        expect(screen.getByText("Data Sources & Provenance")).toBeTruthy();
        expect(screen.getByText("OpenStreetMap")).toBeTruthy();
        expect(screen.getByText("Community Reports")).toBeTruthy();
        expect(screen.getByText("Lighting Survey")).toBeTruthy();
        expect(screen.getByText("Traffic Cameras")).toBeTruthy();
      });
    });
  });
});