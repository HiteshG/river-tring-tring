"""
Run Evaluation — Batch Evaluator for Production Conversations
==============================================================
Evaluates conversations from data/production_logs.jsonl
and writes results to violation_rating.jsonl.

Features:
  - LLM mode: 'combined' (1 call, fast) or 'separate' (3 calls, thorough)
  - Random sampling: evaluate a random subset instead of all 700
  - Concurrent processing (multiple conversations in parallel)
  - Real-time progress with ETA
  - Resume support (skips already-evaluated conversations)
  - Rate limiting for Gemini API calls
  - Error handling with per-conversation fault tolerance

Usage:
    python run_evaluation.py                              # All 700, combined mode
    python run_evaluation.py --mode separate               # All 700, separate (thorough) mode
    python run_evaluation.py --sample 50                   # Random 50 conversations
    python run_evaluation.py --sample 100 --mode separate  # Random 100, thorough mode
    python run_evaluation.py --limit 50                    # First 50 (sequential, no shuffle)
    python run_evaluation.py --workers 3                   # 3 concurrent workers
    python run_evaluation.py --resume                      # Resume from previous run
    python run_evaluation.py --sample 50 --seed 42         # Reproducible random sample
"""

import json
import sys
import time
import random
import threading
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from eval_takehome import AgentEvaluator


INPUT_FILE = Path("data/production_logs.jsonl")
OUTPUT_FILE = Path("violation_rating.jsonl")


def load_conversations(path: Path) -> list[dict]:
    """Load all conversations from JSONL file."""
    conversations = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                conversations.append(json.loads(line))
    return conversations


def load_completed_ids(path: Path) -> set[str]:
    """Load conversation IDs already evaluated (for resume support)."""
    if not path.exists():
        return set()
    completed = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    completed.add(data.get("conversation_id", ""))
                except json.JSONDecodeError:
                    continue
    return completed


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


