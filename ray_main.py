"""
Ray-enabled entry point for MURPHY experiments.
This replaces main.py for parallel execution.

Usage:
    python ray_main.py --mode murphy --problems 10 --strategy mars
    python ray_main.py --mode baseline --problems 10
    python ray_main.py --mode experiment --problems 164 --runs 3
    python ray_main.py --mode demo --profile workstation
"""

import argparse
import ray
import sys

# Import Ray modules
import ray_config
from ray_evaluator import (
    load_humaneval,
    evaluate_murphy_parallel,
    evaluate_baseline_parallel,
    run_experiment_parallel,
    save_results_csv
)

# Import original config for display
from config import MODEL_NAME, NUM_GENERATIONS, NUM_TURNS


def print_banner():
    """Print startup banner"""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   MURPHY Multi-Turn Code Generation Agent               ║
║   🚀 RAY-ENABLED PARALLEL VERSION 🚀                    ║
║                                                          ║
║   Model: {MODEL_NAME:<42} ║
║   Generations (G): {NUM_GENERATIONS:<2}  Turns (S): {NUM_TURNS:<2}                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def init_ray(profile: str = None):
    """
    Initialize Ray with appropriate settings.
    
    Args:
        profile: Deployment profile ('laptop', 'workstation', 'server', 'cluster')
    """
    # Apply profile if specified
    if profile:
        ray_config.quick_setup(profile)
    
    # Initialize Ray
    print(f"\n🔧 Initializing Ray...")
    print(f"   Profile: {profile or 'default'}")
    print(f"   Max parallel tasks: {ray_config.MAX_PARALLEL_TASKS or 'AUTO'}")
    print(f"   Ollama URL: {ray_config.OLLAMA_URL}")
    
    ray.init(**ray_config.get_ray_init_kwargs())
    
    # Print Ray info
    print(f"\n✅ Ray initialized successfully!")
    print(f"   Available CPUs: {ray.available_resources().get('CPU', 'N/A')}")
    print(f"   Available memory: {ray.available_resources().get('memory', 0) / (1024**3):.1f} GB")
    
    if ray_config.ENABLE_RAY_DASHBOARD:
        print(f"   Dashboard: http://localhost:8265")
    
    print()


def mode_demo(args):
    """Run demo mode (single problem, verbose output)"""
    print("\n🎯 DEMO MODE: Running single problem with detailed output\n")
    
    problems = load_humaneval(limit=1)
    result = evaluate_murphy_parallel(problems, strategy=args.strategy)
    
    print("\n📋 Demo Summary:")
    print(f"   Problem: {problems[0]['task_id']}")
    print(f"   Solved: {'✅ YES' if result['solved_count'] > 0 else '❌ NO'}")
    print(f"   Time: {result['time_seconds']:.1f}s")
    print()


def mode_baseline(args):
    """Run baseline evaluation (single-turn, no feedback)"""
    print(f"\n📊 BASELINE MODE: Evaluating {args.problems} problems\n")
    
    problems = load_humaneval(limit=args.problems)
    result = evaluate_baseline_parallel(problems)
    
    # Save results
    import csv
    import os
    from datetime import datetime
    
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/ray_baseline_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['task_id', 'solved', 'reward'])
        for r in result['results']:
            writer.writerow([r['task_id'], r['solved'], r['reward']])
    
    print(f"💾 Results saved to: {filename}\n")


def mode_murphy(args):
    """Run MURPHY evaluation (multi-turn with feedback)"""
    print(f"\n🧠 MURPHY MODE: Evaluating {args.problems} problems with {args.strategy.upper()}\n")
    
    problems = load_humaneval(limit=args.problems)
    result = evaluate_murphy_parallel(problems, strategy=args.strategy)
    
    # Save results
    import csv
    import os
    from datetime import datetime
    
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/ray_murphy_{args.strategy}_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['task_id', 'solved', 'reward', 'generations'])
        for r in result['results']:
            writer.writerow([r['task_id'], r['solved'], r['reward'], r['generations']])
    
    print(f"💾 Results saved to: {filename}\n")


def mode_experiment(args):
    """Run full experiment (baseline + MARS + MERS, multiple runs)"""
    print(f"\n🔬 EXPERIMENT MODE: Full evaluation with {args.runs} runs\n")
    
    problems = load_humaneval(limit=args.problems)
    results = run_experiment_parallel(problems, num_runs=args.runs)
    
    # Save results
    filename = save_results_csv(results)
    print(f"\n✅ Experiment complete! Results saved to: {filename}\n")


