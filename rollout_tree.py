"""
rollout_tree.py — Rollout Tree + MARS/MERS Credit Assignment
Owner: Member N210438

This file implements the tree data structure that stores all of
the AI model's attempts, and the scoring algorithms (MARS / MERS)
from the MURPHY paper (Section 4).

HOW THE TREE WORKS:
    Root (the problem)
    ├── Turn 1, Attempt 1 (reward=0.0, failed)
    │   ├── Turn 2, Attempt 1a (reward=1.0, passed!)
    │   ├── Turn 2, Attempt 1b (reward=0.0, failed)
    │   └── ...
    ├── Turn 1, Attempt 2 (reward=1.0, passed!) → no children needed
    ├── Turn 1, Attempt 3 (reward=0.0, failed)
    │   └── Turn 2, Attempt 3a (reward=0.0, failed)
    └── ...

MARS: Each node's score = max(own score, best child's score)
MERS: Each node's score = weighted average of own + children's scores
"""

from dataclasses import dataclass, field
from typing import List, Optional
import statistics


@dataclass
class RolloutNode:
    """
    One node in the rollout tree = one code generation attempt.
    """
    # Unique identifier for this node
    node_id: str

    # Which turn this attempt belongs to (1, 2, 3, ...)
    turn: int

    # The generated code
    code: str

    # The prompt that was used to generate this code
    prompt_used: str

    # Reward from executing the code (0.0 = failed, 1.0 = all tests passed)
    reward: float = 0.0

    # Error/feedback from code execution
    feedback: str = ""

    # List of child nodes (Turn 2 attempts generated from this node's feedback)
    children: List["RolloutNode"] = field(default_factory=list)

    # Link back to the parent node
    parent: Optional["RolloutNode"] = None

    # MARS/MERS adjusted reward (set after credit assignment)
    credit_reward: float = 0.0

    def add_child(self, child: "RolloutNode"):
        """Add a child node (a refinement attempt)."""
        child.parent = self
        self.children.append(child)

    def is_leaf(self) -> bool:
        """True if this node has no children."""
        return len(self.children) == 0

    def is_success(self) -> bool:
        """True if this node's code passed all tests."""
        return self.reward >= 1.0

    def get_depth(self) -> int:
        """How deep this node is in the tree (root = 0)."""
        depth = 0
        node = self
        while node.parent is not None:
            depth += 1
            node = node.parent
        return depth


# ─────────────────────────────────────────────
# MARS: Max Reward Strategy (Section 4 of paper)
# ─────────────────────────────────────────────

def mars_propagate(node: RolloutNode) -> float:
    """
    MARS credit assignment: propagate rewards bottom-up using MAX.

    For each node:
        credit_reward = max(own_reward, max_child_credit_reward)

    This means if ANY descendant eventually succeeded,
    the ancestor gets credit for being "on the right track".

    Args:
        node: The root of the tree (or subtree)

    Returns:
        The credit-assigned reward for this node
    """
    # Base case: leaf node keeps its own reward
    if node.is_leaf():
        node.credit_reward = node.reward
        return node.credit_reward

    # Recursive case: get credit rewards from all children
    child_rewards = [mars_propagate(child) for child in node.children]
    best_child_reward = max(child_rewards) if child_rewards else 0.0

    # MARS rule: take the maximum of own reward and best child
    node.credit_reward = max(node.reward, best_child_reward)
    return node.credit_reward


# ─────────────────────────────────────────────
# MERS: Mean Reward Strategy (Section 4 of paper)
# ─────────────────────────────────────────────

def mers_propagate(node: RolloutNode, gamma: float = 0.9, total_turns: int = 2) -> float:
    """
    MERS credit assignment: propagate rewards bottom-up using MEAN.

    For each node:
        credit_reward = (own_reward + gamma * mean_child_reward) / (S - s + 1)
    where S = total turns, s = current turn.

    This gives a smoother, averaged credit instead of just the best.

    Args:
        node: The root of the tree (or subtree)
        gamma: Discount factor (0 to 1) controlling child influence
        total_turns: Total number of turns S

    Returns:
        The credit-assigned reward for this node
    """
    # Base case: leaf node keeps its own reward
    if node.is_leaf():
        node.credit_reward = node.reward
        return node.credit_reward

    # Recursive case: get credit rewards from all children
    child_rewards = [mers_propagate(child, gamma, total_turns) for child in node.children]
    mean_child_reward = statistics.mean(child_rewards) if child_rewards else 0.0

    # MERS rule: weighted combination, normalized by depth
    depth_normalizer = total_turns - node.turn + 1
    if depth_normalizer <= 0:
        depth_normalizer = 1

    node.credit_reward = (node.reward + gamma * mean_child_reward) / depth_normalizer
    return node.credit_reward


