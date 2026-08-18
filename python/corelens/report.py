"""Export readable reports with escaped content and raw artifact provenance."""
import html
import json
from pathlib import Path


def rows(data):
    variants = data.get("variants", {"workload": data})
    result = []
    for name, variant in variants.items():
        summary = variant["summary"]
        runtime = summary["runtime_seconds"]
        comparison = data.get("comparisons", {}).get(name, {})
        interval = comparison.get("ci95")
        result.append([name, f"{runtime['median']:.6g}", str(runtime["count"]),
                       f"{summary['throughput_per_second']:.6g}" if summary["throughput_per_second"] else "unavailable",
                       f"{comparison['speedup']:.3f}x" if comparison else "baseline",
                       f"[{interval[0]:.3f}, {interval[1]:.3f}]" if interval else "--",
                       comparison.get("verdict", "--")])
    return result


def render(data, format="html"):
    headers = ["Variant", "Median seconds", "Runs", "Units / second", "Speedup", "95% interval", "Verdict"]
    table = rows(data)
    caveat = ("Runtime includes process startup and output capture. Hardware counters come from separate perf trials. "
              "Intervals describe sampling noise on the supplied workload; exact stdout checks cover only those inputs.")
    if format == "markdown":
        escape = lambda s: str(s).replace("|", r"\|").replace("\n", " ").replace("`", "'")
        lines = ["# CoreLens performance report", "", caveat, "", "| " + " | ".join(headers) + " |",
                 "| " + " | ".join("---" for _ in headers) + " |"]
        lines.extend("| " + " | ".join(escape(v) for v in row) + " |" for row in table)
        lines.extend(["", "## Hardware counter differences", "", "| Variant | Event | Relative change |", "| --- | --- | --- |"])
        for name, comparison in data.get("comparisons", {}).items():
            for event, value in comparison.get("counter_deltas", {}).items():
                delta = value["relative_change"]
                lines.append(f"| {escape(name)} | {escape(event)} | {delta:+.2%} |" if delta is not None else f"| {escape(name)} | {escape(event)} | unavailable |")
        return "\n".join(lines) + "\n"
    if format != "html":
        raise ValueError("report format must be html or markdown")
    head = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CoreLens performance report</title><style>
body{font:16px system-ui,sans-serif;background:#0d1523;color:#e5edf8;max-width:1100px;margin:40px auto;padding:0 24px}
h1{color:#77d7ed}table{border-collapse:collapse;width:100%;margin:24px 0}th,td{padding:12px;text-align:left;border-bottom:1px solid #35465e}
th{color:#94d3ff}p{line-height:1.6;color:#b5c5d9}pre{overflow:auto;background:#152238;padding:16px}summary{cursor:pointer}</style><body>
<h1>CoreLens performance report</h1>"""
    head += "<p>" + html.escape(caveat) + "</p><table><thead><tr>"
    head += "".join("<th>" + html.escape(h) + "</th>" for h in headers) + "</tr></thead><tbody>"
    head += "".join("<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in row) + "</tr>" for row in table)
    head += "</tbody></table><h2>Hardware counter differences</h2><table><tr><th>Variant</th><th>Event</th><th>Relative change</th></tr>"
    for name, comparison in data.get("comparisons", {}).items():
        for event, value in comparison.get("counter_deltas", {}).items():
            delta = value["relative_change"]
            head += "<tr>" + "".join("<td>" + html.escape(v) + "</td>" for v in [name, event, f"{delta:+.2%}" if delta is not None else "unavailable"]) + "</tr>"
    return head + "</table><details><summary>Raw measurements and build provenance</summary><pre>" + html.escape(json.dumps(data, indent=2)) + "</pre></details></body></html>"


def export(input_path, output_path, format):
    from .results import load, validate_report
    data = validate_report(load(input_path))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data, format), encoding="utf-8")
    return {"report": str(target.resolve()), "format": format}