def mode_compare(args):
    """Run side-by-side comparison of baseline vs MURPHY"""
    print(f"\n⚖️  COMPARISON MODE: Baseline vs MURPHY on {args.problems} problems\n")
    
    problems = load_humaneval(limit=args.problems)
    
    # Run baseline
    print("\n" + "="*60)
    print("PHASE 1: BASELINE")
    print("="*60)
    baseline_result = evaluate_baseline_parallel(problems)
    
    # Run MURPHY
    print("\n" + "="*60)
    print(f"PHASE 2: MURPHY ({args.strategy.upper()})")
    print("="*60)
    murphy_result = evaluate_murphy_parallel(problems, strategy=args.strategy)
    
    # Print comparison
    print("\n" + "="*60)
    print("📊 COMPARISON RESULTS")
    print("="*60)
    print(f"{'Method':<20} {'Pass@1':<12} {'Solved':<10} {'Time'}")
    print("-"*60)
    print(f"{'Baseline':<20} {baseline_result['pass_rate']:>6.2f}%     "
          f"{baseline_result['solved_count']:>3}/{baseline_result['total_problems']:<3}    "
          f"{baseline_result['time_seconds']:.1f}s")
    print(f"{'MURPHY (' + args.strategy.upper() + ')':<20} {murphy_result['pass_rate']:>6.2f}%     "
          f"{murphy_result['solved_count']:>3}/{murphy_result['total_problems']:<3}    "
          f"{murphy_result['time_seconds']:.1f}s")
    
    improvement = murphy_result['pass_rate'] - baseline_result['pass_rate']
    print(f"\n{'Improvement':<20} {improvement:>+6.2f}%")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="MURPHY Multi-Turn Code Generation Agent (Ray-Enabled)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo with single problem
  python ray_main.py --mode demo --profile workstation
  
  # Baseline evaluation (10 problems)
  python ray_main.py --mode baseline --problems 10
  
  # MURPHY with MARS (10 problems)
  python ray_main.py --mode murphy --problems 10 --strategy mars
  
  # Full experiment (164 problems, 3 runs each)
  python ray_main.py --mode experiment --problems 164 --runs 3
  
  # Quick comparison
  python ray_main.py --mode compare --problems 10 --strategy mars
  
Deployment Profiles:
  --profile laptop       : 4 parallel tasks (for laptops)
  --profile workstation  : 12 parallel tasks (for lab computers)
  --profile server       : 48 parallel tasks (for servers)
  --profile cluster      : Unlimited tasks (for Ray clusters)
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['demo', 'baseline', 'murphy', 'experiment', 'compare'],
        help='Execution mode'
    )
    
    # Problem count
    parser.add_argument(
        '--problems',
        type=int,
        default=10,
        help='Number of HumanEval problems to evaluate (default: 10, max: 164)'
    )
    
    # Strategy for MURPHY
    parser.add_argument(
        '--strategy',
        type=str,
        default='mars',
        choices=['mars', 'mers'],
        help='Credit assignment strategy for MURPHY mode (default: mars)'
    )
    
    # Number of runs for experiment mode
    parser.add_argument(
        '--runs',
        type=int,
        default=3,
        help='Number of runs for experiment mode (default: 3)'
    )
    
    # Deployment profile
    parser.add_argument(
        '--profile',
        type=str,
        default=None,
        choices=['laptop', 'workstation', 'server', 'cluster'],
        help='Deployment profile (auto-configures parallelism)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Initialize Ray
    init_ray(profile=args.profile)
    
    # Run selected mode
    try:
        if args.mode == 'demo':
            mode_demo(args)
        elif args.mode == 'baseline':
            mode_baseline(args)
        elif args.mode == 'murphy':
            mode_murphy(args)
        elif args.mode == 'experiment':
            mode_experiment(args)
        elif args.mode == 'compare':
            mode_compare(args)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Shutting down Ray...\n")
    
    except Exception as e:
        print(f"\n\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
    
    finally:
        # Shutdown Ray
        print("\n🔌 Shutting down Ray...")
        ray.shutdown()
        print("✅ Done!\n")


if __name__ == '__main__':
    main()