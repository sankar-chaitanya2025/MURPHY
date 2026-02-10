"""
main.py — Entry point for the MURPHY project
Owner: Chaitanya (Team Lead)

Usage:
    python main.py --mode demo          Run one problem (quick test)
    python main.py --mode baseline      Run single-turn baseline
    python main.py --mode murphy        Run MURPHY multi-turn
    python main.py --mode experiment    Run full experiment (baseline + MARS + MERS)
    python main.py --mode tree-test     Test the tree + MARS without model
"""

import argparse
import sys
import config


def run_demo():
    """Run MURPHY on a single HumanEval problem to show it working."""
    from evaluator import load_humaneval, extract_test_code
    from murphy_engine import run_murphy

    print("=" * 60)
    print("MURPHY DEMO — Single Problem")
    print("=" * 60)

    problems = load_humaneval(limit=1)
    if not problems:
        print("Could not load HumanEval. Run: pip install datasets")
        return

    problem = problems[0]
    test_code = extract_test_code(problem)

    print(f"\nProblem: {problem['task_id']}")
    print(f"Function: {problem['entry_point']}")
    print(f"Prompt:\n{problem['prompt']}")
    print("-" * 60)

    result = run_murphy(
        problem=problem,
        test_code=test_code,
        strategy="mars",
        num_generations=config.NUM_GENERATIONS,
        num_turns=config.NUM_TURNS,
        verbose=True
    )

    print(f"\n{'='*60}")
    print(f"DEMO RESULT:")
    print(f"  Solved: {'YES ✅' if result['solved'] else 'NO ❌'}")
    print(f"  Best reward: {result['best_reward']:.2f}")
    print(f"  Total model calls: {result['total_generations']}")
    print(f"  Time: {result['time_seconds']:.1f}s")
    if result['best_code']:
        print(f"\nBest code found:")
        print("-" * 40)
        print(result['best_code'])
    print("=" * 60)


def run_baseline_eval(num_problems):
    """Run single-turn baseline evaluation."""
    from evaluator import load_humaneval, evaluate_baseline

    problems = load_humaneval(limit=num_problems)
    if not problems:
        return
    evaluate_baseline(problems)


def run_murphy_eval(num_problems, strategy):
    """Run MURPHY evaluation."""
    from evaluator import load_humaneval, evaluate_murphy

    problems = load_humaneval(limit=num_problems)
    if not problems:
        return
    evaluate_murphy(problems, strategy=strategy)


def run_full_experiment(num_problems, num_runs):
    """Run full experiment with all methods, multiple runs."""
    from evaluator import load_humaneval, run_experiment, save_results

    problems = load_humaneval(limit=num_problems)
    if not problems:
        return

    results = run_experiment(problems, num_runs=num_runs)
    save_results(results)


def run_tree_test():
    """
    Test the rollout tree + MARS/MERS WITHOUT needing the model.
    Good for testing when Ollama is not available.
    """
    from rollout_tree import (
        RolloutNode, mars_propagate, mers_propagate,
        interp_prune, get_best_solution, print_tree,
        compute_group_advantages
    )

    print("=" * 60)
    print("TREE TEST — No model needed")
    print("=" * 60)

    # Build a sample tree
    root = RolloutNode("root", turn=0, code="", prompt_used="Problem X")

    # Turn 1: 4 attempts with different rewards
    t1 = []
    rewards = [0.0, 0.0, 1.0, 0.0]
    for i, r in enumerate(rewards):
        node = RolloutNode(
            f"t1_{i}", turn=1,
            code=f"# attempt {i}",
            prompt_used="...",
            reward=r,
            feedback=f"Error in attempt {i}" if r < 1.0 else ""
        )
        root.add_child(node)
        t1.append(node)

    # Turn 2: Refinements for failed attempts
    t2_rewards = {
        0: [1.0, 0.0, 0.0, 0.5],  # First failed → one child succeeds
        1: [0.0, 0.0, 0.0, 0.0],  # Second failed → all children fail
        3: [0.5, 1.0, 0.0, 0.0],  # Fourth failed → one child succeeds
    }

    for parent_idx, child_rewards in t2_rewards.items():
        for j, cr in enumerate(child_rewards):
            child = RolloutNode(
                f"t2_{parent_idx}_{j}", turn=2,
                code=f"# refined {parent_idx}-{j}",
                prompt_used="...",
                reward=cr
            )
            t1[parent_idx].add_child(child)

    # Before credit assignment
    print("\nBEFORE credit assignment:")
    print_tree(root)

    # MARS
    print("\nAfter MARS:")
    mars_propagate(root)
    print_tree(root)

    # Show advantages
    print("\nTurn 1 advantages (MARS):")
    advantages = compute_group_advantages(t1)
    for node, adv in advantages:
        print(f"  {node.node_id}: credit={node.credit_reward:.2f}, advantage={adv:+.2f}")

    # Pruning demo
    print("\nPruning demo (budget=2 from 3 failed):")
    failed = [t1[0], t1[1], t1[3]]
    kept = interp_prune(failed, budget=2)
    print(f"  Kept: {[n.node_id for n in kept]}")
    print(f"  Pruned: {[n.node_id for n in failed if n not in kept]}")

    # Best solution
    best, reward = get_best_solution(root)
    print(f"\nBest solution: {best.node_id} (reward={reward})")

    print("\n" + "=" * 60)
    print("✅ Tree test complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="MURPHY: Multi-Turn Self-Correcting Code Generation Agent",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "baseline", "murphy", "experiment", "tree-test"],
        default="demo",
        help="""Which mode to run:
  demo       — Run one problem with verbose output (quick test)
  baseline   — Single-turn evaluation (no feedback)
  murphy     — MURPHY multi-turn evaluation
  experiment — Full experiment: baseline + MARS + MERS, multiple runs
  tree-test  — Test tree + MARS/MERS without needing the model"""
    )
    parser.add_argument(
        "--problems", type=int, default=config.NUM_PROBLEMS,
        help=f"Number of HumanEval problems to evaluate (default: {config.NUM_PROBLEMS})"
    )
    parser.add_argument(
        "--runs", type=int, default=config.NUM_RUNS,
        help=f"Number of experiment runs (default: {config.NUM_RUNS})"
    )
    parser.add_argument(
        "--strategy", choices=["mars", "mers"], default="mars",
        help="Credit assignment strategy (default: mars)"
    )
    parser.add_argument(
        "--generations", type=int, default=None,
        help=f"Override G (generations per turn, default: {config.NUM_GENERATIONS})"
    )

    args = parser.parse_args()

    # Override config if specified
    if args.generations:
        config.NUM_GENERATIONS = args.generations

    # Run selected mode
    if args.mode == "demo":
        run_demo()
    elif args.mode == "baseline":
        run_baseline_eval(args.problems)
    elif args.mode == "murphy":
        run_murphy_eval(args.problems, args.strategy)
    elif args.mode == "experiment":
        run_full_experiment(args.problems, args.runs)
    elif args.mode == "tree-test":
        run_tree_test()


if __name__ == "__main__":
    main()
