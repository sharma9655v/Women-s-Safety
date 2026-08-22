"""Export dataset to various formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ml.data.config.schema import DatasetRecord


def export_csv(records: list[DatasetRecord], output_path: Path) -> Path:
    """Export records to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        output_path.write_text("", encoding="utf-8")
        return output_path

    fieldnames = DatasetRecord.field_names()

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())

    return output_path


def export_parquet(records: list[DatasetRecord], output_path: Path) -> Path:
    """Export records to Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        # Create empty parquet with schema
        schema = pa.schema(
            [
                ("record_id", pa.string()),
                ("source_id", pa.string()),
                ("source_name", pa.string()),
                ("source_type", pa.string()),
                ("crime_category", pa.string()),
                ("crime_subcategory", pa.string()),
                ("incident_date", pa.string()),
                ("incident_time", pa.string()),
                ("latitude", pa.float64()),
                ("longitude", pa.float64()),
                ("district", pa.string()),
                ("city", pa.string()),
                ("state", pa.string()),
                ("country", pa.string()),
                ("description_available", pa.bool_()),
                ("verification_state", pa.string()),
                ("source_url", pa.string()),
                ("collection_timestamp", pa.string()),
                ("geocoding_method", pa.string()),
                ("geocoding_confidence", pa.float64()),
                ("spatial_precision", pa.string()),
                ("data_quality_score", pa.float64()),
                ("dataset_version", pa.string()),
                ("original_category", pa.string()),
                ("original_source_record_id", pa.string()),
                ("processing_version", pa.string()),
            ]
        )
        table = pa.Table.from_pydict({field: [] for field in schema.names}, schema=schema)
    else:
        data = [record.to_dict() for record in records]
        table = pa.Table.from_pylist(data)

    pq.write_table(table, output_path, compression="snappy")
    return output_path


def export_jsonl(records: list[DatasetRecord], output_path: Path) -> Path:
    """Export records to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict()) + "\n")

    return output_path


def export_features_parquet(
    records: list[DatasetRecord],
    features: dict[str, dict[str, float]],
    output_path: Path,
) -> Path:
    """Export features to Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        output_path.write_bytes(b"")
        return output_path

    rows = []
    for record in records:
        feat = features.get(record.record_id, {})
        row = {
            "record_id": record.record_id,
            **feat,
        }
        rows.append(row)

    table = pa.Table.from_pylist(rows)
    pq.write_table(table, output_path, compression="snappy")
    return output_path


def export_all_formats(
    records: list[DatasetRecord],
    features: dict[str, dict[str, float]] | None,
    output_dir: Path,
    dataset_version: str,
) -> dict[str, Path]:
    """Export dataset in all formats."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # CSV
    csv_path = output_dir / f"processed_{dataset_version}.csv"
    results["csv"] = export_csv(records, csv_path)

    # Parquet
    parquet_path = output_dir / f"processed_{dataset_version}.parquet"
    results["parquet"] = export_parquet(records, parquet_path)

    # JSONL
    jsonl_path = output_dir / f"processed_{dataset_version}.jsonl"
    results["jsonl"] = export_jsonl(records, jsonl_path)

    # Features Parquet
    if features:
        features_path = output_dir / f"features_{dataset_version}.parquet"
        results["features_parquet"] = export_features_parquet(records, features, features_path)

    return results
