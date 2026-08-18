"""Validate imported benchmark documents at the external input boundary."""
import json
import math
from pathlib import Path


def load(path):
    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid_constant)


def numeric(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def validate_benchmark(data):
    try:
        if data.get("schema_version") != 1:
            raise ValueError("unsupported result schema version")
        summary = data["summary"]
        runtime = summary["runtime_seconds"]
        if not numeric(runtime["median"]) or runtime["median"] < 0 or not isinstance(runtime["count"], int) or runtime["count"] < 2:
            raise ValueError("invalid runtime summary")
        throughput = summary["throughput_per_second"]
        if throughput is not None and (not numeric(throughput) or throughput < 0):
            raise ValueError("invalid throughput summary")
        if not isinstance(summary["derived"], dict) or not isinstance(summary["counters"], dict):
            raise ValueError("invalid counter summary")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("input must be a CoreLens benchmark result with a summary") from error
    return data


def validate_report(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("input must be a CoreLens schema_version 1 result")
    variants = data.get("variants")
    if variants is None:
        validate_benchmark(data)
    elif not isinstance(variants, dict) or not variants:
        raise ValueError("result variants must be a nonempty object")
    else:
        for variant in variants.values():
            validate_benchmark(variant)
    try:
        for comparison in data.get("comparisons", {}).values():
            interval = comparison["ci95"]
            if not numeric(comparison["speedup"]) or comparison["speedup"] <= 0 or len(interval) != 2 or any(not numeric(v) or v <= 0 for v in interval):
                raise ValueError("invalid speedup comparison")
            for delta in comparison.get("counter_deltas", {}).values():
                value = delta["relative_change"]
                if value is not None and not numeric(value):
                    raise ValueError("invalid counter delta")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("invalid comparison result") from error
    return data
