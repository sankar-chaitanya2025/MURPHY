"""
Ray-enabled evaluator for parallel MURPHY experiments.
This parallelizes problem evaluation across multiple CPU cores.

Author: Modified from original evaluator.py for Ray deployment
"""

import ray
import time
from typing import List, Dict, Tuple
from datasets import load_dataset

# Import from your existing modules
from config import (
    NUM_GENERATIONS, NUM_TURNS, NUM_PROBLEMS, NUM_RUNS, MODEL_NAME
)
from murphy_engine import murphy_solve
from model_client import generate_code
from code_executor import execute_code
import ray_config


# ============================================================
# RAY REMOTE FUNCTIONS (Parallelized Tasks)
# ============================================================

@ray.remote(**ray_config.get_task_options())
def evaluate_single_problem_murphy(problem: Dict, strategy: str = "mars") -> Tuple[str, bool, float, int]:
    """
    Evaluate a single problem using MURPHY (multi-turn with feedback).
    This runs as a distributed Ray task.
    
    Args:
        problem: HumanEval problem dict with 'task_id', 'prompt', 'test', 'entry_point'
        strategy: Credit assignment strategy ('mars' or 'mers')
    
    Returns:
        (task_id, solved, best_reward, total_generations)
    """
    try:
        result = murphy_solve(
            problem=problem['prompt'],
            test_code=problem['test'],
            entry_point=problem['entry_point'],
            strategy=strategy
        )
        
        return (
            problem['task_id'],
            result['solved'],
            result['best_reward'],
            result['total_generations']
        )
    except Exception as e:
        print(f"❌ Error on {problem['task_id']}: {e}")
        return (problem['task_id'], False, 0.0, 0)


@ray.remote(**ray_config.get_task_options())
def evaluate_single_problem_baseline(problem: Dict) -> Tuple[str, bool, float]:
    """
    Evaluate a single problem using baseline (single-turn, no feedback).
    This runs as a distributed Ray task.
    
    Args:
        problem: HumanEval problem dict
    
    Returns:
        (task_id, solved, best_reward)
    """
    try:
        best_reward = 0.0
        solved = False
        
        # Generate G candidates (single turn only)
        for _ in range(NUM_GENERATIONS):
            prompt = f"{problem['prompt']}\n\nGenerate a complete Python function."
            code = generate_code(prompt)
            
            # Execute and check
            result = execute_code(code, problem['test'])
            if result['reward'] > best_reward:
                best_reward = result['reward']
                solved = result['passed']
            
            if solved:
                break  # Stop early if we found a solution
        
        return (problem['task_id'], solved, best_reward)
    
    except Exception as e:
        print(f"❌ Error on {problem['task_id']}: {e}")
        return (problem['task_id'], False, 0.0)


# ============================================================
# PARALLEL EVALUATION FUNCTIONS
# ============================================================

def evaluate_murphy_parallel(problems: List[Dict], strategy: str = "mars") -> Dict:
    """
    Evaluate multiple problems in parallel using MURPHY.
    
    Args:
        problems: List of HumanEval problem dicts
        strategy: Credit assignment strategy ('mars' or 'mers')
    
    Returns:
        Dict with 'pass_rate', 'solved_count', 'total_problems', 'results'
    """
    print(f"\n{'='*60}")
    print(f"🚀 RAY MURPHY Evaluation: {len(problems)} problems (strategy={strategy})")
    print(f"   Parallelism: {ray_config.MAX_PARALLEL_TASKS or 'AUTO'} tasks")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # Submit all problems as Ray tasks
    futures = [
        evaluate_single_problem_murphy.remote(problem, strategy)
        for problem in problems
    ]
    
    # Collect results as they complete
    results = []
    solved_count = 0
    
    print("📊 Progress:")
    for i, future in enumerate(futures):
        task_id, solved, reward, gens = ray.get(future)
        results.append({
            'task_id': task_id,
            'solved': solved,
            'reward': reward,
            'generations': gens
        })
        
        if solved:
            solved_count += 1
        
        # Progress indicator
        if (i + 1) % 10 == 0 or (i + 1) == len(problems):
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"   {i+1}/{len(problems)} done | {solved_count} solved | "
                  f"{rate:.2f} problems/sec | {elapsed:.1f}s elapsed")
    
    elapsed_time = time.time() - start_time
    pass_rate = (solved_count / len(problems)) * 100
    
    print(f"\n{'='*60}")
    print(f"✅ MURPHY Results ({strategy.upper()}):")
    print(f"   Pass@1: {pass_rate:.2f}% ({solved_count}/{len(problems)})")
    print(f"   Time: {elapsed_time:.1f}s ({elapsed_time/60:.1f} min)")
    print(f"   Speed: {len(problems)/elapsed_time:.2f} problems/sec")
    print(f"{'='*60}\n")
    
    return {
        'pass_rate': pass_rate,
        'solved_count': solved_count,
        'total_problems': len(problems),
        'time_seconds': elapsed_time,
        'results': results,
        'strategy': strategy
    }


