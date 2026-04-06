#!/usr/bin/env python3
"""
Analyze human evaluation survey results.

Reads from exported JSON (localStorage dump or Google Sheets export)
and computes:
  - Win rate: Phys-GRPO vs Base (physics + visual quality)
  - Per-phenomenon breakdown
  - Inter-annotator agreement (Fleiss' kappa)
  - Statistical significance (binomial test)

Usage:
    python analyze_results.py results.json
    python analyze_results.py results/     # reads all .json files in dir
"""

import json
import sys
import os
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path


def load_results(path):
    """Load survey results from a JSON file or directory of JSON files."""
    results = []
    p = Path(path)
    if p.is_dir():
        for f in sorted(p.glob("*.json")):
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
    else:
        with open(p) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
    return results


def compute_win_rates(results):
    """Compute overall and per-phenomenon win rates."""
    overall = {"physics": Counter(), "visual": Counter()}
    per_phenomenon = defaultdict(lambda: {"physics": Counter(), "visual": Counter()})

    for participant in results:
        for resp in participant["responses"]:
            phenom = resp["phenomenon"]
            for dim in ["physics", "visual"]:
                choice = resp[f"{dim}_mapped"]
                overall[dim][choice] += 1
                per_phenomenon[phenom][dim][choice] += 1

    return overall, dict(per_phenomenon)


def binomial_test(wins, total, p0=0.5):
    """Two-sided binomial test: is win rate significantly different from p0?"""
    from math import comb
    # Exact binomial test
    observed_p = wins / total if total > 0 else 0
    # Compute p-value (two-sided)
    if total == 0:
        return 1.0
    p_value = 0
    for k in range(total + 1):
        pk = comb(total, k) * (p0 ** k) * ((1 - p0) ** (total - k))
        if comb(total, k) * (p0 ** k) * ((1 - p0) ** (total - k)) <= \
           comb(total, wins) * (p0 ** wins) * ((1 - p0) ** (total - wins)) + 1e-15:
            p_value += pk
    return min(p_value, 1.0)


def fleiss_kappa(ratings_matrix):
    """
    Compute Fleiss' kappa for inter-annotator agreement.
    ratings_matrix: N_items x N_categories, where each cell is the count
                    of raters who assigned that category to that item.
    """
    N, k = ratings_matrix.shape
    n = ratings_matrix.sum(axis=1)
    if len(set(n)) != 1:
        # Unequal raters per item — use average
        pass
    n_val = n[0] if len(set(n)) == 1 else n.mean()

    # Proportion per category
    p_j = ratings_matrix.sum(axis=0) / (N * n_val)

    # Per-item agreement
    P_i = (np.sum(ratings_matrix ** 2, axis=1) - n_val) / (n_val * (n_val - 1) + 1e-10)
    P_bar = np.mean(P_i)

    # Expected agreement
    P_e = np.sum(p_j ** 2)

    kappa = (P_bar - P_e) / (1 - P_e + 1e-10)
    return kappa


def print_results(results):
    n_participants = len(results)
    print(f"{'=' * 60}")
    print(f"  Human Evaluation Results — {n_participants} participants")
    print(f"{'=' * 60}\n")

    # Duration stats
    durations = [r.get("duration_seconds", 0) for r in results]
    if any(durations):
        print(f"Median completion time: {np.median(durations):.0f}s "
              f"(range: {min(durations)}–{max(durations)}s)\n")

    overall, per_phenom = compute_win_rates(results)

    for dim, label in [("physics", "Physical Plausibility"), ("visual", "Visual Quality")]:
        counts = overall[dim]
        total = sum(counts.values())
        grpo_wins = counts.get("grpo", 0)
        base_wins = counts.get("base", 0)
        ties = counts.get("tie", 0)

        # Exclude ties for win rate
        contested = grpo_wins + base_wins
        win_rate = grpo_wins / contested if contested > 0 else 0
        p_val = binomial_test(grpo_wins, contested) if contested > 0 else 1.0

        print(f"  {label}:")
        print(f"    Phys-GRPO wins: {grpo_wins:3d} ({grpo_wins/total*100:5.1f}%)")
        print(f"    Base wins:      {base_wins:3d} ({base_wins/total*100:5.1f}%)")
        print(f"    Ties:           {ties:3d} ({ties/total*100:5.1f}%)")
        print(f"    Win rate (excl. ties): {win_rate:.1%}  "
              f"(p={p_val:.4f}{'***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''})")
        print()

    # Per-phenomenon breakdown
    print(f"\n{'─' * 60}")
    print(f"  Per-Phenomenon Breakdown (Physics)")
    print(f"{'─' * 60}")
    print(f"  {'Phenomenon':<12s}  {'GRPO':>5s}  {'Base':>5s}  {'Tie':>5s}  {'Win%':>6s}")
    print(f"  {'─'*42}")
    for phenom in sorted(per_phenom.keys()):
        c = per_phenom[phenom]["physics"]
        g, b, t = c.get("grpo", 0), c.get("base", 0), c.get("tie", 0)
        contested = g + b
        wr = g / contested if contested > 0 else 0
        print(f"  {phenom:<12s}  {g:5d}  {b:5d}  {t:5d}  {wr:5.0%}")

    # Fleiss' kappa (if enough participants)
    if n_participants >= 3:
        print(f"\n{'─' * 60}")
        print(f"  Inter-Annotator Agreement (Fleiss' kappa)")
        print(f"{'─' * 60}")

        n_items = 14  # trials
        categories = ["grpo", "base", "tie"]

        for dim in ["physics", "visual"]:
            matrix = np.zeros((n_items, len(categories)))
            trial_ids = [f"pair_{i+1:02d}" for i in range(n_items)]

            for participant in results:
                for resp in participant["responses"]:
                    idx = trial_ids.index(resp["trial_id"]) if resp["trial_id"] in trial_ids else -1
                    if idx >= 0:
                        choice = resp[f"{dim}_mapped"]
                        if choice in categories:
                            matrix[idx, categories.index(choice)] += 1

            kappa = fleiss_kappa(matrix)
            interpretation = (
                "poor" if kappa < 0.0 else
                "slight" if kappa < 0.20 else
                "fair" if kappa < 0.40 else
                "moderate" if kappa < 0.60 else
                "substantial" if kappa < 0.80 else
                "almost perfect"
            )
            print(f"  {dim:>10s}: kappa = {kappa:.3f} ({interpretation})")

    # LaTeX table
    print(f"\n{'─' * 60}")
    print(f"  LaTeX Table (copy into main.tex)")
    print(f"{'─' * 60}\n")

    for dim, label in [("physics", "Physical Plausibility"), ("visual", "Visual Quality")]:
        counts = overall[dim]
        total = sum(counts.values())
        g = counts.get("grpo", 0)
        b = counts.get("base", 0)
        t = counts.get("tie", 0)
        contested = g + b
        wr = g / contested if contested > 0 else 0
        p_val = binomial_test(g, contested) if contested > 0 else 1.0
        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
        print(f"  {label} & {g} ({g/total*100:.0f}\\%) & {b} ({b/total*100:.0f}\\%) "
              f"& {t} ({t/total*100:.0f}\\%) & {wr:.0%}{sig} \\\\")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <results.json or dir/>")
        print("\nTo export from browser localStorage:")
        print('  Open browser console → JSON.stringify(JSON.parse(localStorage.survey_results))')
        print("  Save output to results.json")
        sys.exit(1)

    results = load_results(sys.argv[1])
    if not results:
        print("No results found.")
        sys.exit(1)

    print_results(results)