def evaluate_one(evaluator: AgentEvaluator, conv: dict) -> dict:
    """Evaluate a single conversation (thread-safe target)."""
    result = evaluator.evaluate(conv)
    result["conversation_id"] = conv["conversation_id"]
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate production conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_evaluation.py --sample 50                  # Random 50, fast mode
  python run_evaluation.py --mode separate --sample 20  # Random 20, thorough mode
  python run_evaluation.py --resume --workers 5         # Resume with 5 workers
  python run_evaluation.py --sample 100 --seed 42       # Reproducible sample
        """
    )
    parser.add_argument("--mode", choices=["combined", "separate"], default="combined",
                        help="LLM evaluation mode: 'combined' (1 call, faster) or 'separate' (3 calls, more thorough). Default: combined")
    parser.add_argument("--sample", type=int, default=None,
                        help="Randomly sample N conversations (instead of evaluating all)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible sampling (use with --sample)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Evaluate first N conversations sequentially (no shuffle)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous run (skip already evaluated)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Number of concurrent workers (default: 5)")
    args = parser.parse_args()

    if args.sample and args.limit:
        print("ERROR: Cannot use both --sample and --limit. Use one or the other.")
        sys.exit(1)

    # ── Load data ──────────────────────────────────────────────────────
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found.")
        sys.exit(1)

    print(f"Loading conversations from {INPUT_FILE}...")
    conversations = load_conversations(INPUT_FILE)
    total_available = len(conversations)
    print(f"  Found {total_available} conversations.")
    print(f"  Mode: {args.mode} ({'1 LLM call/conv' if args.mode == 'combined' else '3 LLM calls/conv'})")

    # ── Resume support ─────────────────────────────────────────────────
    completed_ids = set()
    if args.resume:
        completed_ids = load_completed_ids(OUTPUT_FILE)
        print(f"  Resume: {len(completed_ids)} already completed.")

    # Filter out completed
    pending = [c for c in conversations if c["conversation_id"] not in completed_ids]

    # ── Random sampling ────────────────────────────────────────────────
    if args.sample:
        if args.seed is not None:
            random.seed(args.seed)
            print(f"  Random seed: {args.seed}")
        sample_size = min(args.sample, len(pending))
        pending = random.sample(pending, sample_size)
        print(f"  Randomly sampled {sample_size} conversations.")

    # ── Sequential limit ───────────────────────────────────────────────
    elif args.limit:
        pending = pending[:args.limit]

    total_to_eval = len(pending)
    if total_to_eval == 0:
        print("Nothing to evaluate. All conversations already processed.")
        return

    print(f"  Will evaluate {total_to_eval} conversations with {args.workers} workers.\n")
    print("=" * 72)

    # ── Initialize evaluator ───────────────────────────────────────────
    evaluator = AgentEvaluator(mode=args.mode)

    # ── Thread-safe output ─────────────────────────────────────────────
    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    completed_count = [0]
    error_count = [0]
    total_violations = [0]
    start_time = time.time()

    # Open output file
    mode = "a" if args.resume else "w"
    out_f = open(OUTPUT_FILE, mode)

    def write_result(result: dict):
        with write_lock:
            out_f.write(json.dumps(result) + "\n")
            out_f.flush()

    def update_progress(cid: str, n_violations: int, error: bool = False):
        with progress_lock:
            if error:
                error_count[0] += 1
            else:
                completed_count[0] += 1
                total_violations[0] += n_violations

            done = completed_count[0] + error_count[0]
            elapsed = time.time() - start_time
            avg_time = elapsed / max(done, 1)
            remaining = avg_time * (total_to_eval - done)

            pct = done / total_to_eval * 100
            bar_len = 30
            filled = int(bar_len * done / total_to_eval)
            bar = "█" * filled + "░" * (bar_len - filled)

            print(
                f"\r  [{bar}] {pct:5.1f}% | "
                f"{done}/{total_to_eval} | "
                f"ETA: {format_duration(remaining)} | "
                f"✓{completed_count[0]} ✗{error_count[0]} | "
                f"{cid[:12]}  ",
                end="", flush=True
            )

    # ── Concurrent evaluation ──────────────────────────────────────────
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {}
            for conv in pending:
                cid = conv["conversation_id"]
                future = executor.submit(evaluate_one, evaluator, conv)
                futures[future] = cid

            for future in as_completed(futures):
                cid = futures[future]
                try:
                    result = future.result()
                    write_result(result)
                    update_progress(cid, len(result["violations"]))
                except Exception as e:
                    error_result = {
                        "conversation_id": cid,
                        "quality_score": None,
                        "risk_score": None,
                        "violations": [],
                        "error": str(e),
                    }
                    write_result(error_result)
                    update_progress(cid, 0, error=True)
                    print(f"\n    ERROR on {cid}: {e}")

    except KeyboardInterrupt:
        print(f"\n\n⚠  Interrupted by user after {completed_count[0]} conversations.")
        print(f"   Progress saved to {OUTPUT_FILE}. Run with --resume to continue.")
    finally:
        out_f.close()

    # ── Summary ────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n\n" + "=" * 72)
    print("EVALUATION COMPLETE")
    print("=" * 72)
    print(f"  Mode:                    {args.mode}")
    print(f"  Conversations evaluated: {completed_count[0]}")
    print(f"  Errors:                  {error_count[0]}")
    print(f"  Total violations found:  {total_violations[0]}")
    print(f"  Time elapsed:            {format_duration(elapsed)}")
    if completed_count[0] > 0:
        print(f"  Avg per conversation:    {elapsed / completed_count[0]:.1f}s")
    print(f"  Output:                  {OUTPUT_FILE}")
    print()

    if completed_count[0] > 0:
        results = []
        with open(OUTPUT_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("quality_score") is not None:
                        results.append(r)

        if results:
            avg_q = sum(r["quality_score"] for r in results) / len(results)
            avg_r = sum(r["risk_score"] for r in results) / len(results)
            total_v = sum(len(r["violations"]) for r in results)
            print(f"  Avg quality score: {avg_q:.3f}")
            print(f"  Avg risk score:    {avg_r:.3f}")
            print(f"  Total violations:  {total_v}")
            print()

    print(f"Next step: python3 generate_violations_report.py")


if __name__ == "__main__":
    main()