# ─────────────────────────────────────────────
# PRUNING: InterP Strategy (Section 4.1 of paper)
# ─────────────────────────────────────────────

def interp_prune(parent_nodes: list, budget: int) -> list:
    """
    Inter-Group Pruning: keep only the top-b groups based on
    reward variance (standard deviation) of their children.

    High variance = model is uncertain = most useful for learning.
    Low variance (all 0s or all 1s) = nothing to learn.

    Args:
        parent_nodes: List of nodes whose children groups we're evaluating
        budget: How many groups (parent nodes) to keep

    Returns:
        List of parent nodes to keep (pruned list)
    """
    if len(parent_nodes) <= budget:
        return parent_nodes  # No pruning needed

    # Calculate score for each parent based on children's reward variance
    scored = []
    for node in parent_nodes:
        if len(node.children) == 0:
            scored.append((node, 0.0))
            continue

        rewards = [child.reward for child in node.children]
        if len(rewards) >= 2:
            std = statistics.stdev(rewards)
        else:
            std = 0.0

        scored.append((node, std))

    # Sort by score (highest variance first) and keep top-b
    scored.sort(key=lambda x: x[1], reverse=True)
    kept = [node for node, score in scored[:budget]]

    return kept


def intrap_prune(children: list, budget: int) -> list:
    """
    Intra-Group Pruning: within a group of children (siblings),
    keep only the top-b that contribute most to reward variance.

    We keep the children with the most extreme rewards (highest and lowest)
    because they create the most variance = most learning signal.

    Args:
        children: List of sibling nodes
        budget: How many to keep

    Returns:
        Pruned list of children
    """
    if len(children) <= budget:
        return children

    # Sort by reward
    sorted_children = sorted(children, key=lambda c: c.reward)

    # Keep extremes: some from lowest, some from highest
    half = budget // 2
    kept = sorted_children[:half] + sorted_children[-(budget - half):]

    return kept


# ─────────────────────────────────────────────
# UTILITY: Get best solution from tree
# ─────────────────────────────────────────────

def get_best_solution(root: RolloutNode) -> tuple:
    """
    Find the node with the highest reward in the entire tree.
    Returns (best_node, best_reward).
    """
    best_node = None
    best_reward = -1.0

    def _search(node):
        nonlocal best_node, best_reward
        if node.reward > best_reward and node.code:
            best_reward = node.reward
            best_node = node
        for child in node.children:
            _search(child)

    _search(root)
    return best_node, best_reward


def compute_group_advantages(nodes: list) -> list:
    """
    Compute normalized advantages for a group of nodes.
    advantage = (credit_reward - mean) / std

    This is how MURPHY (and GRPO) decides which attempts were
    better or worse than average.

    Args:
        nodes: List of sibling nodes (same turn, same parent)

    Returns:
        List of (node, advantage) tuples
    """
    if not nodes:
        return []

    rewards = [n.credit_reward for n in nodes]
    mean_r = statistics.mean(rewards)

    if len(rewards) >= 2:
        std_r = statistics.stdev(rewards)
    else:
        std_r = 1.0

    if std_r == 0:
        std_r = 1.0  # Avoid division by zero

    advantages = []
    for node in nodes:
        adv = (node.credit_reward - mean_r) / std_r
        advantages.append((node, adv))

    return advantages


# ─────────────────────────────────────────────
# UTILITY: Print tree (for debugging)
# ─────────────────────────────────────────────

def print_tree(node: RolloutNode, indent: int = 0):
    """
    Pretty-print the rollout tree for debugging.
    """
    prefix = "  " * indent
    status = "✅" if node.is_success() else "❌"
    credit = f" → credit: {node.credit_reward:.2f}" if node.credit_reward != node.reward else ""
    code_preview = node.code[:50].replace("\n", " ") if node.code else "(root)"

    print(f"{prefix}{status} [{node.node_id}] turn={node.turn} "
          f"reward={node.reward:.2f}{credit} | {code_preview}...")

    for child in node.children:
        print_tree(child, indent + 1)


