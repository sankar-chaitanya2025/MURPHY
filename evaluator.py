"""
evaluator.py — Loads HumanEval, runs MURPHY, reports results
Owner: Chaitanya (Team Lead)

This file:
  1. Downloads the HumanEval dataset (164 Python problems)
  2. Runs each problem through MURPHY (multi-turn) or baseline (single-turn)
  3. Computes pass@1 = (solved / total) * 100
  4. Repeats N times and calculates mean ± standard deviation
  5. Saves results to CSV
"""

import os
import csv
import time
import statistics
import config
from murphy_engine import run_murphy, run_single_turn


# ─────────────────────────────────────────────
# DATASET LOADING
# ─────────────────────────────────────────────

def load_humaneval(limit: int = None) -> list:
    """
    Load HumanEval dataset.

    Returns list of dicts, each with:
        - task_id: e.g. "HumanEval/0"
        - prompt: the function signature + docstring
        - test: the test cases
        - entry_point: the function name
        - canonical_solution: the correct answer (we don't use this)
    """
    try:
        from datasets import load_dataset
        ds = load_dataset("openai/openai_humaneval", split="test")
    except ImportError:
        print("ERROR: 'datasets' library not installed.")
        print("Run: pip install datasets")
        return []
    except Exception as e:
        print(f"ERROR loading HumanEval: {e}")
        print("Make sure you have internet connection for first download.")
        return []

    problems = []
    for item in ds:
        problems.append({
            "task_id": item["task_id"],
            "prompt": item["prompt"],
            "test": item["test"],
            "entry_point": item["entry_point"],
        })

    if limit:
        problems = problems[:limit]

    print(f"Loaded {len(problems)} HumanEval problems.")
    return problems


def extract_test_code(problem: dict) -> str:
    """
    Extract runnable test code from a HumanEval problem.
    HumanEval tests are in a check() function that needs to be called.
    """
    test = problem["test"]
    entry_point = problem["entry_point"]

    # HumanEval wraps tests in a check() function
    # We need to add the function call at the end
    if "def check(" in test:
        test_code = test + f"\ncheck({entry_point})\n"
    else:
        test_code = test

    return test_code


# ─────────────────────────────────────────────
# EVALUATION RUNNERS
# ─────────────────────────────────────────────

def evaluate_murphy(problems: list, strategy: str = "mars",
                     num_generations: int = None,
                     num_turns: int = None,
                     verbose: bool = False) -> dict:
    """
    Run MURPHY on all problems and compute pass@1.

    Args:
        problems: List of HumanEval problem dicts
        strategy: "mars" or "mers"
        num_generations: G (defaults to config)
        num_turns: S (defaults to config)
        verbose: Print per-problem details

    Returns:
        Dict with pass_at_1, solved_count, total, per_problem results
    """
    G = num_generations or config.NUM_GENERATIONS
    S = num_turns or config.NUM_TURNS

    solved = 0
    total = len(problems)
    per_problem = []
    total_time = 0

    print(f"\nRunning MURPHY evaluation (G={G}, S={S}, strategy={strategy})")
    print(f"Problems: {total}")
    print("-" * 50)

    for i, problem in enumerate(problems):
        test_code = extract_test_code(problem)

        try:
            result = run_murphy(
                problem=problem,
                test_code=test_code,
                strategy=strategy,
                num_generations=G,
                num_turns=S,
                verbose=verbose
            )
            if result["solved"]:
                solved += 1

            per_problem.append({
                "task_id": problem["task_id"],
                "solved": result["solved"],
                "best_reward": result["best_reward"],
                "generations": result["total_generations"],
                "time": result["time_seconds"]
            })
            total_time += result["time_seconds"]

            status = "✅" if result["solved"] else "❌"
            print(f"  [{i+1}/{total}] {problem['task_id']}: {status} "
                  f"(reward={result['best_reward']:.2f}, "
                  f"gens={result['total_generations']}, "
                  f"time={result['time_seconds']:.1f}s)")

        except Exception as e:
            print(f"  [{i+1}/{total}] {problem['task_id']}: ⚠️ ERROR: {e}")
            per_problem.append({
                "task_id": problem["task_id"],
                "solved": False,
                "best_reward": 0.0,
                "generations": 0,
                "time": 0.0
            })

    pass_at_1 = (solved / total) * 100 if total > 0 else 0.0

    print("-" * 50)
    print(f"Result: {solved}/{total} solved = {pass_at_1:.2f}% pass@1")
    print(f"Total time: {total_time:.1f}s")

    return {
        "pass_at_1": pass_at_1,
        "solved": solved,
        "total": total,
        "per_problem": per_problem,
        "total_time": total_time
    }


