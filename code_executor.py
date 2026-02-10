"""
code_executor.py — Runs generated code safely and reports results
Owner: Member N211004

This file takes Python code (as a string), runs it in a safe subprocess,
checks if it passes the test cases, and returns:
  - reward: 1.0 if all tests pass, 0.0 if any fail
  - feedback: the error message (so the model can learn from it)
"""

import subprocess
import tempfile
import os
import config


def execute_code(generated_code: str, test_code: str) -> dict:
    """
    Execute generated Python code against test cases.

    Args:
        generated_code: The Python code the AI model wrote
        test_code: The test cases to check against (from HumanEval)

    Returns:
        dict with keys:
            - passed (bool): True if all tests passed
            - reward (float): 1.0 if passed, 0.0 if failed
            - error (str): Error message if failed, empty if passed
            - output (str): Standard output from running the code
    """
    # Step 1: Basic safety check
    safety_result = _safety_check(generated_code)
    if safety_result is not None:
        return safety_result

    # Step 2: Combine generated code with test cases
    full_code = generated_code + "\n\n" + test_code

    # Step 3: Write to a temporary file and run it
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        )
        tmp_file.write(full_code)
        tmp_file.flush()
        tmp_file.close()

        # Run the code in a separate process (isolated from our program)
        result = subprocess.run(
            ["python", tmp_file.name],
            capture_output=True,
            text=True,
            timeout=config.CODE_TIMEOUT
        )

        if result.returncode == 0:
            # All tests passed
            return {
                "passed": True,
                "reward": 1.0,
                "error": "",
                "output": result.stdout.strip()
            }
        else:
            # Tests failed — extract the useful error
            error_msg = _clean_error(result.stderr, tmp_file.name)
            return {
                "passed": False,
                "reward": 0.0,
                "error": error_msg,
                "output": result.stdout.strip()
            }

    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "reward": 0.0,
            "error": "TIMEOUT: Code took too long to run (possible infinite loop).",
            "output": ""
        }
    except Exception as e:
        return {
            "passed": False,
            "reward": 0.0,
            "error": f"EXECUTION ERROR: {str(e)}",
            "output": ""
        }
    finally:
        # Clean up the temporary file
        if tmp_file and os.path.exists(tmp_file.name):
            try:
                os.remove(tmp_file.name)
            except OSError:
                pass


def _safety_check(code: str) -> dict | None:
    """
    Check if code contains dangerous operations.
    Returns an error dict if unsafe, None if safe.
    """
    for blocked in config.BLOCKED_IMPORTS:
        if f"import {blocked}" in code or f"from {blocked}" in code:
            return {
                "passed": False,
                "reward": 0.0,
                "error": f"BLOCKED: Code contains forbidden import '{blocked}'.",
                "output": ""
            }

    # Check for obviously dangerous operations
    dangerous_patterns = [
        "os.remove(", "os.rmdir(", "os.system(",
        "shutil.rmtree(", "subprocess.call(",
        "eval(input", "exec(input"
    ]
    for pattern in dangerous_patterns:
        if pattern in code:
            return {
                "passed": False,
                "reward": 0.0,
                "error": f"BLOCKED: Code contains potentially dangerous operation '{pattern}'.",
                "output": ""
            }

    return None  # Code is safe


def _clean_error(stderr: str, filename: str) -> str:
    """
    Clean up error messages to be more readable.
    Remove the temp filename and keep just the useful parts.
    """
    if not stderr:
        return "Unknown error (no error output)"

    # Replace the temp file path with "solution.py" for readability
    cleaned = stderr.replace(filename, "solution.py")

    # Limit error length (very long errors aren't useful for the model)
    lines = cleaned.strip().split("\n")
    if len(lines) > 20:
        # Keep first 5 and last 15 lines (the traceback end is most useful)
        lines = lines[:5] + ["  ... (truncated) ..."] + lines[-15:]

    return "\n".join(lines)