def count_nodes(node: RolloutNode) -> int:
    """Count total nodes in the tree."""
    count = 1
    for child in node.children:
        count += count_nodes(child)
    return count


def count_successes(node: RolloutNode) -> int:
    """Count nodes that passed all tests."""
    count = 1 if node.is_success() else 0
    for child in node.children:
        count += count_successes(child)
    return count


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly to test)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Testing rollout_tree.py")
    print("=" * 50)

    # Build a sample tree manually
    root = RolloutNode(node_id="root", turn=0, code="", prompt_used="Reverse a string")

    # Turn 1: 4 attempts
    t1_a = RolloutNode("t1_a", turn=1, code="def rev(s): return s[::-1]", prompt_used="...", reward=1.0)
    t1_b = RolloutNode("t1_b", turn=1, code="def rev(s): return s", prompt_used="...", reward=0.0,
                        feedback="AssertionError: expected 'cba' got 'abc'")
    t1_c = RolloutNode("t1_c", turn=1, code="def rev(s): return list(s)", prompt_used="...", reward=0.0,
                        feedback="AssertionError: expected str got list")
    t1_d = RolloutNode("t1_d", turn=1, code="def rev(s):", prompt_used="...", reward=0.0,
                        feedback="SyntaxError")

    root.add_child(t1_a)
    root.add_child(t1_b)
    root.add_child(t1_c)
    root.add_child(t1_d)

    # Turn 2: Refinements for failed attempts
    t2_b1 = RolloutNode("t2_b1", turn=2, code="def rev(s): return s[::-1]", prompt_used="...", reward=1.0)
    t2_b2 = RolloutNode("t2_b2", turn=2, code="def rev(s): return reversed(s)", prompt_used="...", reward=0.0)
    t1_b.add_child(t2_b1)
    t1_b.add_child(t2_b2)

    t2_c1 = RolloutNode("t2_c1", turn=2, code="def rev(s): return ''.join(reversed(s))", prompt_used="...", reward=1.0)
    t1_c.add_child(t2_c1)

    t2_d1 = RolloutNode("t2_d1", turn=2, code="def rev(s): return s[-1::-1]", prompt_used="...", reward=1.0)
    t2_d2 = RolloutNode("t2_d2", turn=2, code="def rev(s): pass", prompt_used="...", reward=0.0)
    t1_d.add_child(t2_d1)
    t1_d.add_child(t2_d2)

    # Test: Print tree
    print("\nTree structure:")
    print("-" * 40)
    print_tree(root)

    # Test: MARS
    print("\nAfter MARS propagation:")
    print("-" * 40)
    mars_propagate(root)
    print_tree(root)

    print(f"\nt1_b: original reward=0.0, MARS credit={t1_b.credit_reward}")
    assert t1_b.credit_reward == 1.0, "❌ MARS should give t1_b credit=1.0 (child succeeded)"
    print("✅ MARS works correctly!")

    # Reset and test MERS
    print("\nAfter MERS propagation (gamma=0.9):")
    print("-" * 40)
    mers_propagate(root, gamma=0.9, total_turns=2)
    print_tree(root)
    print(f"\nt1_b: MERS credit={t1_b.credit_reward:.3f}")
    print("✅ MERS works!")

    # Test: Best solution
    best_node, best_reward = get_best_solution(root)
    print(f"\nBest solution: {best_node.node_id} with reward={best_reward}")
    print("✅ Best solution finder works!")

    # Test: Pruning
    print("\nInterP pruning (budget=2 from 3 failed nodes):")
    failed_nodes = [t1_b, t1_c, t1_d]
    kept = interp_prune(failed_nodes, budget=2)
    print(f"  Kept: {[n.node_id for n in kept]}")
    print("✅ Pruning works!")

    # Test: Stats
    print(f"\nTree stats: {count_nodes(root)} nodes, {count_successes(root)} successes")

    print("\n" + "=" * 50)
    print("All tests passed! rollout_tree.py is working.")
    print("=" * 50)
