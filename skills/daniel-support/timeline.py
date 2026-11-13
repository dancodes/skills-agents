#!/usr/bin/env python3
"""Print the request timeline of one session from Tempo traces, through gcx."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

STATUS_KEYS = ("http.status_code", "http.response.status_code")
CONTEXT = []


def gcx(*args):
    result = subprocess.run(["gcx", *args, *CONTEXT, "-o", "json"], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"gcx {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
    return json.loads(result.stdout)


def value(attribute):
    raw = attribute.get("value") or {}
    return next(iter(raw.values()), None)


def spans(trace):
    for resource_spans in trace["trace"].get("resourceSpans", []):
        resource = {a["key"]: value(a) for a in resource_spans["resource"].get("attributes", [])}
        for scope_spans in resource_spans.get("scopeSpans", []):
            for span in scope_spans.get("spans", []):
                yield resource, span


def summarize(trace_id, request_key, request_chars):
    request, status, errors, services = None, None, [], set()
    for resource, span in spans(gcx("traces", "get", trace_id)):
        services.add(resource.get("service.name"))
        attributes = {a["key"]: value(a) for a in span.get("attributes", [])}
        request = request or attributes.get(request_key)
        status = status or next((attributes[k] for k in STATUS_KEYS if k in attributes), None)
        if span.get("status", {}).get("code") in (2, "STATUS_CODE_ERROR"):
            errors.append(span.get("status", {}).get("message") or span["name"])
        for event in span.get("events", []):
            message = {a["key"]: value(a) for a in event.get("attributes", [])}.get("exception.message")
            if message:
                errors.append(message)
    if request and request_chars and len(request) > request_chars:
        request = request[:request_chars] + f"... ({len(request)} chars)"
    return request, status, sorted(s for s in services if s), list(dict.fromkeys(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("value", help="the session id (or other attribute value) to follow")
    parser.add_argument("--attr", required=True, help="TraceQL attribute that holds the value, e.g. span.session_id")
    parser.add_argument("--request-attr", default="request", help="span attribute that holds the request body")
    parser.add_argument("--since", default="24h")
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to")
    parser.add_argument("--chars", type=int, default=300, help="cut request bodies to this length, 0 for full")
    parser.add_argument("--limit", type=int, default=200, help="most traces to fetch; Tempo caps 0 at 20")
    parser.add_argument("--context", help="gcx context name")
    args = parser.parse_args()

    window = ["--from", args.start] + (["--to", args.to] if args.to else []) if args.start else ["--since", args.since]
    CONTEXT.extend(["--context", args.context] if args.context else [])
    query = f'{{ {args.attr} = "{args.value}" }}'
    found = gcx("traces", "query", query, "--limit", str(args.limit), *window).get("traces", [])
    found.sort(key=lambda t: int(t["startTimeUnixNano"]))
    print(f"{len(found)} traces for {query}")
    if len(found) >= args.limit:
        print(f"WARNING hit --limit {args.limit}; the timeline has gaps. Narrow --from/--to or raise --limit.")

    for trace in found:
        started = datetime.fromtimestamp(int(trace["startTimeUnixNano"]) / 1e9, timezone.utc)
        request, status, services, errors = summarize(trace["traceID"], args.request_attr, args.chars)
        print(f"\n{started:%Y-%m-%d %H:%M:%S.%f}"[:-3] + f"Z  {status or '-'}  {trace.get('durationMs', 0)}ms  "
              f"{trace.get('rootTraceName')}  [{trace['traceID']}]  {','.join(services)}")
        for error in errors:
            print(f"  ERROR {error}")
        if request:
            print(f"  request {request}")


if __name__ == "__main__":
    main()
