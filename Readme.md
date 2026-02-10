# MURPHY-Inspired Multi-Turn Code Generation Agent

A multi-turn self-correcting code generation system based on the
[MURPHY paper](https://arxiv.org/abs/2511.07833) — *Multi-Turn GRPO for Self-Correcting Code Generation*.

Built by CSE students at RGUKT Nuzvid under the guidance of Dr. A. Udaya Kumar.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [File Structure](#file-structure)
3. [Phase 1: Setup on Your Laptop (No GPU Needed)](#phase-1-setup-on-your-laptop-no-gpu-needed)
4. [Phase 2: Test Core Logic on Your Laptop](#phase-2-test-core-logic-on-your-laptop)
5. [Phase 3: Lab Setup (Ollama + Model)](#phase-3-lab-setup-ollama--model)
6. [Phase 4: First Real Run (Single Problem Demo)](#phase-4-first-real-run-single-problem-demo)
7. [Phase 5: Baseline Evaluation (Single-Turn, No Feedback)](#phase-5-baseline-evaluation-single-turn-no-feedback)
8. [Phase 6: MURPHY Evaluation (Multi-Turn With Feedback)](#phase-6-murphy-evaluation-multi-turn-with-feedback)
9. [Phase 7: Full Experiment (Baseline vs MARS vs MERS)](#phase-7-full-experiment-baseline-vs-mars-vs-mers)
10. [Phase 8: Ablation Studies](#phase-8-ablation-studies)
11. [Phase 9: Results Collection and Report](#phase-9-results-collection-and-report)
12. [Config Reference](#config-reference)
13. [Troubleshooting](#troubleshooting)
14. [Team Responsibilities](#team-responsibilities)

---

## What This Project Does

```
Coding Problem
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  TURN 1: Model generates G=4 code solutions          │
│          Each solution is executed against test cases  │
│          Result: reward (0.0 = fail, 1.0 = pass)      │
│          Failed solutions get error feedback           │
└──────────────────┬───────────────────────────────────┘
                   │ failed solutions + error feedback
                   ▼
┌──────────────────────────────────────────────────────┐
│  TURN 2: Model receives error feedback                │
│          Generates G=4 NEW solutions per failure      │
│          Each new solution is executed and scored      │
└──────────────────┬───────────────────────────────────┘
                   │ all rewards collected
                   ▼
┌──────────────────────────────────────────────────────┐
│  CREDIT ASSIGNMENT (MARS or MERS)                     │
│  MARS: parent score = max(own score, best child)      │
│  MERS: parent score = avg(own score, mean of children)│
│                                                        │
│  PRUNING (InterP): drop hopeless branches early        │
│                                                        │
│  OUTPUT: best solution from the entire tree            │
└──────────────────────────────────────────────────────┘
```

---

## File Structure

```
murphy-project/
├── config.py            ← All settings (model, G, S, timeouts)
├── model_client.py      ← Sends prompts to Ollama, gets code back
├── code_executor.py     ← Runs generated code, returns pass/fail + errors
├── rollout_tree.py      ← Tree data structure + MARS + MERS + pruning
├── murphy_engine.py     ← Multi-turn loop (connects all modules)
├── evaluator.py         ← Loads HumanEval, runs experiments, saves CSV
├── main.py              ← Entry point (run this)
├── requirements.txt     ← Python packages needed
├── .gitignore           ← Files to ignore in git
└── results/             ← Created automatically when experiments run
```

---

## Phase 1: Setup on Your Laptop (No GPU Needed)

These steps work on ANY computer. No AI model needed yet.

### Step 1.1: Make sure Python is installed

Open your terminal and run:

```bash
python --version
```

You should see `Python 3.10.x` or `3.11.x` or similar. If you get an error:
- **Linux (Ubuntu):** `sudo apt install python3 python3-venv python3-pip`
- **Windows:** Download from https://python.org/downloads — check "Add to PATH" during install
- **Mac:** `brew install python`

### Step 1.2: Clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/murphy-project.git
cd murphy-project
```

Or if you already have the files, just `cd` into the folder:

```bash
cd ~/Desktop/murphy-project
```

### Step 1.3: Create virtual environment

```bash
python -m venv venv
```

### Step 1.4: Activate virtual environment

**Linux / Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

You should see `(venv)` at the start of your terminal prompt. This means the virtual environment is active. **You must activate this every time you open a new terminal.**

### Step 1.5: Install Python packages

```bash
pip install -r requirements.txt
```

This installs `requests` and `datasets`. Takes about 1-2 minutes.

### Step 1.6: Verify installation

```bash
pip list | grep -E "requests|datasets"
```

You should see both packages listed.

**Phase 1 is done.** Nothing runs yet, but your environment is ready.

---

## Phase 2: Test Core Logic on Your Laptop

These tests use NO model, NO internet, NO GPU. They verify the algorithms work.

### Step 2.1: Test the rollout tree + MARS + MERS + pruning

```bash
python -c "
from rollout_tree import RolloutNode, mars_propagate, mers_propagate, interp_prune, print_tree

# Build a small test tree
root = RolloutNode('root', turn=0, code='', prompt_used='Test problem')

# Turn 1: two attempts, one passes, one fails
t1_pass = RolloutNode('t1_pass', turn=1, code='def f(): return 1', prompt_used='...', reward=1.0)
t1_fail = RolloutNode('t1_fail', turn=1, code='def f(): return 0', prompt_used='...', reward=0.0)
root.add_child(t1_pass)
root.add_child(t1_fail)

# Turn 2: the failed attempt gets refined, one child succeeds
t2_fixed = RolloutNode('t2_fixed', turn=2, code='def f(): return 1', prompt_used='...', reward=1.0)
t2_still_bad = RolloutNode('t2_bad', turn=2, code='def f(): return -1', prompt_used='...', reward=0.0)
t1_fail.add_child(t2_fixed)
t1_fail.add_child(t2_still_bad)

print('BEFORE MARS:')
print_tree(root)

mars_propagate(root)

print('\nAFTER MARS:')
print_tree(root)

print(f'\nt1_fail started at reward=0.0, after MARS: credit={t1_fail.credit_reward}')
assert t1_fail.credit_reward == 1.0, 'MARS FAILED'
print('MARS works correctly!')
"
```

**Expected:** `t1_fail` starts with reward 0.0, but MARS updates it to 1.0 because its child `t2_fixed` succeeded.

### Step 2.2: Test the code executor

```bash
python -c "
from code_executor import execute_code, format_feedback

# Test 1: Good code
result = execute_code('def add(a,b): return a+b', 'assert add(2,3)==5')
print(f'Good code: passed={result[\"passed\"]}, reward={result[\"reward\"]}')
assert result['passed'] == True

# Test 2: Bad code
result = execute_code('def add(a,b): return a-b', 'assert add(2,3)==5')
print(f'Bad code:  passed={result[\"passed\"]}, reward={result[\"reward\"]}')
print(f'Error: {result[\"error\"][:100]}')
assert result['passed'] == False

# Test 3: Feedback formatting
feedback = format_feedback(result)
print(f'\nFormatted feedback:\n{feedback}')

print('\nAll executor tests passed!')
"
```

**Expected:** Good code passes (reward=1.0), bad code fails (reward=0.0) with error message.

### Step 2.3: Test the full tree pipeline (no model)

```bash
python main.py --mode tree-test
```

**Expected:** A full tree is built with fake data, MARS propagates rewards, pruning removes useless branches, advantages are computed. All should work.

**Phase 2 is done.** All core MURPHY algorithms are verified. Screenshot these outputs for your records.

---

## Phase 3: Lab Setup (Ollama + Model)

Do this on a lab computer with decent specs (16GB+ RAM recommended).

### Step 3.1: Install Ollama

**Linux (most lab machines):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
- Go to https://ollama.com/download
- Download and run the Windows installer
- Click Next through all screens

**Verify it installed:**
```bash
ollama --version
```

If you see a version number, it worked. If you get "Permission denied" or "command not found":
- Ask your lab administrator to install it
- Or try: `sudo curl -fsSL https://ollama.com/install.sh | sh`

### Step 3.2: Start Ollama server

Open a terminal and run:

```bash
ollama serve
```

**Leave this terminal open. Do not close it.** This is the server that your code talks to. You will do everything else in a SECOND terminal.

### Step 3.3: Download the AI model

Open a **second terminal** and run:

```bash
ollama pull qwen2.5-coder:7b
```

This downloads ~4.7 GB. It will show a progress bar. Wait for it to finish.

**If your lab computer has only 8GB RAM**, use the smaller model instead:
```bash
ollama pull qwen2.5-coder:1.5b
```
And change `config.py` line: `MODEL_NAME = "qwen2.5-coder:1.5b"`

### Step 3.4: Test the model manually

```bash
ollama run qwen2.5-coder:7b
```

Type this prompt:
```
Write a Python function to reverse a string
```

If it responds with Python code, the model works. Type `/bye` to exit.

### Step 3.5: Set up the project on the lab machine

```bash
git clone https://github.com/YOUR_USERNAME/murphy-project.git
cd murphy-project
python -m venv venv
source venv/bin/activate          # Linux
pip install -r requirements.txt
```

### Step 3.6: Test the model connection from Python

Make sure the `ollama serve` terminal is still running, then:

```bash
python -c "
from model_client import generate_code
code = generate_code('Write a Python function called add(a, b) that returns a + b.')
print('Generated code:')
print(code)
print('\nModel connection works!')
"
```

**Expected:** The model generates a Python function. This may take 10-30 seconds the first time (model loading into RAM).

**Phase 3 is done.** You now have a working AI model connected to your code.

---

## Phase 4: First Real Run (Single Problem Demo)

This runs the complete MURPHY pipeline on ONE HumanEval problem.

### Step 4.1: Run the demo

Make sure `ollama serve` is running in another terminal, then:

```bash
python main.py --mode demo
```

### Step 4.2: What you should see

```
============================================================
MURPHY Engine: Starting (G=4, S=2, strategy=mars)
============================================================

--- Turn 1: Generating 4 candidates ---
  Candidate 1: FAIL (reward=0.0)
  Candidate 2: PASS (reward=1.0)
  Candidate 3: FAIL (reward=0.0)
  Candidate 4: FAIL (reward=0.0)

--- Turn 2: Refining 3 failed candidates ---
  t1_0 -> Refinement 1: PASS
  t1_0 -> Refinement 2: FAIL
  ...

--- Result ---
  Solved: YES
  Best reward: 1.00
  Total generations: 16
  Time: 45.2s

Tree:
  [tree visualization here]
============================================================
```

The exact numbers will differ. What matters:
- Turn 1 generates 4 candidates
- Failed ones go to Turn 2 with error feedback
- MARS credit assignment runs
- A best solution is selected

### Step 4.3: If demo takes too long

If each generation takes more than 60 seconds, the machine is too slow for 7B.
Change `config.py`:

```python
MODEL_NAME = "qwen2.5-coder:1.5b"    # smaller, faster model
NUM_GENERATIONS = 2                    # fewer candidates (faster)
```

Then pull the smaller model and re-run:
```bash
ollama pull qwen2.5-coder:1.5b
python main.py --mode demo
```

**Phase 4 is done.** Screenshot this output. This is your proof-of-concept.

---

## Phase 5: Baseline Evaluation (Single-Turn, No Feedback)

This measures how well the model does WITHOUT MURPHY (just generate once, no feedback).

### Step 5.1: Start small (10 problems)

```bash
python main.py --mode baseline --problems 10
```

This runs 10 HumanEval problems with single-turn generation. Each problem generates G=4 solutions and picks the best. No Turn 2, no feedback.

**Expected time:** 10-30 minutes depending on model speed.

### Step 5.2: Note down the result

You will see output like:
```
Result: 6/10 solved = 60.00% pass@1
```

Write this number down. This is your **baseline**.

### Step 5.3: Scale up when ready

Once you're confident it works:

```bash
python main.py --mode baseline --problems 164
```

This runs ALL 164 HumanEval problems. **Expected time: 2-5 hours.**

**Phase 5 is done.** You now have a baseline score to compare MURPHY against.

---

## Phase 6: MURPHY Evaluation (Multi-Turn With Feedback)

This is the main event — MURPHY with feedback + MARS credit assignment.

### Step 6.1: Start small (10 problems, MARS)

```bash
python main.py --mode murphy --problems 10 --strategy mars
```

This runs MURPHY with:
- G=4 generations per turn
- S=2 turns (generate → feedback → refine)
- MARS credit assignment
- InterP pruning (budget=3)

**Expected time:** 30-90 minutes for 10 problems (more model calls due to Turn 2).

### Step 6.2: Compare with baseline

You will see output like:
```
Result: 8/10 solved = 80.00% pass@1
```

Compare this with your Phase 5 baseline:
- Baseline: 60% (example)
- MURPHY: 80% (example)
- **Improvement: +20 percentage points**

This improvement demonstrates that feeding errors back to the model helps it fix its code.

### Step 6.3: Run with MERS too

```bash
python main.py --mode murphy --problems 10 --strategy mers
```

Note down this number. You now have three scores:
- Baseline (single-turn)
- MURPHY + MARS
- MURPHY + MERS

### Step 6.4: Scale up when ready

```bash
python main.py --mode murphy --problems 164 --strategy mars
python main.py --mode murphy --problems 164 --strategy mers
```

**Expected time: 5-15 hours total** (run overnight if needed).

**Phase 6 is done.** You now have MURPHY results.

---

## Phase 7: Full Experiment (Baseline vs MARS vs MERS)

This runs everything automatically with multiple runs for statistical significance.

### Step 7.1: Quick version (10 problems, 3 runs)

```bash
python main.py --mode experiment --problems 10 --runs 3
```

This automatically runs:
1. Baseline × 3 runs
2. MURPHY + MARS × 3 runs
3. MURPHY + MERS × 3 runs

And prints a results table with mean ± std.

**Expected time:** 3-6 hours for 10 problems × 3 runs.

### Step 7.2: Full version (all problems)

```bash
python main.py --mode experiment --problems 164 --runs 3
```

**Expected time: 24-48 hours.** Run this overnight or over a weekend.

### Step 7.3: Find your results

Results are saved automatically to:
```
results/results_YYYYMMDD_HHMMSS.csv
```

The CSV contains:
```
Method, Mean_Pass@1, Std_Pass@1, Run_Scores
baseline, 58.54, 1.23, [57.32, 59.76, 58.54]
murphy_mars, 66.46, 0.89, [65.85, 67.07, 66.46]
murphy_mers, 64.02, 1.45, [63.41, 65.24, 63.41]
```

**Phase 7 is done.** You now have publication-quality results.

---

## Phase 8: Ablation Studies

These are extra experiments that show WHY each component of MURPHY matters.

### Study 1: MARS vs MERS (already done in Phase 7)

Your experiment results already have both. Compare them:
- MARS emphasizes peak performance (max child reward)
- MERS emphasizes consistency (mean child reward)
- MARS should generally perform better (matches the paper)

### Study 2: Effect of Pruning

Run MURPHY with different pruning budgets:

```bash
# No pruning (keep all failed branches — slow but complete)
python -c "
import config
config.PRUNING_BUDGET = 100
from evaluator import load_humaneval, evaluate_murphy
problems = load_humaneval(limit=10)
evaluate_murphy(problems, strategy='mars')
"

# Tight pruning (keep only 1 branch — fast but might miss good solutions)
python -c "
import config
config.PRUNING_BUDGET = 1
from evaluator import load_humaneval, evaluate_murphy
problems = load_humaneval(limit=10)
evaluate_murphy(problems, strategy='mars')
"
```

Compare: budget=100 (no pruning) vs budget=3 (default) vs budget=1 (aggressive).

### Study 3: Effect of Number of Generations (G)

```bash
python main.py --mode murphy --problems 10 --generations 2
python main.py --mode murphy --problems 10 --generations 4
python main.py --mode murphy --problems 10 --generations 8
```

More generations = more chances to find a working solution, but takes longer.

### Study 4: Single-Turn vs Multi-Turn (the core comparison)

This is your most important result:
- Single-turn (S=1): `python main.py --mode baseline --problems 10`
- Multi-turn (S=2): `python main.py --mode murphy --problems 10`

The gap between these two numbers proves that feedback-driven self-correction works.

**Phase 8 is done.** You now have ablation results for your report.

---

## Phase 9: Results Collection and Report

### Step 9.1: Collect all CSV files

```bash
ls results/
```

You should have CSV files from each experiment run.

### Step 9.2: Build your results table

Your main results table should look like this (fill in your numbers):

| Method             | HumanEval pass@1 (mean ± std) |
|--------------------|-------------------------------|
| Baseline (Iter-1)  | XX.XX ± X.XX%                 |
| MURPHY MARS (Iter-2)| XX.XX ± X.XX%                |
| MURPHY MERS (Iter-2)| XX.XX ± X.XX%                |

Your ablation table:

| Setting                | pass@1   | Total Model Calls |
|------------------------|----------|--------------------|
| G=2, S=2, MARS         | XX.XX%   | ~XXX               |
| G=4, S=2, MARS         | XX.XX%   | ~XXX               |
| G=8, S=2, MARS         | XX.XX%   | ~XXX               |
| G=4, S=2, MARS, b=1    | XX.XX%   | ~XXX               |
| G=4, S=2, MARS, b=3    | XX.XX%   | ~XXX               |
| G=4, S=2, MARS, no prune| XX.XX%  | ~XXX               |

### Step 9.3: What to write in the report

Your report should clearly state:

> "We implement MURPHY's inference-time components — multi-turn rollout tree,
> MARS/MERS credit assignment, and InterP pruning — as an agent system using
> Qwen2.5-Coder served through Ollama. We do NOT perform GRPO training
> (which requires 8× H100 GPUs). Our system demonstrates that MURPHY's
> architectural innovations provide measurable benefits even at inference time."

---

## Config Reference

All settings are in `config.py`. Change these before running experiments:

| Setting           | Default              | What It Controls                              |
|-------------------|----------------------|-----------------------------------------------|
| `MODEL_NAME`      | `qwen2.5-coder:7b`  | Which Ollama model to use                     |
| `TEMPERATURE`     | `0.6`                | Randomness (0=same output, 1=very random)     |
| `NUM_GENERATIONS` | `4`                  | G: how many code solutions per turn           |
| `NUM_TURNS`       | `2`                  | S: how many rounds of feedback                |
| `PRUNING_BUDGET`  | `3`                  | b: max failed branches to keep                |
| `MERS_GAMMA`      | `0.9`                | Discount factor for MERS                      |
| `CODE_TIMEOUT`    | `10`                 | Max seconds for code execution                |
| `NUM_PROBLEMS`    | `10`                 | Default number of HumanEval problems          |
| `NUM_RUNS`        | `3`                  | How many times to repeat experiment           |
| `USE_OPENROUTER`  | `False`              | Set True to use cloud API instead of Ollama   |

---

## Troubleshooting

### "Cannot connect to Ollama"
Ollama server is not running. Open another terminal and run:
```bash
ollama serve
```

### "model not found"
Model not downloaded. Run:
```bash
ollama pull qwen2.5-coder:7b
```

### "ModuleNotFoundError: No module named 'datasets'"
Packages not installed. Make sure venv is activated, then:
```bash
pip install -r requirements.txt
```

### Model is very slow (>60 seconds per generation)
Your machine doesn't have enough RAM for the 7B model. Switch to smaller:
```bash
ollama pull qwen2.5-coder:1.5b
```
Change `config.py`: `MODEL_NAME = "qwen2.5-coder:1.5b"`

### "Killed" or system freezes
Model is too large for your RAM. Use `qwen2.5-coder:1.5b` or reduce `NUM_GENERATIONS` to 2.

### Virtual environment not activating
Make sure you run the correct command for your OS:
- Linux/Mac: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

### Tests pass but generated code is bad
This is expected with smaller models. The POINT of the project is to show that
multi-turn (with feedback) is BETTER than single-turn, even if absolute numbers are low.

---

## Team Responsibilities

| Member      | File               | What They Own                                      |
|-------------|--------------------|----------------------------------------------------|
| Chaitanya   | evaluator.py, main.py | Dataset loading, experiment runner, results, report |
| N210770     | model_client.py    | Ollama connection, OpenRouter fallback, code extraction |
| N211004     | code_executor.py   | Safe execution, timeout, error parsing, feedback formatting |
| N210438     | rollout_tree.py    | Tree structure, MARS, MERS, IntraP, InterP pruning |
| N210109     | murphy_engine.py   | Multi-turn loop, prompt construction, engine orchestration |

---

## Quick Command Reference

```bash
# Test without model (works anywhere)
python main.py --mode tree-test

# Demo (one problem, verbose)
python main.py --mode demo

# Baseline (single-turn)
python main.py --mode baseline --problems 10

# MURPHY with MARS
python main.py --mode murphy --problems 10 --strategy mars

# MURPHY with MERS
python main.py --mode murphy --problems 10 --strategy mers

# Full experiment (baseline + MARS + MERS, 3 runs each)
python main.py --mode experiment --problems 10 --runs 3

# Override number of generations
python main.py --mode murphy --problems 10 --generations 8
```

---

## References

- MURPHY Paper: [arxiv.org/abs/2511.07833](https://arxiv.org/abs/2511.07833)
- HumanEval Benchmark: [github.com/openai/human-eval](https://github.com/openai/human-eval)
- Ollama: [ollama.com](https://ollama.com)
- Qwen2.5-Coder: [ollama.com/library/qwen2.5-coder](https://ollama.com/library/qwen2.5-coder)
