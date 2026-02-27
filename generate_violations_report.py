"""
Generate Violations Report
============================
Reads violation_rating.jsonl + data/outcomes.jsonl to produce violations.md.

Analyzes:
  1. Most common violation types
  2. Correlation with bad outcomes (complaints, regulatory flags)
  3. Violation rates by borrower segment (language, DPD, zone)
  4. Specific conversation examples with evidence

Usage:
    python generate_violations_report.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


RATINGS_FILE = Path("violation_rating.jsonl")
OUTCOMES_FILE = Path("data/outcomes.jsonl")
LOGS_FILE = Path("data/production_logs.jsonl")
OUTPUT_FILE = Path("violations.md")


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_rule_category(rule: str) -> str:
    """Map a rule string to its high-level category."""
    rule_lower = rule.lower()
    if "invariant i1" in rule_lower or "invariant i2" in rule_lower:
        return "State Invariant"
    if "invariant i4" in rule_lower:
        return "Action-State Mismatch"
    if "invariant i5" in rule_lower or "classification" in rule_lower:
        return "Classification Accuracy"
    if "transition" in rule_lower or "section 4" in rule_lower:
        return "State Transition"
    if "section 4.3" in rule_lower or "escalation" in rule_lower:
        return "Missing Escalation"
    if "quiet" in rule_lower or "timing" in rule_lower or "section 6" in rule_lower:
        return "Timing"
    if "follow-up" in rule_lower or "spacing" in rule_lower:
        return "Follow-Up Spacing"
    if "dormancy" in rule_lower or "dormant" in rule_lower:
        return "Dormancy"
    if "amount" in rule_lower or "pos" in rule_lower or "tos" in rule_lower:
        return "Amount"
    if "compliance" in rule_lower or "section 8" in rule_lower:
        return "Compliance"
    if "q1" in rule_lower or "progress" in rule_lower:
        return "Quality: Progress"
    if "q2" in rule_lower:
        return "Quality: Classification Impact"
    if "q3" in rule_lower or "tone" in rule_lower:
        return "Quality: Tone"
    if "q4" in rule_lower or "context" in rule_lower:
        return "Quality: Context"
    if "q5" in rule_lower or "repetition" in rule_lower or "loop" in rule_lower:
        return "Quality: Repetition"
    if "quality" in rule_lower:
        return "Quality: Other"
    return "Other"


def severity_label(sev: float) -> str:
    """Human label for severity."""
    if sev >= 0.9:
        return "Critical"
    elif sev >= 0.7:
        return "High"
    elif sev >= 0.5:
        return "Medium"
    elif sev >= 0.3:
        return "Low"
    return "Minor"


def dpd_bucket(dpd: int) -> str:
    """Bucket DPD into ranges."""
    if dpd <= 30:
        return "0–30"
    elif dpd <= 60:
        return "31–60"
    elif dpd <= 90:
        return "61–90"
    elif dpd <= 180:
        return "91–180"
    return "180+"


def main():
    # ── Load data ──────────────────────────────────────────────────────
    if not RATINGS_FILE.exists():
        print(f"ERROR: {RATINGS_FILE} not found. Run 'python run_evaluation.py' first.")
        sys.exit(1)

    print("Loading evaluation results...")
    ratings = load_jsonl(RATINGS_FILE)
    ratings = [r for r in ratings if r.get("quality_score") is not None]
    print(f"  {len(ratings)} evaluated conversations.")

    # Collect the set of evaluated conversation IDs
    evaluated_ids = {r["conversation_id"] for r in ratings}

    print("Loading outcomes...")
    outcomes_list = load_jsonl(OUTCOMES_FILE)
    # Scope outcomes to ONLY evaluated conversations
    outcomes = {o["conversation_id"]: o for o in outcomes_list if o["conversation_id"] in evaluated_ids}
    print(f"  {len(outcomes)} matching outcomes (of {len(outcomes_list)} total).")

    print("Loading conversation metadata...")
    logs = load_jsonl(LOGS_FILE)
    # Scope metadata to ONLY evaluated conversations
    metadata = {c["conversation_id"]: c.get("metadata", {}) for c in logs if c["conversation_id"] in evaluated_ids}
    print(f"  {len(metadata)} matching metadata records.\n")

    # ── Analysis ───────────────────────────────────────────────────────
    all_violations = []
    conv_violations = {}  # cid → violations list
    conv_scores = {}  # cid → {quality, risk}

    for r in ratings:
        cid = r["conversation_id"]
        conv_violations[cid] = r["violations"]
        conv_scores[cid] = {
            "quality_score": r["quality_score"],
            "risk_score": r["risk_score"],
        }
        for v in r["violations"]:
            v["conversation_id"] = cid
            all_violations.append(v)

    total_convs = len(ratings)
    total_violations = len(all_violations)
    convs_with_violations = sum(1 for v in conv_violations.values() if v)
    convs_clean = total_convs - convs_with_violations

    # ── 1. Most common violation types ─────────────────────────────────
    category_counts = Counter()
    category_severities = defaultdict(list)
    rule_counts = Counter()

    for v in all_violations:
        cat = extract_rule_category(v["rule"])
        category_counts[cat] += 1
        category_severities[cat].append(v["severity"])
        rule_counts[v["rule"]] += 1

    # ── 2. Correlate with outcomes (scoped to evaluated IDs) ───────────
    complained_cids = {cid for cid, o in outcomes.items() if o.get("borrower_complained")}
    flagged_cids = {cid for cid, o in outcomes.items() if o.get("regulatory_flag")}
    paid_cids = {cid for cid, o in outcomes.items() if o.get("payment_received")}
    human_cids = {cid for cid, o in outcomes.items() if o.get("required_human_intervention")}

    def violation_stats(cid_set):
        """Get violation stats for a set of conversation IDs."""
        matching = [r for r in ratings if r["conversation_id"] in cid_set]
        if not matching:
            return {"count": 0, "avg_violations": 0, "avg_quality": 0, "avg_risk": 0}
        return {
            "count": len(matching),
            "avg_violations": sum(len(r["violations"]) for r in matching) / len(matching),
            "avg_quality": sum(r["quality_score"] for r in matching) / len(matching),
            "avg_risk": sum(r["risk_score"] for r in matching) / len(matching),
        }

    complained_stats = violation_stats(complained_cids)
    not_complained_stats = violation_stats(evaluated_ids - complained_cids)
    flagged_stats = violation_stats(flagged_cids)
    not_flagged_stats = violation_stats(evaluated_ids - flagged_cids)
    paid_stats = violation_stats(paid_cids)
    not_paid_stats = violation_stats(evaluated_ids - paid_cids)

    # Category breakdown for complained conversations
    complained_violation_cats = Counter()
    for cid in complained_cids:
        for v in conv_violations.get(cid, []):
            complained_violation_cats[extract_rule_category(v["rule"])] += 1

    # Category breakdown for flagged conversations
    flagged_violation_cats = Counter()
    for cid in flagged_cids:
        for v in conv_violations.get(cid, []):
            flagged_violation_cats[extract_rule_category(v["rule"])] += 1

    # ── 3. Segment analysis ────────────────────────────────────────────
    segment_stats = {
        "language": defaultdict(lambda: {"count": 0, "violations": 0, "quality_sum": 0, "risk_sum": 0}),
        "zone": defaultdict(lambda: {"count": 0, "violations": 0, "quality_sum": 0, "risk_sum": 0}),
        "dpd_bucket": defaultdict(lambda: {"count": 0, "violations": 0, "quality_sum": 0, "risk_sum": 0}),
    }

    for r in ratings:
        cid = r["conversation_id"]
        meta = metadata.get(cid, {})
        lang = meta.get("language", "unknown")
        zone = meta.get("zone", "unknown")
        dpd = meta.get("dpd", 0)
        bucket = dpd_bucket(dpd)

        n_v = len(r["violations"])
        for dim, key in [("language", lang), ("zone", zone), ("dpd_bucket", bucket)]:
            segment_stats[dim][key]["count"] += 1
            segment_stats[dim][key]["violations"] += n_v
            segment_stats[dim][key]["quality_sum"] += r["quality_score"]
            segment_stats[dim][key]["risk_sum"] += r["risk_score"]

    # ── 4. Find examples — diverse across conversations ────────────────
    worst_quality = sorted(ratings, key=lambda r: r["quality_score"])[:10]

    # Pick diverse examples per category — max 1 per conversation per category
    category_examples = defaultdict(list)
    category_seen_cids = defaultdict(set)
    for v in all_violations:
        cat = extract_rule_category(v["rule"])
        cid = v["conversation_id"]
        if len(category_examples[cat]) < 3 and cid not in category_seen_cids[cat]:
            category_examples[cat].append(v)
            category_seen_cids[cat].add(cid)

    # Pick diverse examples per specific rule — max 1 per conversation
    rule_examples = defaultdict(list)
    rule_seen_cids = defaultdict(set)
    for v in all_violations:
        rule = v["rule"]
        cid = v["conversation_id"]
        if len(rule_examples[rule]) < 2 and cid not in rule_seen_cids[rule]:
            rule_examples[rule].append(v)
            rule_seen_cids[rule].add(cid)

    # ── Generate Report ────────────────────────────────────────────────
    print("Generating violations.md...")
    lines = []

    lines.append(f"# Violation Report — {total_convs} Production Conversations\n")
    lines.append(f"Evaluated **{total_convs}** conversations (random sample from 700 total) against the agent specification.\n")
    lines.append(f"- Total violations found: **{total_violations}**")
    lines.append(f"- Avg violations per conversation: **{total_violations/total_convs:.1f}**")
    lines.append(f"- Conversations with violations: **{convs_with_violations}** ({convs_with_violations/total_convs*100:.0f}%)")
    lines.append(f"- Clean conversations: **{convs_clean}** ({convs_clean/total_convs*100:.0f}%)")
    lines.append(f"- Average quality score: **{sum(r['quality_score'] for r in ratings)/total_convs:.3f}** (0 = worst, 1 = best)")
    lines.append(f"- Average risk score: **{sum(r['risk_score'] for r in ratings)/total_convs:.3f}** (0 = safe, 1 = high risk)\n")

    # ── Section 1: Most Common Violations ──────────────────────────────
    lines.append("---\n")
    lines.append("## 1. Most Common Violation Types\n")
    lines.append("| Rank | Category | Count | % of All | Avg Severity | Severity Level |")
    lines.append("|------|----------|------:|---------:|-------------:|:--------------:|")

    for rank, (cat, count) in enumerate(category_counts.most_common(15), 1):
        pct = count / total_violations * 100 if total_violations > 0 else 0
        avg_sev = sum(category_severities[cat]) / len(category_severities[cat])
        lines.append(f"| {rank} | {cat} | {count} | {pct:.1f}% | {avg_sev:.2f} | {severity_label(avg_sev)} |")

    lines.append("")

    # Top specific rules with DIVERSE examples (full conversation IDs)
    lines.append("### Top 10 Specific Rules Violated\n")
    lines.append("| Rule | Count | Example Conversation | Turn |")
    lines.append("|------|------:|:---------------------|-----:|")
    for rule, count in rule_counts.most_common(10):
        examples = rule_examples.get(rule, [])
        if examples:
            ex = examples[0]
            lines.append(f"| {rule} | {count} | `{ex['conversation_id']}` | {ex['turn']} |")
        else:
            lines.append(f"| {rule} | {count} | — | — |")
    lines.append("")

    # ── Section 2: Correlation with Outcomes ───────────────────────────
    lines.append("---\n")
    lines.append("## 2. Violations Correlated with Bad Outcomes\n")

    lines.append("### Complaints vs No Complaints\n")
    lines.append("| Metric | Complained | Did Not Complain |")
    lines.append("|--------|----------:|------------------:|")
    lines.append(f"| Conversations | {complained_stats['count']} | {not_complained_stats['count']} |")
    lines.append(f"| Avg violations | {complained_stats['avg_violations']:.1f} | {not_complained_stats['avg_violations']:.1f} |")
    lines.append(f"| Avg quality score | {complained_stats['avg_quality']:.3f} | {not_complained_stats['avg_quality']:.3f} |")
    lines.append(f"| Avg risk score | {complained_stats['avg_risk']:.3f} | {not_complained_stats['avg_risk']:.3f} |")
    lines.append("")

    if complained_violation_cats:
        lines.append("#### Violation Types in Complained Conversations\n")
        lines.append("| Category | Count in Complained | % of Complained Violations |")
        lines.append("|----------|--------------------:|---------------------------:|")
        total_complained_v = sum(complained_violation_cats.values())
        for cat, count in complained_violation_cats.most_common(10):
            pct = count / total_complained_v * 100 if total_complained_v > 0 else 0
            lines.append(f"| {cat} | {count} | {pct:.1f}% |")
        lines.append("")

    lines.append("### Regulatory Flags\n")
    lines.append("| Metric | Flagged | Not Flagged |")
    lines.append("|--------|--------:|------------:|")
    lines.append(f"| Conversations | {flagged_stats['count']} | {not_flagged_stats['count']} |")
    lines.append(f"| Avg violations | {flagged_stats['avg_violations']:.1f} | {not_flagged_stats['avg_violations']:.1f} |")
    lines.append(f"| Avg quality score | {flagged_stats['avg_quality']:.3f} | {not_flagged_stats['avg_quality']:.3f} |")
    lines.append(f"| Avg risk score | {flagged_stats['avg_risk']:.3f} | {not_flagged_stats['avg_risk']:.3f} |")
    lines.append("")

    if flagged_violation_cats:
        lines.append("#### Violation Types in Flagged Conversations\n")
        lines.append("| Category | Count in Flagged | % of Flagged Violations |")
        lines.append("|----------|------------------:|------------------------:|")
        total_flagged_v = sum(flagged_violation_cats.values())
        for cat, count in flagged_violation_cats.most_common(10):
            pct = count / total_flagged_v * 100 if total_flagged_v > 0 else 0
            lines.append(f"| {cat} | {count} | {pct:.1f}% |")
        lines.append("")

    lines.append("### Payment vs Non-Payment\n")
    lines.append("| Metric | Payment Received | No Payment |")
    lines.append("|--------|------------------:|-----------:|")
    lines.append(f"| Conversations | {paid_stats['count']} | {not_paid_stats['count']} |")
    lines.append(f"| Avg violations | {paid_stats['avg_violations']:.1f} | {not_paid_stats['avg_violations']:.1f} |")
    lines.append(f"| Avg quality score | {paid_stats['avg_quality']:.3f} | {not_paid_stats['avg_quality']:.3f} |")
    lines.append(f"| Avg risk score | {paid_stats['avg_risk']:.3f} | {not_paid_stats['avg_risk']:.3f} |")
    lines.append("")

    # ── Section 3: Segment Analysis ────────────────────────────────────
    lines.append("---\n")
    lines.append("## 3. Violation Rates by Borrower Segment\n")

    for dim_name, dim_label in [("language", "Language"), ("zone", "Zone"), ("dpd_bucket", "DPD Bucket")]:
        lines.append(f"### By {dim_label}\n")
        lines.append(f"| {dim_label} | Conversations | Avg Violations | Avg Quality | Avg Risk |")
        lines.append(f"|------------|---------------:|----------------:|-------------:|----------:|")

        dim_data = segment_stats[dim_name]
        sorted_keys = sorted(dim_data.keys())
        for key in sorted_keys:
            s = dim_data[key]
            n = s["count"]
            avg_v = s["violations"] / n if n > 0 else 0
            avg_q = s["quality_sum"] / n if n > 0 else 0
            avg_r = s["risk_sum"] / n if n > 0 else 0
            lines.append(f"| {key} | {n} | {avg_v:.1f} | {avg_q:.3f} | {avg_r:.3f} |")
        lines.append("")

    # ── Section 4: Specific Examples ───────────────────────────────────
    lines.append("---\n")
    lines.append("## 4. Specific Conversation Examples\n")

    lines.append("### Worst Quality Conversations\n")
    lines.append("| Rank | Conversation ID | Quality | Risk | Violations | Key Issue |")
    lines.append("|------|-----------------|--------:|-----:|-----------:|-----------|")
    for rank, r in enumerate(worst_quality[:10], 1):
        cid = r["conversation_id"]
        key_issue = r["violations"][0]["rule"] if r["violations"] else "—"
        lines.append(
            f"| {rank} | `{cid}` | {r['quality_score']:.3f} | "
            f"{r['risk_score']:.3f} | {len(r['violations'])} | {key_issue} |"
        )
    lines.append("")

    # Detailed examples for top violation categories — diverse conversations
    lines.append("### Detailed Examples by Category\n")
    for cat_tuple in list(category_counts.most_common(8)):
        cat_name = cat_tuple[0]
        examples = category_examples.get(cat_name, [])
        if not examples:
            continue

        lines.append(f"#### {cat_name}\n")
        for ex in examples[:2]:
            cid = ex["conversation_id"]
            explanation = ex["explanation"]
            if len(explanation) > 400:
                explanation = explanation[:397] + "..."
            sev = severity_label(ex["severity"])
            lines.append(f"- **`{cid}`** — Turn {ex['turn']}, Severity {ex['severity']:.2f} ({sev})")
            lines.append(f"  - **Rule**: {ex['rule']}")
            lines.append(f"  - **Evidence**: {explanation}")
            lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────
    lines.append("---\n")
    lines.append("## Methodology\n")
    lines.append("This report was generated by the Hybrid Evaluator pipeline:\n")
    lines.append("1. **Layer 1 (Deterministic)**: State transition validation (Section 4), timing checks (Section 6), amount validation (Section 9), loop detection")
    lines.append("2. **Layer 2 (Gemini LLM)**: Compliance evaluation (Section 8, 1–5 rubric), quality assessment (Section 10, 1–3 rubric), classification accuracy (Invariant I5, 1–3 rubric)")
    lines.append("3. **Aggregation**: Quality deduction model + worst-case risk scoring")
    lines.append(f"\nAll rules documented in [`rulesets.md`](file:///Users/harry/assignments/riverline/rulesets.md).\n")

    # Write
    report = "\n".join(lines)
    with open(OUTPUT_FILE, "w") as f:
        f.write(report)

    print(f"\nWrote {OUTPUT_FILE} ({len(lines)} lines)")
    print("Done!")


if __name__ == "__main__":
    main()
