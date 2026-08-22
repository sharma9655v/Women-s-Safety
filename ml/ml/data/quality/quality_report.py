"""Data quality scoring and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ml.data.config.schema import DatasetRecord
from ml.data.validation.validate import ValidationReport


@dataclass(frozen=True)
class QualityReport:
    """Comprehensive data quality report."""

    dataset_version: str
    generated_at: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_coordinates: int
    missing_dates: int
    unknown_categories: int
    category_distribution: dict[str, int] = field(default_factory=dict)
    geographic_distribution: dict[str, int] = field(default_factory=dict)
    temporal_distribution: dict[str, int] = field(default_factory=dict)
    source_distribution: dict[str, int] = field(default_factory=dict)
    verification_distribution: dict[str, int] = field(default_factory=dict)
    quality_distribution: dict[str, int] = field(default_factory=dict)
    errors_by_type: dict[str, int] = field(default_factory=dict)
    mean_quality_score: float = 0.0
    median_quality_score: float = 0.0
    source_quality: dict[str, float] = field(default_factory=dict)
    processing_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "generated_at": self.generated_at,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "duplicate_records": self.duplicate_records,
            "missing_coordinates": self.missing_coordinates,
            "missing_dates": self.missing_dates,
            "unknown_categories": self.unknown_categories,
            "category_distribution": self.category_distribution,
            "geographic_distribution": self.geographic_distribution,
            "temporal_distribution": self.temporal_distribution,
            "source_distribution": self.source_distribution,
            "verification_distribution": self.verification_distribution,
            "quality_distribution": self.quality_distribution,
            "errors_by_type": self.errors_by_type,
            "mean_quality_score": self.mean_quality_score,
            "median_quality_score": self.median_quality_score,
            "source_quality": self.source_quality,
            "processing_version": self.processing_version,
        }

    def to_html(self) -> str:
        """Generate HTML report."""
        css = """
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
        .metric {
            display: inline-block; margin: 10px; padding: 15px;
            background: #f9f9f9; border-radius: 5px;
        }
        .metric-value { font-size: 24px; font-weight: bold; color: #333; }
        .metric-label { font-size: 12px; color: #666; }
        .warning { color: #d9534f; }
        .good { color: #5cb85c; }
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Data Quality Report - {self.dataset_version}</title>
    <style>{css}</style>
</head>
<body>
    <h1>Data Quality Report</h1>
    <p><strong>Dataset Version:</strong> {self.dataset_version}</p>
    <p><strong>Generated:</strong> {self.generated_at}</p>
    <p><strong>Processing Version:</strong> {self.processing_version}</p>

    <h2>Summary</h2>
    <div class="metric">
        <div class="metric-value">{self.total_records:,}</div>
        <div class="metric-label">Total Records</div>
    </div>
    <div class="metric good">
        <div class="metric-value">{self.valid_records:,}</div>
        <div class="metric-label">Valid Records</div>
    </div>
    <div class="metric warning">
        <div class="metric-value">{self.invalid_records:,}</div>
        <div class="metric-label">Invalid Records</div>
    </div>
    <div class="metric">
        <div class="metric-value">{self.duplicate_records:,}</div>
        <div class="metric-label">Duplicates Removed</div>
    </div>
    <div class="metric">
        <div class="metric-value">{self.mean_quality_score:.3f}</div>
        <div class="metric-label">Mean Quality Score</div>
    </div>
    <div class="metric">
        <div class="metric-value">{self.median_quality_score:.3f}</div>
        <div class="metric-label">Median Quality Score</div>
    </div>

    <h2>Data Completeness</h2>
    <table>
        <tr><th>Metric</th><th>Count</th><th>Percentage</th></tr>"""
        total = self.total_records or 1

        def _row(label: str, n: int) -> str:
            return (
                f"        <tr><td>{label}</td><td>{n:,}</td><td>{n / total * 100:.1f}%</td></tr>\n"
            )

        html += _row("Missing Coordinates", self.missing_coordinates)
        html += _row("Missing Dates", self.missing_dates)
        html += _row("Unknown Categories", self.unknown_categories)
        html += """
    </table>

    <h2>Category Distribution</h2>
    <table>
        <tr><th>Category</th><th>Count</th><th>Percentage</th></tr>
"""
        for cat, count in sorted(self.category_distribution.items(), key=lambda x: -x[1]):
            pct = count / self.total_records * 100
            html += f"        <tr><td>{cat}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>\n"

        html += """
    </table>

    <h2>Geographic Distribution (Top 20)</h2>
    <table>
        <tr><th>State</th><th>Count</th><th>Percentage</th></tr>
"""
        for state, count in sorted(self.geographic_distribution.items(), key=lambda x: -x[1])[:20]:
            pct = count / self.total_records * 100
            html += f"        <tr><td>{state}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>\n"

        html += """
    </table>

    <h2>Source Distribution</h2>
    <table>
        <tr><th>Source</th><th>Count</th><th>Percentage</th><th>Avg Quality</th></tr>
"""
        for source, count in sorted(self.source_distribution.items(), key=lambda x: -x[1]):
            pct = count / self.total_records * 100
            avg_q = self.source_quality.get(source, 0)
            html += (
                f"        <tr><td>{source}</td><td>{count:,}</td>"
                f"<td>{pct:.1f}%</td><td>{avg_q:.3f}</td></tr>\n"
            )

        html += """
    </table>

    <h2>Verification State Distribution</h2>
    <table>
        <tr><th>State</th><th>Count</th><th>Percentage</th></tr>
"""
        for state, count in sorted(self.verification_distribution.items(), key=lambda x: -x[1]):
            pct = count / self.total_records * 100
            html += f"        <tr><td>{state}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>\n"

        html += """
    </table>

    <h2>Errors by Type</h2>
    <table>
        <tr><th>Error Type</th><th>Count</th></tr>
"""
        for error, count in sorted(self.errors_by_type.items(), key=lambda x: -x[1]):
            html += f"        <tr><td>{error}</td><td>{count:,}</td></tr>\n"

        html += """
    </table>
</body>
</html>
"""
        return html


def generate_quality_report(
    records: list[DatasetRecord],
    validation_report: ValidationReport,
    dataset_version: str,
    processing_version: str = "1.0.0",
) -> QualityReport:
    """Generate comprehensive quality report."""
    valid_records = [r for r in records if r.data_quality_score is not None]

    if valid_records:
        scores = [r.data_quality_score for r in valid_records]
        mean_quality = sum(scores) / len(scores)
        median_quality = sorted(scores)[len(scores) // 2]
    else:
        mean_quality = 0.0
        median_quality = 0.0

    source_quality = {}
    for source_id in set(r.source_id for r in records):
        source_records = [r for r in records if r.source_id == source_id]
        source_scores = [
            r.data_quality_score for r in source_records if r.data_quality_score is not None
        ]
        if source_scores:
            source_quality[source_id] = sum(source_scores) / len(source_scores)

    return QualityReport(
        dataset_version=dataset_version,
        generated_at=datetime.now(UTC).isoformat() + "Z",
        total_records=len(records),
        valid_records=validation_report.valid_records,
        invalid_records=validation_report.invalid_records,
        duplicate_records=validation_report.duplicate_records,
        missing_coordinates=validation_report.missing_coordinates,
        missing_dates=validation_report.missing_dates,
        unknown_categories=validation_report.unknown_categories,
        category_distribution=validation_report.category_distribution,
        geographic_distribution=validation_report.geographic_distribution,
        temporal_distribution=validation_report.temporal_distribution,
        source_distribution=validation_report.source_distribution,
        verification_distribution=validation_report.verification_distribution,
        quality_distribution=validation_report.quality_distribution,
        errors_by_type=validation_report.errors_by_type,
        mean_quality_score=mean_quality,
        median_quality_score=median_quality,
        source_quality=source_quality,
        processing_version=processing_version,
    )


def save_quality_report(report: QualityReport, output_dir: str) -> tuple[str, str]:
    """Save quality report as JSON and HTML."""
    import json
    from pathlib import Path

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"quality_report_{report.dataset_version}.json"
    html_path = out_dir / f"quality_report_{report.dataset_version}.html"

    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    html_path.write_text(report.to_html(), encoding="utf-8")

    return str(json_path), str(html_path)
