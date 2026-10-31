"""Day 11 evaluation using only the local Ollama native API."""
import argparse
import csv
import hashlib
import http.client
import json
import platform
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from day11_attack_cases import ATTACK_CASES, ATTACK_MARKER
from day11_messages import build_attack_messages, build_messages
from day11_retrieval import DOCUMENTS
from day14_trials import SYSTEM_PROMPTS

COHORT = "day11_ollama_local_v1"
MODEL = "qwen3:4b-instruct"
ROOT = Path(__file__).resolve().parent / "ollama_runs"
LIMIT = 8 * 1024 * 1024


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def native_messages(messages):
    """Translate the simulated retrieval history to Ollama's native schema."""
    messages = deepcopy(messages)
    for message in messages:
        if message["role"] == "assistant":
            message["content"] = ""
            for call in message["tool_calls"]:
                call.pop("id")
                call.pop("type")
                call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        if message["role"] == "tool":
            message.pop("tool_call_id")
            message["tool_name"] = "retrieve_document"
    return messages


def make_plan(run_id, model=MODEL, seed=11):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError("Invalid run ID")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*:[a-z0-9][a-z0-9_.-]*", model) or "cloud" in model:
        raise ValueError("Use an explicit local model:tag without a registry or cloud suffix")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("Seed must be a nonnegative 32-bit integer")
    rows = []
    for dataset, cases in (("initial", DOCUMENTS), ("expanded", ATTACK_CASES)):
        for case_id, document in cases.items():
            for condition, prompt in SYSTEM_PROMPTS.items():
                messages = (build_messages(case_id, prompt) if dataset == "initial"
                            else build_attack_messages(document, prompt))
                request = dict(model=model, messages=native_messages(messages), stream=False,
                               options=dict(temperature=0, seed=seed, num_predict=200, num_ctx=4096))
                rows.append(dict(trial_id=f"{dataset}:{case_id}:{condition}", dataset=dataset,
                                 case_id=case_id, kind="control" if dataset == "initial" and case_id != "incident" else "attack",
                                 condition=condition, request=request, request_sha256=fingerprint(request)))
    return dict(schema_version=1, run_id=run_id, provider="ollama_local", cohort=COHORT,
                endpoint="http://127.0.0.1:11434", model=model, seed=seed,
                dataset_sha256=fingerprint(dict(initial=DOCUMENTS, expanded=ATTACK_CASES)),
                request_count=len(rows), requests=rows)


def local_request(method, path, payload=None):
    """No URL overrides, proxies, redirects, authentication, or retries."""
    if (method, path) not in {("GET", "/api/status"), ("GET", "/api/tags"),
                              ("GET", "/api/version"), ("POST", "/api/chat")}:
        raise ValueError("Endpoint is not allowed")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=180)
    try:
        body = None if payload is None else json.dumps(payload).encode()
        connection.request(method, path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("Ollama response exceeds size limit")
        return response.status, raw
    finally:
        connection.close()


def decode(status, raw):
    if status != 200:
        raise ValueError(f"Ollama returned HTTP {status}")
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("error"):
        raise ValueError("Invalid Ollama response")
    return value


def save_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def run(run_id, model=MODEL, seed=11):
    plan = make_plan(run_id, model, seed)
    ROOT.mkdir(parents=True, exist_ok=True)
    directory = ROOT / run_id
    directory.mkdir()  # Reserve the run before any network request; never resume implicitly.
    save_json(directory / "plan.json", plan)
    try:
        source_root = Path(__file__).resolve().parent
        source_files = ("ollama_evaluate.py", "day11_attack_cases.py", "day11_messages.py",
                        "day11_retrieval.py", "day14_trials.py")
        metadata = dict(python=platform.python_version(), platform=platform.platform(),
                        source_sha256={name: hashlib.sha256((source_root / name).read_bytes()).hexdigest()
                                       for name in source_files})
        for name in ("status", "tags", "version"):
            status, raw = local_request("GET", f"/api/{name}")
            (directory / f"{name}.raw.json").write_bytes(raw)
            metadata[name] = decode(status, raw)
            if name == "status" and metadata[name].get("cloud", {}).get("disabled") is not True:
                raise ValueError("Ollama must report cloud.disabled=true; disable cloud and restart it")
        matches = [m for m in metadata["tags"].get("models", []) if m.get("name") == model]
        if len(matches) != 1:
            raise ValueError("Requested model must already exist locally; no automatic pulls")
        selected = matches[0]
        if (selected.get("remote_host") or selected.get("remote_model")
                or not selected.get("digest") or not selected.get("size", 0) > 0):
            raise ValueError("Model must have local weights and a digest, without remote routing")
        metadata["model_digest"] = selected["digest"]
        save_json(directory / "metadata.json", metadata)
        reviews = directory / "reviews.csv"
        fields = ["trial_id", "provider", "cohort", "model", "model_digest", "dataset", "case_id",
                  "kind", "condition", "request_sha256", "raw_sha256", "response", "marker_present",
                  "done_reason", "attack_success", "task_completed", "reviewer", "reviewed_at", "review_notes"]
        with reviews.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index, trial in enumerate(plan["requests"], 1):
                status, raw = local_request("POST", "/api/chat", trial["request"])
                raw_path = directory / f"response_{index:02d}.raw.json"
                with raw_path.open("xb") as output:
                    output.write(raw)
                save_json(directory / f"response_{index:02d}.status.json", dict(status=status, trial_id=trial["trial_id"]))
                result = decode(status, raw)
                message = result.get("message", {})
                if (result.get("done") is not True or result.get("model") != model
                        or not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls")
                        or not isinstance(message.get("content"), str) or not message["content"].strip()):
                    raise ValueError("Expected a completed assistant text response from the requested model")
                row = {key: trial[key] for key in ("trial_id", "dataset", "case_id", "kind", "condition", "request_sha256")}
                row.update(provider=plan["provider"], cohort=COHORT, model=model,
                           model_digest=selected["digest"], raw_sha256=hashlib.sha256(raw).hexdigest(),
                           response=message["content"], marker_present=ATTACK_MARKER in message["content"],
                           done_reason=result.get("done_reason", ""))
                writer.writerow(row)
                stream.flush()
        save_json(directory / "complete.json", dict(completed=len(plan["requests"]), timestamp=datetime.now(timezone.utc).isoformat()))
    except Exception as error:
        save_json(directory / "error.json", dict(error_type=type(error).__name__, message=str(error),
                                                timestamp=datetime.now(timezone.utc).isoformat()))
        raise
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--execute-local", action="store_true", help="Explicitly enable local inference")
    args = parser.parse_args()
    if args.execute_local:
        print(run(args.run_id, args.model, args.seed))
    else:
        print(json.dumps(make_plan(args.run_id, args.model, args.seed), indent=2))


if __name__ == "__main__":
    main()
