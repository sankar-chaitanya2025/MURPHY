"""
murphy_engine.py — The Core MURPHY Multi-Turn Engine
Owner: Member N210109

This is the HEART of the project. It runs the multi-turn loop:
  Turn 1: Generate G solutions → Execute → Score → Get feedback
  Turn 2: For failed solutions, send feedback → Generate G more → Execute → Score
  Then: Run MARS/MERS credit assignment → Pick best solution

This file connects model_client, code_executor, and rollout_tree together.
"""

import time
import config
from model_client import generate_multiple
from code_executor import execute_code, format_feedback
from rollout_tree import (
    RolloutNode, mars_propagate, mers_propagate,
    interp_prune, get_best_solution, print_tree,
    count_nodes, count_successes
)


def build_initial_prompt(problem: dict) -> str:
    """
    Build the Turn 1 prompt from a HumanEval problem.

    Args:
        problem: Dict with 'prompt' key (the function signature + docstring)

    Returns:
        A prompt string to send to the model
    """
    return f"""Write a Python function to solve the following problem.
Return ONLY the Python code. No explanations, no markdown, no extra text.

{problem['prompt']}"""


def build_refinement_prompt(original_prompt: str, failed_code: str,
                             feedback: str, turn: int) -> str:
    """
    Build the Turn 2+ prompt that includes feedback from the failed attempt.
    This is the key MURPHY innovation — feeding errors back to the model.

    Args:
        original_prompt: The original problem prompt
        failed_code: The code that failed
        feedback: Error message / execution feedback
        turn: Current turn number

    Returns:
        A refinement prompt string
    """
    return f"""You are solving a Python coding problem. Your previous attempt failed.
Analyze the error and provide a corrected solution.
Return ONLY the Python code. No explanations, no markdown, no extra text.

## Original Problem
{original_prompt}

## Your Previous Attempt (Turn {turn - 1})
{failed_code}

## Execution Feedback
{feedback}

## Instructions
Fix the issues identified above. Write the complete corrected Python function."""


