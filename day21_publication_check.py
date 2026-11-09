"""Read-only publication allowlist, ignore-rule and pattern-based privacy checks."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
STAGING_FILES = (
    "DAY26.md", "day26_lifecycle.py", "tests/test_day26_lifecycle.py",
    "DAY25.md", "day25_authorization.py", "tests/test_day25_authorization.py",
    "DAY24_PUBLICATION.md", "tests/test_day24_publication.py",
    'results/day24-offline-recovery-001/REPORT.md',
    'results/day24-offline-recovery-001/SHA256SUMS.json',
    'results/day24-offline-recovery-001/evidence.json',
    'results/day24-offline-recovery-001/provenance.json',
    'results/day24-offline-recovery-001/snapshot/day21_gate.py',
    'results/day24-offline-recovery-001/snapshot/day22_gate.py',
    'results/day24-offline-recovery-001/snapshot/day23_live_results.json',
    'results/day24-offline-recovery-001/snapshot/day23_plan.json',
    'results/day24-offline-recovery-001/snapshot/day23_plan.sha256',
    'results/day24-offline-recovery-001/snapshot/day24_cases.json',
    'results/day24-offline-recovery-001/snapshot/day24_offline.json',
    'results/day24-offline-recovery-001/snapshot/day24_owner_fixtures.json',
    'results/day24-offline-recovery-001/snapshot/day24_recovery.py',
    'results/day24-offline-recovery-001/snapshot/day24_replay.py',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/REPORT.md',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/SHA256SUMS.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/day21_gate.py',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/day22_gate.py',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/evidence.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/plan.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/plan.sha256',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/provenance.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/rejection_analysis.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/review_manifest.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/review_stage.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/reviews.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/run_manifest.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/summary.json',
    'results/day24-offline-recovery-001/snapshot/results/day23-local-qwen-001/verify.py',
    'results/day24-offline-recovery-001/snapshot/tests/test_day24_recovery.py',
    'results/day24-offline-recovery-001/summary.json',
    'results/day24-offline-recovery-001/verify.py',

    "DAY24.md", "day24_recovery.py", "day24_replay.py", "day24_cases.json",
    "day24_owner_fixtures.json", "day24_offline.json", "tests/test_day24_recovery.py",
    'results/day23-local-qwen-001/REPORT.md',
    'results/day23-local-qwen-001/SHA256SUMS.json',
    'results/day23-local-qwen-001/day21_gate.py',
    'results/day23-local-qwen-001/day22_gate.py',
    'results/day23-local-qwen-001/evidence.json',
    'results/day23-local-qwen-001/plan.json',
    'results/day23-local-qwen-001/plan.sha256',
    'results/day23-local-qwen-001/provenance.json',
    'results/day23-local-qwen-001/rejection_analysis.json',
    'results/day23-local-qwen-001/review_manifest.json',
    'results/day23-local-qwen-001/review_stage.json',
    'results/day23-local-qwen-001/reviews.json',
    'results/day23-local-qwen-001/run_manifest.json',
    'results/day23-local-qwen-001/summary.json',
    'results/day23-local-qwen-001/verify.py',
    'DAY23_PUBLICATION.md',
    'DAY24_PROPOSAL.md',
    'tests/test_day23_publication.py',

    "DAY23_LIVE.md", "day23_review.py", "day23_live_results.json", "tests/test_day23_review.py",
    "DAY23.md", "day23_evaluate.py", "day23_plan.json", "day23_plan.sha256",
    "day23_cases.json", "day23_offline.json", "tests/test_day23_evaluate.py",
    'tests/test_day22_publication.py',
    'DAY22_PUBLICATION.md',
    'results/day22-local-qwen-001/REPORT.md',
    'results/day22-local-qwen-001/SHA256SUMS.json',
    'results/day22-local-qwen-001/evidence.json',
    'results/day22-local-qwen-001/original_gate.py',
    'results/day22-local-qwen-001/provenance.json',
    'results/day22-local-qwen-001/summary.json',
    'results/day22-local-qwen-001/verify.py',

    "day22_live_regression.json", "DAY22.md", "day22_gate.py", "day22_analysis.py", "day22_facts.json",
    "day22_cases.json", "day22_replay.json", "tests/test_day22_gate.py",
    ".gitattributes", ".gitignore", ".github/workflows/python-tests.yml", "README.md",
    "DAY21.md", "DAY21_PUBLICATION.md", "day16_analysis.py", "tests/test_day16_defense.py",
    "day21_gate.py", "day21_live.py", "day21_analysis.py", "day21_replay.json",
    "day21_publication_check.py", "tests/test_day21_gate.py", "tests/test_day21_live.py",
    "results/day21-local-qwen-001/REPORT.md", "results/day21-local-qwen-001/cases.csv",
    "results/day21-local-qwen-001/evidence.json", "results/day21-local-qwen-001/provenance.json",
    "results/day21-local-qwen-001/summary.json", "results/day21-local-qwen-001/verify.py",
    "results/day21-local-qwen-001/SHA256SUMS.json",
)
PRIVATE_DIRS = ("day23_runs", "day21_runs", "day21_followup_checks", "ollama_runs", "day14_runs")
# Deliberately bounded patterns; this is not an exhaustive secret detector.
RULES = {
    "provider_token": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16})\b"),
    "private_key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "bearer_value": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_./+=-]{20,}"),
    "secret_assignment": re.compile(r'''(?i)["']?(?:api[_-]?key|secret|password|access[_-]?token)["']?\s*[:=]\s*["'][A-Za-z0-9_./+=-]{20,}["']'''),
    "personal_local_path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+"),
    "email_address": re.compile(r"\b[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode()


def scan_text(text):
    return [(name, text.count("\n", 0, match.start()) + 1)
            for name, pattern in RULES.items() for match in pattern.finditer(text)]


def check():
    files = set(STAGING_FILES)
    if len(files) != len(STAGING_FILES) or any(not (ROOT / p).is_file() for p in files):
        raise SystemExit("Missing/duplicate publication candidate")
    changed = set(git("diff", "--name-only").splitlines())
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    staged = set(git("diff", "--cached", "--name-only").splitlines())
    if (changed | untracked | staged) - files:
        raise SystemExit("Unexpected files outside explicit staging list")
    for folder in PRIVATE_DIRS:
        # Ignore rules do not protect already tracked files; check that too.
        if git("ls-files", "--", folder).strip():
            raise SystemExit("Private directory unexpectedly tracked: " + folder)
        subprocess.run(["git", "check-ignore", "-q", folder + "/publication-sentinel"], cwd=ROOT, check=True)
        for path in (ROOT / folder).rglob("*"):
            if path.is_file():
                subprocess.run(["git", "check-ignore", "-q", str(path.relative_to(ROOT))], cwd=ROOT, check=True)
    findings = []
    for path in STAGING_FILES:
        findings.extend((path, rule, line) for rule, line in scan_text((ROOT / path).read_text(encoding="utf-8")))
    if findings:
        # Never print matching values or possibly sensitive source lines.
        for path, rule, line in findings:
            print(f"{path}:{line}: {rule}")
        raise SystemExit("Pattern scan requires review")
    print(f"{len(STAGING_FILES)} explicit candidate files; no secret/path/email pattern findings.")
    print("New/private raw directories ignored and untracked; current changes fit the allowlist.")
    print("Legacy day15_runs contains already tracked history; ignore rules do not remove it.")
    print("No staging performed. Explicit git add -f can override ignore rules; do not use it.")


if __name__ == "__main__":
    check()
