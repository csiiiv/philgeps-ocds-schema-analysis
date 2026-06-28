"""Run libcoveocds validation and normalize error shapes across versions."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from typing import Any


def count_validation_errors(raw_errors: list) -> int:
    """Count individual validation errors (handles dict and tuple formats)."""
    n = 0
    for err in raw_errors or []:
        if isinstance(err, dict):
            n += 1
        elif isinstance(err, (list, tuple)) and err:
            paths = err[1] if len(err) > 1 else []
            n += len(paths) if isinstance(paths, list) else 1
        else:
            n += 1
    return n


def extract_first_errors(raw_errors: list, *, limit: int = 5) -> list[dict]:
    """Normalize libcoveocds errors into a stable list of dicts."""
    out: list[dict] = []
    for err in (raw_errors or [])[:limit]:
        if isinstance(err, dict):
            out.append({
                "type": err.get("type") or err.get("message_type"),
                "description": err.get("description") or err.get("message"),
                "path": err.get("path") or err.get("field"),
            })
        elif isinstance(err, (list, tuple)) and err:
            head = err[0]
            if isinstance(head, str):
                try:
                    parsed = json.loads(head)
                    out.append({
                        "type": parsed.get("message_type"),
                        "description": parsed.get("message"),
                        "path": err[1][0].get("path") if err[1:] and err[1] else None,
                    })
                    continue
                except json.JSONDecodeError:
                    pass
            out.append({"raw": str(err)[:200]})
        else:
            out.append({"raw": str(err)[:200]})
    return out


def validation_error_type_counts(raw_errors: list) -> list[dict]:
    """Group libcoveocds errors by type/message for unified rule_counts."""
    counter: Counter[str] = Counter()
    for err in raw_errors or []:
        if isinstance(err, dict):
            key = err.get("type") or err.get("message_type") or err.get("description") or "validation_error"
            counter[str(key)] += 1
        elif isinstance(err, (list, tuple)) and err:
            paths = err[1] if len(err) > 1 else []
            n = len(paths) if isinstance(paths, list) else 1
            etype = "validation_error"
            head = err[0]
            if isinstance(head, str):
                try:
                    etype = json.loads(head).get("message_type") or etype
                except json.JSONDecodeError:
                    pass
            counter[etype] += n
        else:
            counter["validation_error"] += 1
    return [
        {"rule": rule, "severity": "error", "layer": "ocds_validation", "count": count}
        for rule, count in counter.most_common()
    ]


def run_ocds_validation(package: dict) -> dict[str, Any]:
    """Validate an OCDS release package with libcoveocds.

    Returns a dict with validation results. On import/runtime failure, sets
    ``available`` to False and ``error`` to the exception message.
    """
    try:
        from libcoveocds.api import common_checks_ocds
        from libcoveocds.config import LibCoveOCDSConfig
        from libcoveocds.schema import SchemaOCDS
    except ImportError as exc:
        return {
            "available": False,
            "passed": None,
            "error": f"libcoveocds not installed: {exc}",
            "validation_errors": [],
            "additional_checks": [],
            "conformance_errors": {},
            "deprecated_fields": {},
            "validation_stats": None,
        }

    config = LibCoveOCDSConfig()
    config.config["schema_version"] = "1.1"
    config.config["context"] = "api"

    schema_obj = SchemaOCDS(select_version="1.1", package_data=package, lib_cove_ocds_config=config)

    with tempfile.TemporaryDirectory() as tmp:
        results: dict[str, Any] = {
            "file_type": "json",
            "validation_errors": [],
            "validation_errors_count": 0,
            "additional_fields_count": 0,
            "additional_fields": {},
            "data_only": [],
            "deprecated_fields": {},
            "extensions": {},
            "additional_checks": [],
            "common_async_items": [],
        }
        try:
            common_checks_ocds(
                context=results,
                upload_dir=tmp,
                json_data=package,
                schema_obj=schema_obj,
                cache=False,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "available": True,
                "passed": False,
                "error": str(exc),
                "validation_errors": [],
                "additional_checks": [],
                "conformance_errors": {},
                "deprecated_fields": {},
                "validation_stats": None,
            }

    validation_errors = results.get("validation_errors") or []
    additional_checks = results.get("additional_checks") or []
    conformance_errors = results.get("conformance_errors") or {}
    deprecated = results.get("deprecated_fields") or {}
    val_count = count_validation_errors(validation_errors)
    conf_count = len(conformance_errors) if isinstance(conformance_errors, dict) else 0

    return {
        "available": True,
        "passed": val_count == 0 and conf_count == 0,
        "error": None,
        "validation_error_count": val_count,
        "validation_error_groups": len(validation_errors),
        "additional_checks_count": len(additional_checks),
        "conformance_error_count": conf_count,
        "deprecated_field_count": len(deprecated) if isinstance(deprecated, dict) else 0,
        "validation_errors": validation_errors,
        "additional_checks": additional_checks,
        "conformance_errors": conformance_errors,
        "deprecated_fields": deprecated,
        "validation_stats": results.get("validation_stats"),
        "first_errors": extract_first_errors(validation_errors, limit=15),
        "error_type_counts": validation_error_type_counts(validation_errors),
    }
