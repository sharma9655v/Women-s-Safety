"use client";

import { Card, CardHeader } from "@/app/components/ui/Card";
import { Chart } from "@/app/components/ui/Chart";

export function ScoreTrendCard({
  points,
}: {
  points: { hour: number; score: number; confidence: number }[];
}) {
  const chartPoints = points.map((p) => ({ x: p.hour, y: p.score }));

  return (
    <Card>
      <CardHeader
        title="Estimated Safety by Hour"
        subtitle="Based on available evidence — not a guarantee"
      />
      {chartPoints.length >= 2 ? (
        <Chart points={chartPoints} height={140} className="mt-2" />
      ) : (
        <p className="py-8 text-center text-sm text-text-muted">
          Insufficient data for trend analysis.
        </p>
      )}
      <div className="mt-3 flex items-center justify-between text-[10px] text-text-muted">
        <span>12 AM</span>
        <span>6 AM</span>
        <span>12 PM</span>
        <span>6 PM</span>
        <span>12 AM</span>
      </div>
    </Card>
  );
}