def evaluate_baseline_parallel(problems: List[Dict]) -> Dict:
    """
    Evaluate multiple problems in parallel using baseline (single-turn).
    
    Args:
        problems: List of HumanEval problem dicts
    
    Returns:
        Dict with 'pass_rate', 'solved_count', 'total_problems', 'results'
    """
    print(f"\n{'='*60}")
    print(f"🚀 RAY BASELINE Evaluation: {len(problems)} problems")
    print(f"   Parallelism: {ray_config.MAX_PARALLEL_TASKS or 'AUTO'} tasks")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # Submit all problems as Ray tasks
    futures = [
        evaluate_single_problem_baseline.remote(problem)
        for problem in problems
    ]
    
    # Collect results as they complete
    results = []
    solved_count = 0
    
    print("📊 Progress:")
    for i, future in enumerate(futures):
        task_id, solved, reward = ray.get(future)
        results.append({
            'task_id': task_id,
            'solved': solved,
            'reward': reward
        })
        
        if solved:
            solved_count += 1
        
        # Progress indicator
        if (i + 1) % 10 == 0 or (i + 1) == len(problems):
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"   {i+1}/{len(problems)} done | {solved_count} solved | "
                  f"{rate:.2f} problems/sec | {elapsed:.1f}s elapsed")
    
    elapsed_time = time.time() - start_time
    pass_rate = (solved_count / len(problems)) * 100
    
    print(f"\n{'='*60}")
    print(f"✅ BASELINE Results:")
    print(f"   Pass@1: {pass_rate:.2f}% ({solved_count}/{len(problems)})")
    print(f"   Time: {elapsed_time:.1f}s ({elapsed_time/60:.1f} min)")
    print(f"   Speed: {len(problems)/elapsed_time:.2f} problems/sec")
    print(f"{'='*60}\n")
    
    return {
        'pass_rate': pass_rate,
        'solved_count': solved_count,
        'total_problems': len(problems),
        'time_seconds': elapsed_time,
        'results': results,
        'strategy': 'baseline'
    }


# ============================================================
# EXPERIMENT RUNNER (Multiple Runs)
# ============================================================

def run_experiment_parallel(problems: List[Dict], num_runs: int = 3) -> Dict:
    """
    Run complete experiment with multiple runs of baseline, MARS, and MERS.
    
    Args:
        problems: List of HumanEval problems
        num_runs: Number of times to repeat each configuration
    
    Returns:
        Dict with aggregated results
    """
    print(f"\n{'#'*60}")
    print(f"# RAY EXPERIMENT: {len(problems)} problems × {num_runs} runs")
    print(f"# Model: {MODEL_NAME}")
    print(f"# G={NUM_GENERATIONS}, S={NUM_TURNS}")
    print(f"{'#'*60}\n")
    
    all_results = {
        'baseline': [],
        'murphy_mars': [],
        'murphy_mers': []
    }
    
    # Run baseline multiple times
    print(f"\n{'*'*60}")
    print(f"* BASELINE (Single-Turn, No Feedback)")
    print(f"{'*'*60}")
    for run in range(num_runs):
        print(f"\n--- Run {run+1}/{num_runs} ---")
        result = evaluate_baseline_parallel(problems)
        all_results['baseline'].append(result['pass_rate'])
    
    # Run MURPHY with MARS multiple times
    print(f"\n{'*'*60}")
    print(f"* MURPHY + MARS (Multi-Turn, Max Reward)")
    print(f"{'*'*60}")
    for run in range(num_runs):
        print(f"\n--- Run {run+1}/{num_runs} ---")
        result = evaluate_murphy_parallel(problems, strategy='mars')
        all_results['murphy_mars'].append(result['pass_rate'])
    
    # Run MURPHY with MERS multiple times
    print(f"\n{'*'*60}")
    print(f"* MURPHY + MERS (Multi-Turn, Mean Reward)")
    print(f"{'*'*60}")
    for run in range(num_runs):
        print(f"\n--- Run {run+1}/{num_runs} ---")
        result = evaluate_murphy_parallel(problems, strategy='mers')
        all_results['murphy_mers'].append(result['pass_rate'])
    
    # Calculate statistics
    import statistics
    summary = {}
    for method, scores in all_results.items():
        summary[method] = {
            'mean': statistics.mean(scores),
            'std': statistics.stdev(scores) if len(scores) > 1 else 0.0,
            'scores': scores
        }
    
    # Print summary table
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Method':<20} {'Mean Pass@1':<15} {'Std':<10} {'Runs'}")
    print(f"{'-'*60}")
    for method, stats in summary.items():
        scores_str = ', '.join([f"{s:.2f}" for s in stats['scores']])
        print(f"{method:<20} {stats['mean']:>6.2f}%        ±{stats['std']:>5.2f}   [{scores_str}]")
    print(f"{'='*60}\n")
    
    return summary


# ============================================================
# DATASET LOADING
# ============================================================

def load_humaneval(limit: int = None) -> List[Dict]:
    """
    Load HumanEval dataset from HuggingFace.
    
    Args:
        limit: Maximum number of problems to load (None = all 164)
    
    Returns:
        List of problem dicts
    """
    print(f"📥 Loading HumanEval dataset...")
    dataset = load_dataset("openai_humaneval", split="test")
    
    problems = []
    for item in dataset:
        problems.append({
            'task_id': item['task_id'],
            'prompt': item['prompt'],
            'test': item['test'],
            'entry_point': item['entry_point']
        })
    
    if limit:
        problems = problems[:limit]
    
    print(f"✅ Loaded {len(problems)} problems\n")
    return problems


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results_csv(results: Dict, filename: str = None):
    """
    Save experiment results to CSV file.
    
    Args:
        results: Results dict from run_experiment_parallel()
        filename: Output filename (auto-generated if None)
    """
    import csv
    import os
    from datetime import datetime
    
    # Create results directory
    os.makedirs('results', exist_ok=True)
    
    # Generate filename
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/ray_results_{timestamp}.csv"
    
    # Write CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Method', 'Mean_Pass@1', 'Std_Pass@1', 'Run_Scores'])
        
        for method, stats in results.items():
            scores_str = ','.join([f"{s:.2f}" for s in stats['scores']])
            writer.writerow([
                method,
                f"{stats['mean']:.2f}",
                f"{stats['std']:.2f}",
                scores_str
            ])
    
    print(f"💾 Results saved to: {filename}")
    return filename