def format_feedback(result: dict, problem_description: str = "") -> str:
    """
    Format execution results into a feedback string that can be
    sent back to the model for the next turn.

    This is the qualitative feedback mentioned in the MURPHY paper.

    Args:
        result: Output from execute_code()
        problem_description: Optional, the original problem text

    Returns:
        A formatted feedback string
    """
    if result["passed"]:
        return "All test cases passed successfully."

    feedback_parts = []
    feedback_parts.append("Your code did NOT pass the test cases.")
    feedback_parts.append("")

    if "TIMEOUT" in result["error"]:
        feedback_parts.append("Issue: Your code timed out (took too long).")
        feedback_parts.append("This usually means there is an infinite loop.")
        feedback_parts.append("Check your loop conditions and recursion base cases.")
    elif "BLOCKED" in result["error"]:
        feedback_parts.append(f"Issue: {result['error']}")
    elif "SyntaxError" in result["error"]:
        feedback_parts.append("Issue: Your code has a syntax error.")
        feedback_parts.append("Error details:")
        feedback_parts.append(result["error"])
    elif "IndentationError" in result["error"]:
        feedback_parts.append("Issue: Your code has an indentation error.")
        feedback_parts.append("Error details:")
        feedback_parts.append(result["error"])
    elif "AssertionError" in result["error"] or "AssertionError" in result["error"]:
        feedback_parts.append("Issue: One or more test assertions failed.")
        feedback_parts.append("Your code runs but produces incorrect output.")
        feedback_parts.append("Error details:")
        feedback_parts.append(result["error"])
    else:
        feedback_parts.append("Error details:")
        feedback_parts.append(result["error"])

    return "\n".join(feedback_parts)


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly to test)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Testing code_executor.py")
    print("=" * 50)

    # Test 1: Code that PASSES
    print("\nTest 1: Code that should PASS")
    print("-" * 30)
    good_code = """
def add(a, b):
    return a + b
"""
    good_test = """
assert add(2, 3) == 5
assert add(-1, 1) == 0
assert add(0, 0) == 0
print("All tests passed!")
"""
    result = execute_code(good_code, good_test)
    print(f"  Passed: {result['passed']}")
    print(f"  Reward: {result['reward']}")
    print(f"  Output: {result['output']}")
    assert result["passed"] == True, "❌ Should have passed!"
    print("  ✅ Correct!")

    # Test 2: Code that FAILS
    print("\nTest 2: Code that should FAIL")
    print("-" * 30)
    bad_code = """
def add(a, b):
    return a - b
"""
    bad_test = """
assert add(2, 3) == 5, f"Expected 5 but got {add(2, 3)}"
"""
    result = execute_code(bad_code, bad_test)
    print(f"  Passed: {result['passed']}")
    print(f"  Reward: {result['reward']}")
    print(f"  Error: {result['error'][:200]}")
    assert result["passed"] == False, "❌ Should have failed!"
    print("  ✅ Correct!")

    # Test 3: Code with SYNTAX ERROR
    print("\nTest 3: Code with syntax error")
    print("-" * 30)
    syntax_code = """
def add(a, b)
    return a + b
"""
    result = execute_code(syntax_code, good_test)
    print(f"  Passed: {result['passed']}")
    print(f"  Error: {result['error'][:200]}")
    assert result["passed"] == False, "❌ Should have failed!"
    print("  ✅ Correct!")

    # Test 4: Code with INFINITE LOOP
    print("\nTest 4: Code with infinite loop (should timeout)")
    print("-" * 30)
    loop_code = """
def add(a, b):
    while True:
        pass
"""
    result = execute_code(loop_code, good_test)
    print(f"  Passed: {result['passed']}")
    print(f"  Error: {result['error'][:200]}")
    assert result["passed"] == False, "❌ Should have failed!"
    assert "TIMEOUT" in result["error"], "❌ Should mention timeout!"
    print("  ✅ Correct!")

    # Test 5: Feedback formatting
    print("\nTest 5: Feedback formatting")
    print("-" * 30)
    bad_result = execute_code(bad_code, bad_test)
    feedback = format_feedback(bad_result)
    print(f"  Feedback:\n{feedback}")
    print("  ✅ Feedback generated!")

    print("\n" + "=" * 50)
    print("All tests passed! code_executor.py is working.")
    print("=" * 50)
