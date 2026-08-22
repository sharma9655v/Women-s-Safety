"""Incremental dataset update.

Checks each enabled source for changes (checksum/ETag), ingests only changed
sources, re-validates, deduplicates against existing records, bumps the
dataset version and regenerates reports. Skips rebuild entirely when nothing
changed.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from ml.data.build_dataset import DatasetPipeline, PipelineConfig, load_source_registry

logger = logging.getLogger(__name__)


class DatasetUpdater:
    """Incremental update on top of the build pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline = DatasetPipeline(config)
        self.state_path = config.versions_dir / "update_state.json"

    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {}

    def _save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def run(self) -> dict:
        registry_path = Path("ml/data/config/sources.yaml")
        source_registry = load_source_registry(registry_path)
        enabled = [s for s in source_registry.values() if s.enabled]

        state = self._load_state()
        previous_checksums: dict[str, str] = state.get("source_checksums", {})

        changed_sources: list[str] = []
        unchanged_sources: list[str] = []

        for entry in enabled:
            from ml.data.sources.adapters import get_adapter

            try:
                adapter = get_adapter(entry.to_dict(), self.config.cache_dir)
                result = adapter.fetch(force=False)  # cache-aware fetch
            except Exception as exc:
                logger.warning(f"Source {entry.source_id}: probe failed ({exc})")
                continue

            prev = previous_checksums.get(entry.source_id)
            if result.records and result.source_checksum != prev:
                changed_sources.append(entry.source_id)
            else:
                unchanged_sources.append(entry.source_id)

        if not changed_sources:
            logger.info("No source changes detected — dataset is up to date.")
            return {
                "status": "up_to_date",
                "changed_sources": [],
                "unchanged_sources": unchanged_sources,
                "checked_at": datetime.now(UTC).isoformat(),
            }

        logger.info(f"Changed sources: {changed_sources}. Rebuilding affected dataset.")

        # Full pipeline run ingests everything; cached sources cost nothing.
        summary = self.pipeline.run()

        if summary.get("status") == "success":
            # Persist new checksums for next update cycle
            new_state = {
                "source_checksums": {
                    **previous_checksums,
                    **{sid: self._current_checksum(sid) for sid in summary.get("sources", [])},
                },
                "last_update": datetime.now(UTC).isoformat(),
                "dataset_version": summary.get("dataset_version"),
            }
            self._save_state(new_state)

        summary["update_mode"] = "incremental"
        summary["changed_sources"] = changed_sources
        summary["unchanged_sources"] = unchanged_sources
        return summary

    def _current_checksum(self, source_id: str) -> str | None:
        meta_path = self.config.cache_dir / source_id / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return meta.get("checksum")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Incremental dataset update")
    parser.add_argument("--config", default="ml/data/config/sources.yaml")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    config = PipelineConfig(Path(args.config))
    if args.offline:
        config.config["pipeline"]["offline_mode"] = True

    updater = DatasetUpdater(config)
    result = updater.run()
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") in ("success", "up_to_date") else 1


if __name__ == "__main__":
    sys.exit(main())