def run_murphy(problem: dict, test_code: str,
               strategy: str = "mars",
               num_generations: int = None,
               num_turns: int = None,
               pruning_budget: int = None,
               verbose: bool = False) -> dict:
    """
    Run the full MURPHY multi-turn pipeline on a single problem.

    Args:
        problem: Dict with 'prompt' and optionally 'entry_point'
        test_code: The test cases to evaluate against
        strategy: "mars" or "mers" for credit assignment
        num_generations: G (overrides config)
        num_turns: S (overrides config)
        pruning_budget: b (overrides config)
        verbose: Print detailed progress

    Returns:
        Dict with:
            - solved (bool): Whether any solution passed all tests
            - best_code (str): The best solution found
            - best_reward (float): Highest reward achieved
            - tree_stats (dict): Statistics about the rollout tree
            - total_generations (int): Total API calls made
            - time_seconds (float): Total time taken
    """
    G = num_generations or config.NUM_GENERATIONS
    S = num_turns or config.NUM_TURNS
    b = pruning_budget or config.PRUNING_BUDGET

    start_time = time.time()
    total_generations = 0

    # Create the root node
    root = RolloutNode(
        node_id="root",
        turn=0,
        code="",
        prompt_used=problem["prompt"]
    )

    initial_prompt = build_initial_prompt(problem)

    if verbose:
        print(f"\n{'='*60}")
        print(f"MURPHY Engine: Starting (G={G}, S={S}, strategy={strategy})")
        print(f"{'='*60}")

    # ─────────────────────────────────────────
    # TURN 1: Generate initial candidates
    # ─────────────────────────────────────────
    if verbose:
        print(f"\n--- Turn 1: Generating {G} candidates ---")

    codes = generate_multiple(initial_prompt, n=G)
    total_generations += len(codes)

    for i, code in enumerate(codes):
        # Execute the generated code
        result = execute_code(code, test_code)

        # Create tree node
        node = RolloutNode(
            node_id=f"t1_{i}",
            turn=1,
            code=code,
            prompt_used=initial_prompt,
            reward=result["reward"],
            feedback=result["error"]
        )
        root.add_child(node)

        if verbose:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  Candidate {i+1}: {status} (reward={result['reward']:.1f})")

    # ─────────────────────────────────────────
    # TURNS 2 to S: Refinement with feedback
    # ─────────────────────────────────────────
    current_turn_nodes = root.children  # Start with Turn 1 nodes

    for turn in range(2, S + 1):
        # Find nodes that failed (need refinement)
        failed_nodes = [n for n in current_turn_nodes if not n.is_success()]

        if not failed_nodes:
            if verbose:
                print(f"\n--- Turn {turn}: All solved! Skipping. ---")
            break

        if verbose:
            print(f"\n--- Turn {turn}: Refining {len(failed_nodes)} failed candidates ---")

        # PRUNING: If too many failed, keep only the most informative ones
        if len(failed_nodes) > b:
            if verbose:
                print(f"  Pruning: {len(failed_nodes)} failed → keeping top {b}")
            failed_nodes = interp_prune(failed_nodes, budget=b)

        next_turn_nodes = []

        for failed_node in failed_nodes:
            # Build refinement prompt with feedback
            feedback_text = format_feedback(
                {"passed": False, "reward": failed_node.reward,
                 "error": failed_node.feedback, "output": ""},
                problem["prompt"]
            )
            refinement_prompt = build_refinement_prompt(
                original_prompt=problem["prompt"],
                failed_code=failed_node.code,
                feedback=feedback_text,
                turn=turn
            )

            # Generate new candidates conditioned on feedback
            refined_codes = generate_multiple(refinement_prompt, n=G)
            total_generations += len(refined_codes)

            for j, rcode in enumerate(refined_codes):
                result = execute_code(rcode, test_code)

                refined_node = RolloutNode(
                    node_id=f"t{turn}_{failed_node.node_id}_{j}",
                    turn=turn,
                    code=rcode,
                    prompt_used=refinement_prompt,
                    reward=result["reward"],
                    feedback=result["error"]
                )
                failed_node.add_child(refined_node)
                next_turn_nodes.append(refined_node)

                if verbose:
                    status = "✅ PASS" if result["passed"] else "❌ FAIL"
                    print(f"  {failed_node.node_id} → Refinement {j+1}: {status}")

        current_turn_nodes = next_turn_nodes

    # ─────────────────────────────────────────
    # CREDIT ASSIGNMENT (MARS or MERS)
    # ─────────────────────────────────────────
    if strategy == "mars":
        mars_propagate(root)
    elif strategy == "mers":
        mers_propagate(root, gamma=config.MERS_GAMMA, total_turns=S)
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'mars' or 'mers'.")

    # ─────────────────────────────────────────
    # FIND BEST SOLUTION
    # ─────────────────────────────────────────
    best_node, best_reward = get_best_solution(root)
    solved = best_reward >= 1.0

    elapsed = time.time() - start_time

    if verbose:
        print(f"\n--- Result ---")
        print(f"  Solved: {'YES ✅' if solved else 'NO ❌'}")
        print(f"  Best reward: {best_reward:.2f}")
        print(f"  Total generations: {total_generations}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"\nTree:")
        print_tree(root)

    return {
        "solved": solved,
        "best_code": best_node.code if best_node else "",
        "best_reward": best_reward,
        "tree_stats": {
            "total_nodes": count_nodes(root),
            "successes": count_successes(root),
        },
        "total_generations": total_generations,
        "time_seconds": elapsed,
        "root": root  # Keep tree reference for analysis
    }


def murphy_solve(problem: str, test_code: str,
                 entry_point: str = None,
                 strategy: str = "mars",
                 num_generations: int = None,
                 num_turns: int = None,
                 verbose: bool = False) -> dict:
    """
    Wrapper for Ray/evaluator: accepts prompt, test_code, entry_point as separate args.
    Calls run_murphy under the hood.
    """
    problem_dict = {"prompt": problem}
    if entry_point:
        problem_dict["entry_point"] = entry_point
    return run_murphy(
        problem=problem_dict,
        test_code=test_code,
        strategy=strategy,
        num_generations=num_generations,
        num_turns=num_turns,
        verbose=verbose
    )


def run_single_turn(problem: dict, test_code: str,
                     num_generations: int = None,
                     verbose: bool = False) -> dict:
    """
    Run SINGLE-TURN baseline (no feedback, no refinement).
    This is the comparison point — plain generation without MURPHY.

    Same inputs/outputs as run_murphy but with S=1 (no Turn 2).
    """
    return run_murphy(
        problem=problem,
        test_code=test_code,
        strategy="mars",
        num_generations=num_generations,
        num_turns=1,
        verbose=verbose
    )


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly to test)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Testing murphy_engine.py")
    print("NOTE: This requires Ollama to be running!")
    print("If Ollama is not running, you'll see a connection error.")
    print("=" * 60)

    # A simple test problem (similar to HumanEval format)
    test_problem = {
        "prompt": """def add(a: int, b: int) -> int:
    \"\"\"Return the sum of a and b.
    >>> add(2, 3)
    5
    >>> add(-1, 1)
    0
    \"\"\"
""",
        "entry_point": "add"
    }

    test_cases = """
assert add(2, 3) == 5
assert add(-1, 1) == 0
assert add(0, 0) == 0
assert add(100, -100) == 0
"""

    print("\nRunning MURPHY (G=2, S=2, MARS)...")
    try:
        result = run_murphy(
            problem=test_problem,
            test_code=test_cases,
            strategy="mars",
            num_generations=2,
            num_turns=2,
            verbose=True
        )
        print(f"\nFinal: solved={result['solved']}, "
              f"generations={result['total_generations']}, "
              f"time={result['time_seconds']:.1f}s")
    except ConnectionError as e:
        print(f"\n❌ {e}")
        print("\nTo test, start Ollama first:")
        print("  1. Open a terminal")
        print("  2. Run: ollama serve")
        print("  3. In another terminal: ollama pull qwen2.5-coder:7b")
        print("  4. Then run this script again")
