import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StatCardStrip } from "./StatCardStrip";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("lucide-react", () => {
  const react = require("react");
  const Icon = (props: Record<string, unknown>) =>
    react.createElement("span", { ...props, "data-testid": "icon" });
  const icons: Record<string, typeof Icon> = {};
  for (const name of ["ArrowRight", "Building2", "ShieldAlert", "Users", "Loader2"]) {
    icons[name] = Icon;
  }
  return icons;
});

const BASE = {
  safetyScore: 62,
  safetyBand: "moderate",
  confidenceLevel: "medium",
  incidentCount: 4,
  facilityCount: 12,
  contactCount: 2,
  scoreLoading: false,
};

describe("StatCardStrip", () => {
  it("renders every stat from props with a text band label", () => {
    render(<StatCardStrip {...BASE} />);
    expect(screen.getByText("62")).toBeTruthy();
    expect(screen.getByText("Moderate")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("never implies a safety guarantee", () => {
    render(<StatCardStrip {...BASE} />);
    expect(screen.getByText("Based on recent evidence")).toBeTruthy();
    const html = document.body.textContent ?? "";
    expect(html).not.toMatch(/guarantee/i);
    expect(html).not.toMatch(/safe route/i);
  });

  it("shows Limited Data when the score is unavailable", () => {
    render(<StatCardStrip {...BASE} safetyScore={null} safetyBand={null} confidenceLevel={null} />);
    expect(screen.getByText("Limited Data")).toBeTruthy();
    expect(screen.getByText("Estimate from available data")).toBeTruthy();
  });

  it("does not claim a fixed 7-day window for incident counts", () => {
    render(<StatCardStrip {...BASE} />);
    expect(screen.queryByText(/7 days/)).toBeNull();
    expect(screen.getByText("Recent community reports")).toBeTruthy();
  });
});
