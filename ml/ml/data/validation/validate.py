"""Validation pipeline for dataset records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ml.data.config.schema import (
    REQUIRED_FIELDS,
    VALIDATION_RULES,
    CrimeCategory,
    DatasetRecord,
    GeocodingMethod,
    SourceType,
    VerificationState,
)


@dataclass
class ValidationResult:
    """Result of validating a record."""

    record_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Aggregate validation report for a batch."""

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
    validated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class Validator:
    """Validate normalized records against schema and rules."""

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate(self, record: DatasetRecord) -> ValidationResult:
        """Validate a single record."""
        errors = []
        warnings = []

        # Check required fields
        for field_name in REQUIRED_FIELDS:
            value = getattr(record, field_name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field_name}")

        # Validate field types and ranges
        for field_name, rules in VALIDATION_RULES.items():
            value = getattr(record, field_name, None)
            if value is not None:
                field_errors = self._validate_field(field_name, value, rules)
                errors.extend(field_errors)

        # Validate enums
        if record.source_type and record.source_type not in [e.value for e in SourceType]:
            errors.append(f"Invalid source_type: {record.source_type}")

        if record.crime_category and record.crime_category not in [e.value for e in CrimeCategory]:
            warnings.append(f"Unknown crime_category: {record.crime_category}")

        if record.verification_state and record.verification_state not in [
            e.value for e in VerificationState
        ]:
            errors.append(f"Invalid verification_state: {record.verification_state}")

        if record.geocoding_method and record.geocoding_method not in [
            e.value for e in GeocodingMethod
        ]:
            warnings.append(f"Unknown geocoding_method: {record.geocoding_method}")

        # Coordinate validation
        if record.latitude is not None and record.longitude is not None:
            if not self._valid_coordinates(record.latitude, record.longitude):
                errors.append(
                    f"Coordinates out of bounds: lat={record.latitude}, lon={record.longitude}"
                )

        # Date validation
        if record.incident_date:
            try:
                datetime.strptime(record.incident_date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Invalid incident_date format: {record.incident_date}")

        # Time validation
        if record.incident_time:
            try:
                datetime.strptime(record.incident_time, "%H:%M:%S")
            except ValueError:
                warnings.append(f"Invalid incident_time format: {record.incident_time}")

        # Quality score validation
        if record.data_quality_score is not None:
            if not (0.0 <= record.data_quality_score <= 1.0):
                errors.append(f"data_quality_score out of range [0,1]: {record.data_quality_score}")

        return ValidationResult(
            record_id=record.record_id,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_field(self, field_name: str, value: Any, rules: dict[str, Any]) -> list[str]:
        errors = []
        expected_type = rules.get("type")

        if expected_type == "float":
            try:
                float_val = float(value)
                if "min" in rules and float_val < rules["min"]:
                    errors.append(f"{field_name} below minimum: {float_val} < {rules['min']}")
                if "max" in rules and float_val > rules["max"]:
                    errors.append(f"{field_name} above maximum: {float_val} > {rules['max']}")
            except (ValueError, TypeError):
                errors.append(f"{field_name} is not a valid float: {value}")

        elif expected_type == "date":
            try:
                datetime.strptime(str(value), rules.get("format", "%Y-%m-%d"))
            except ValueError:
                errors.append(f"{field_name} is not a valid date ({rules.get('format')}): {value}")

        elif expected_type == "time":
            try:
                datetime.strptime(str(value), rules.get("format", "%H:%M:%S"))
            except ValueError:
                errors.append(f"{field_name} is not a valid time ({rules.get('format')}): {value}")

        return errors

    def _valid_coordinates(self, lat: float, lon: float) -> bool:
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def validate_batch(
        self, records: list[DatasetRecord]
    ) -> tuple[list[DatasetRecord], ValidationReport]:
        """Validate a batch of records, returning valid records and report."""
        valid_records = []
        seen_ids = set()
        duplicate_count = 0

        report = ValidationReport(
            total_records=len(records),
            valid_records=0,
            invalid_records=0,
            duplicate_records=0,
            missing_coordinates=0,
            missing_dates=0,
            unknown_categories=0,
        )

        for record in records:
            # Check for duplicates
            if record.record_id in seen_ids:
                duplicate_count += 1
                report.duplicate_records += 1
                continue
            seen_ids.add(record.record_id)

            result = self.validate(record)

            if result.valid:
                valid_records.append(record)
                report.valid_records += 1
            else:
                report.invalid_records += 1

            # Aggregate statistics
            if record.latitude is None or record.longitude is None:
                report.missing_coordinates += 1

            if not record.incident_date:
                report.missing_dates += 1

            if record.crime_category == CrimeCategory.OTHER.value:
                report.unknown_categories += 1

            # Category distribution
            cat = record.crime_category or "unknown"
            report.category_distribution[cat] = report.category_distribution.get(cat, 0) + 1

            # Geographic distribution (by state)
            if record.state:
                report.geographic_distribution[record.state] = (
                    report.geographic_distribution.get(record.state, 0) + 1
                )

            # Temporal distribution (by month)
            if record.incident_date:
                try:
                    month = record.incident_date[:7]  # YYYY-MM
                    report.temporal_distribution[month] = (
                        report.temporal_distribution.get(month, 0) + 1
                    )
                except Exception:
                    pass

            # Source distribution
            report.source_distribution[record.source_id] = (
                report.source_distribution.get(record.source_id, 0) + 1
            )

            # Verification distribution
            vs = record.verification_state or "unknown"
            report.verification_distribution[vs] = report.verification_distribution.get(vs, 0) + 1

            # Quality distribution (binned)
            if record.data_quality_score is not None:
                bin_key = f"{int(record.data_quality_score * 10) / 10:.1f}"
                report.quality_distribution[bin_key] = (
                    report.quality_distribution.get(bin_key, 0) + 1
                )

            # Errors by type
            for error in result.errors:
                error_type = error.split(":")[0] if ":" in error else error
                report.errors_by_type[error_type] = report.errors_by_type.get(error_type, 0) + 1

        return valid_records, report


def validate_records(
    records: list[DatasetRecord], strict_mode: bool = True
) -> tuple[list[DatasetRecord], ValidationReport]:
    """Convenience function to validate a batch of records."""
    validator = Validator(strict_mode=strict_mode)
    return validator.validate_batch(records)