def evaluate_baseline(problems: list, num_generations: int = None,
                       verbose: bool = False) -> dict:
    """
    Run single-turn baseline (no feedback) on all problems.
    This is what we compare MURPHY against.
    """
    G = num_generations or config.NUM_GENERATIONS

    solved = 0
    total = len(problems)
    per_problem = []
    total_time = 0

    print(f"\nRunning BASELINE evaluation (G={G}, single-turn)")
    print(f"Problems: {total}")
    print("-" * 50)

    for i, problem in enumerate(problems):
        test_code = extract_test_code(problem)

        try:
            result = run_single_turn(
                problem=problem,
                test_code=test_code,
                num_generations=G,
                verbose=verbose
            )
            if result["solved"]:
                solved += 1

            per_problem.append({
                "task_id": problem["task_id"],
                "solved": result["solved"],
                "best_reward": result["best_reward"],
                "generations": result["total_generations"],
                "time": result["time_seconds"]
            })
            total_time += result["time_seconds"]

            status = "✅" if result["solved"] else "❌"
            print(f"  [{i+1}/{total}] {problem['task_id']}: {status} "
                  f"(reward={result['best_reward']:.2f}, "
                  f"time={result['time_seconds']:.1f}s)")

        except Exception as e:
            print(f"  [{i+1}/{total}] {problem['task_id']}: ⚠️ ERROR: {e}")
            per_problem.append({
                "task_id": problem["task_id"],
                "solved": False,
                "best_reward": 0.0,
                "generations": 0,
                "time": 0.0
            })

    pass_at_1 = (solved / total) * 100 if total > 0 else 0.0

    print("-" * 50)
    print(f"Result: {solved}/{total} solved = {pass_at_1:.2f}% pass@1")

    return {
        "pass_at_1": pass_at_1,
        "solved": solved,
        "total": total,
        "per_problem": per_problem,
        "total_time": total_time
    }


# ─────────────────────────────────────────────
# MULTI-RUN EXPERIMENT (for mean ± std)
# ─────────────────────────────────────────────

def run_experiment(problems: list, num_runs: int = None) -> dict:
    """
    Run the full experiment: baseline + MURPHY (MARS) + MURPHY (MERS)
    repeated num_runs times. Computes mean ± std for each.

    This produces the numbers for your results table.
    """
    runs = num_runs or config.NUM_RUNS

    baseline_scores = []
    mars_scores = []
    mers_scores = []

    for run_id in range(1, runs + 1):
        print(f"\n{'='*60}")
        print(f"EXPERIMENT RUN {run_id}/{runs}")
        print(f"{'='*60}")

        # Baseline (single-turn)
        bl = evaluate_baseline(problems)
        baseline_scores.append(bl["pass_at_1"])

        # MURPHY with MARS
        mars = evaluate_murphy(problems, strategy="mars")
        mars_scores.append(mars["pass_at_1"])

        # MURPHY with MERS
        mers = evaluate_murphy(problems, strategy="mers")
        mers_scores.append(mers["pass_at_1"])

    # Calculate statistics
    results = {
        "baseline": {
            "mean": statistics.mean(baseline_scores),
            "std": statistics.stdev(baseline_scores) if len(baseline_scores) > 1 else 0.0,
            "scores": baseline_scores
        },
        "murphy_mars": {
            "mean": statistics.mean(mars_scores),
            "std": statistics.stdev(mars_scores) if len(mars_scores) > 1 else 0.0,
            "scores": mars_scores
        },
        "murphy_mers": {
            "mean": statistics.mean(mers_scores),
            "std": statistics.stdev(mers_scores) if len(mers_scores) > 1 else 0.0,
            "scores": mers_scores
        }
    }

    # Print final results
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS ({runs} runs, {len(problems)} problems)")
    print(f"{'='*60}")
    print(f"{'Method':<25} {'pass@1 (mean ± std)':<25}")
    print(f"{'-'*50}")
    print(f"{'Baseline (single-turn)':<25} "
          f"{results['baseline']['mean']:.2f} ± {results['baseline']['std']:.2f}%")
    print(f"{'MURPHY (MARS)':<25} "
          f"{results['murphy_mars']['mean']:.2f} ± {results['murphy_mars']['std']:.2f}%")
    print(f"{'MURPHY (MERS)':<25} "
          f"{results['murphy_mers']['mean']:.2f} ± {results['murphy_mers']['std']:.2f}%")

    improvement = results["murphy_mars"]["mean"] - results["baseline"]["mean"]
    print(f"\nMARS improvement over baseline: +{improvement:.2f}%")

    return results


# ─────────────────────────────────────────────
# SAVE RESULTS TO CSV
# ─────────────────────────────────────────────

def save_results(results: dict, filename: str = None):
    """Save experiment results to CSV file."""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(config.RESULTS_DIR, f"results_{timestamp}.csv")

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Method", "Mean_Pass@1", "Std_Pass@1", "Run_Scores"])
        for method, data in results.items():
            writer.writerow([
                method,
                f"{data['mean']:.2f}",
                f"{data['std']:.2f}",
                str(data['scores'])
            ])

    print(f"\nResults saved to: {filename}")
    return filename


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Testing evaluator.py")
    print("=" * 60)

    # Test 1: Load dataset
    print("\nTest 1: Loading HumanEval...")
    problems = load_humaneval(limit=3)
    if problems:
        print(f"  First problem: {problems[0]['task_id']}")
        print(f"  Entry point: {problems[0]['entry_point']}")
        print(f"  Prompt preview: {problems[0]['prompt'][:100]}...")
        print("  ✅ Dataset loaded!")
    else:
        print("  ❌ Could not load dataset")
        print("  Run: pip install datasets")

    # Test 2: Extract test code
    if problems:
        print("\nTest 2: Extracting test code...")
        test_code = extract_test_code(problems[0])
        print(f"  Test code preview: {test_code[:150]}...")
        print("  ✅ Test extraction works!")

    print("\nTo run full evaluation:")
    print("  python main.py --mode murphy --problems 10")
