# MURPHY Ray Deployment Guide

Complete guide to deploying your MURPHY code generation agent on Ray for parallel processing.

---

## 🎯 What Ray Will Do For Your Project

**Before Ray (Sequential):**
- 164 problems × 3 runs = **24-48 hours**
- One problem at a time
- Single CPU core doing all the work

**After Ray (Parallel):**
- 164 problems × 3 runs = **3-6 hours** (on 16-core workstation)
- 12+ problems running simultaneously
- All CPU cores utilized efficiently

**Speed improvement: 4-8x faster** 🚀

---

## 📋 Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Understanding Ray Basics](#understanding-ray-basics)
3. [Installation](#installation)
4. [Configuration for Your Hardware](#configuration)
5. [Running Your First Parallel Experiment](#first-run)
6. [Full Deployment Workflow](#full-deployment)
7. [Monitoring and Debugging](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tuning](#performance-tuning)

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Ray

```bash
cd ~/Desktop/murphy-project  # or wherever your project is
source venv/bin/activate      # activate your virtual environment
pip install ray[default]
```

### Step 2: Copy the Ray files to your project

Copy these 3 new files into your MURPHY project folder:
- `ray_config.py`
- `ray_evaluator.py`
- `ray_main.py`

Your project structure should now look like:

```
murphy-project/
├── config.py               # Original files
├── model_client.py
├── code_executor.py
├── rollout_tree.py
├── murphy_engine.py
├── evaluator.py
├── main.py
├── ray_config.py          # NEW: Ray configuration
├── ray_evaluator.py       # NEW: Parallel evaluator
└── ray_main.py            # NEW: Ray entry point
```

### Step 3: Make sure Ollama is running

```bash
# In a separate terminal
ollama serve
```

### Step 4: Run your first parallel experiment

```bash
python ray_main.py --mode demo --profile workstation
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════╗
║   MURPHY Multi-Turn Code Generation Agent               ║
║   🚀 RAY-ENABLED PARALLEL VERSION 🚀                    ║
╚══════════════════════════════════════════════════════════╝

🖥️  Configured for WORKSTATION (12 parallel tasks)

🔧 Initializing Ray...
✅ Ray initialized successfully!
   Available CPUs: 16
   Dashboard: http://localhost:8265

🎯 DEMO MODE: Running single problem with detailed output
...
```

**If you see this, Ray is working! 🎉**

---

## 📚 Understanding Ray Basics

### What is Ray?

Ray is a **distributed computing framework** that lets you run Python code in parallel across multiple CPU cores (or even multiple computers).

### Key Ray Concepts for MURPHY

**1. `@ray.remote` Decorator**

Turns a normal Python function into a "task" that can run in parallel:

```python
# Normal function (runs sequentially)
def solve_problem(problem):
    return murphy_solve(problem)

# Ray remote function (can run in parallel)
@ray.remote
def solve_problem(problem):
    return murphy_solve(problem)
```

**2. `.remote()` Call**

Starts a task in the background (doesn't block):

```python
# Sequential (waits for each to finish)
result1 = solve_problem(problem1)
result2 = solve_problem(problem2)

# Parallel (starts both immediately)
future1 = solve_problem.remote(problem1)
future2 = solve_problem.remote(problem2)
```

**3. `ray.get()` - Get Results**

Waits for a task to finish and gets its result:

```python
# Start 10 tasks in parallel
futures = [solve_problem.remote(p) for p in problems]

# Wait for all to finish
results = [ray.get(f) for f in futures]
```

**4. Ray automatically handles:**
- Scheduling tasks to available CPU cores
- Moving data between processes
- Retrying failed tasks
- Memory management

### How Ray Helps MURPHY

Your original code processes problems **one at a time**:

```python
# Original evaluator.py (sequential)
for problem in problems:
    result = murphy_solve(problem)  # Takes 2-5 minutes per problem
    results.append(result)
# Total: 164 problems × 3 min = 8+ hours
```

With Ray, problems run **in parallel**:

```python
# ray_evaluator.py (parallel)
futures = [murphy_solve_remote.remote(problem) for problem in problems]
results = ray.get(futures)  # All run simultaneously
# Total: 164 problems ÷ 12 cores = ~40 minutes
```

---

## 💻 Installation

### Prerequisites

- Python 3.10 or 3.11 (you already have this)
- Your existing MURPHY project (already set up)
- Ollama running (already set up)

### Install Ray

```bash
# Make sure you're in your project directory
cd ~/Desktop/murphy-project

# Activate virtual environment
source venv/bin/activate

# Install Ray
pip install ray[default]
```

The `[default]` includes the Ray dashboard for monitoring.

**Installation takes 2-3 minutes** and downloads ~200 MB.

### Verify Installation

```bash
python -c "import ray; print(f'Ray version: {ray.__version__}')"
```

**Expected output:**
```
Ray version: 2.9.0 (or similar)
```

---

## ⚙️ Configuration for Your Hardware

Ray needs to know how many tasks to run in parallel. This depends on your computer's CPU cores.

### Check Your CPU Cores

**Linux:**
```bash
nproc
```

**Mac:**
```bash
sysctl -n hw.ncpu
```

**Windows:**
```bash
echo %NUMBER_OF_PROCESSORS%
```

### Choose Your Profile

Edit `ray_config.py` or use command-line flag:

| Your Computer       | CPU Cores | Profile         | Parallel Tasks |
|---------------------|-----------|-----------------|----------------|
| Laptop              | 4-8       | `laptop`        | 4              |
| Lab Workstation     | 12-16     | `workstation`   | 12             |
| Server              | 32-64+    | `server`        | 48             |
| Ray Cluster         | 100+      | `cluster`       | Unlimited      |

### Option 1: Use Command-Line Profile

```bash
# For lab computer with 16 cores
python ray_main.py --mode murphy --problems 10 --profile workstation
```

### Option 2: Edit ray_config.py

Open `ray_config.py` and change these lines:

```python
# For lab computer with 16 cores
MAX_PARALLEL_TASKS = 12  # Leave 4 cores for system + Ollama
MAX_CONCURRENT_OLLAMA_REQUESTS = 6  # Don't overwhelm Ollama
```

**Rule of thumb:**
- `MAX_PARALLEL_TASKS` = Total CPU cores - 4
- `MAX_CONCURRENT_OLLAMA_REQUESTS` = MAX_PARALLEL_TASKS ÷ 2

---

## 🏃 Running Your First Parallel Experiment

### Test 1: Demo Mode (1 problem)

Verify everything works with a single problem:

```bash
python ray_main.py --mode demo --profile workstation
```

**What to look for:**
- ✅ Ray initializes without errors
- ✅ Problem solves (might pass or fail, doesn't matter)
- ✅ Time is reasonable (10-60 seconds)

### Test 2: Small Baseline (10 problems)

Run baseline evaluation on 10 problems:

```bash
python ray_main.py --mode baseline --problems 10 --profile workstation
```

**Expected time:** 5-15 minutes (vs 30-60 minutes sequentially)

**What to look for:**
```
🚀 RAY BASELINE Evaluation: 10 problems
   Parallelism: 12 tasks

📊 Progress:
   10/10 done | 6 solved | 0.65 problems/sec | 15.4s elapsed

✅ BASELINE Results:
   Pass@1: 60.00% (6/10)
   Time: 15.4s
   Speed: 0.65 problems/sec
```

### Test 3: Small MURPHY (10 problems)

Run MURPHY with feedback:

```bash
python ray_main.py --mode murphy --problems 10 --strategy mars --profile workstation
```

**Expected time:** 10-30 minutes

### Test 4: Quick Comparison

See the improvement of MURPHY over baseline:

```bash
python ray_main.py --mode compare --problems 10 --strategy mars --profile workstation
```

**Expected output:**
```
📊 COMPARISON RESULTS
Method               Pass@1       Solved     Time
------------------------------------------------------------
Baseline              60.00%       6/10      15.4s
MURPHY (MARS)         80.00%       8/10      25.7s

Improvement          +20.00%
```

---

## 🎯 Full Deployment Workflow

Once you've verified everything works on 10 problems, scale up to full experiments.

### Phase 1: Full Baseline (164 problems)

```bash
python ray_main.py --mode baseline --problems 164 --profile workstation
```

**Expected time:** 1-2 hours (vs 5-8 hours sequential)

### Phase 2: Full MURPHY MARS (164 problems)

```bash
python ray_main.py --mode murphy --problems 164 --strategy mars --profile workstation
```

**Expected time:** 2-4 hours (vs 10-15 hours sequential)

### Phase 3: Full MURPHY MERS (164 problems)

```bash
python ray_main.py --mode murphy --problems 164 --strategy mers --profile workstation
```

**Expected time:** 2-4 hours

### Phase 4: Complete Experiment (3 runs each)

Run everything automatically:

```bash
python ray_main.py --mode experiment --problems 164 --runs 3 --profile workstation
```

**Expected time:** 10-15 hours (vs 48+ hours sequential)

**Recommendation:** Run this overnight or over a weekend.

**What it does:**
1. Baseline × 3 runs
2. MURPHY MARS × 3 runs
3. MURPHY MERS × 3 runs
4. Calculates mean ± std for each
5. Saves results to CSV

---

## 📊 Monitoring and Debugging

### Ray Dashboard

Ray provides a web dashboard to monitor your tasks in real-time.

**Access it:** Open browser to `http://localhost:8265`

**What you can see:**
- Number of running tasks
- CPU/memory usage per core
- Task timeline (which tasks are running when)
- Failed tasks with error messages
- Resource utilization graphs

### Command-Line Progress

Ray shows real-time progress in your terminal:

```
📊 Progress:
   10/164 done | 7 solved | 0.58 problems/sec | 17.2s elapsed
   20/164 done | 14 solved | 0.61 problems/sec | 32.8s elapsed
   ...
```

### Check Ray Status

In a separate terminal:

```bash
ray status
```

Shows:
- Number of CPUs available
- Number of running tasks
- Memory usage

---

## 🔧 Troubleshooting

### Problem: "Cannot connect to Ray"

**Cause:** Ray not initialized

**Solution:**
```bash
# Ray should auto-initialize, but if not:
ray stop  # Stop any old Ray instances
python ray_main.py --mode demo --profile workstation
```

### Problem: "Out of memory" or system freezes

**Cause:** Too many parallel tasks for your RAM

**Solution:** Reduce parallelism in `ray_config.py`:

```python
MAX_PARALLEL_TASKS = 6  # Reduce from 12
MAX_CONCURRENT_OLLAMA_REQUESTS = 3  # Reduce from 6
```

Or use command line:

```bash
# Edit ray_config.py before running
python -c "
import ray_config
ray_config.MAX_PARALLEL_TASKS = 6
ray_config.MAX_CONCURRENT_OLLAMA_REQUESTS = 3
" && python ray_main.py --mode murphy --problems 10
```

### Problem: Ollama connection errors

**Cause:** Too many concurrent requests to Ollama

**Solution:** Reduce `MAX_CONCURRENT_OLLAMA_REQUESTS` in `ray_config.py`:

```python
MAX_CONCURRENT_OLLAMA_REQUESTS = 3  # Lower this if you see errors
```

### Problem: Tasks are slow

**Cause:** Model is too large for your machine

**Solution:** Switch to smaller model in `config.py`:

```python
MODEL_NAME = "qwen2.5-coder:1.5b"  # Instead of 7b
```

Then pull the smaller model:

```bash
ollama pull qwen2.5-coder:1.5b
```

### Problem: "ModuleNotFoundError: No module named 'ray'"

**Cause:** Ray not installed or wrong virtual environment

**Solution:**
```bash
# Make sure venv is activated
source venv/bin/activate

# Install Ray
pip install ray[default]
```

---

## ⚡ Performance Tuning

### Optimize for Speed

**Goal:** Process problems as fast as possible

```python
# In ray_config.py
MAX_PARALLEL_TASKS = 20  # Maximum parallelism
MAX_CONCURRENT_OLLAMA_REQUESTS = 10  # More concurrent requests
CPUS_PER_TASK = 1  # Minimal resources per task
```

**Best for:** Powerful servers with 32+ CPU cores

### Optimize for Stability

**Goal:** Avoid crashes and out-of-memory errors

```python
# In ray_config.py
MAX_PARALLEL_TASKS = 4  # Conservative parallelism
MAX_CONCURRENT_OLLAMA_REQUESTS = 2  # Fewer Ollama requests
CPUS_PER_TASK = 2  # More resources per task
MEMORY_PER_TASK_GB = 4  # Reserve memory
```

**Best for:** Laptops or machines with limited RAM

### Optimize for Balance (Recommended)

**Goal:** Good speed without overwhelming system

```python
# In ray_config.py
MAX_PARALLEL_TASKS = 12  # For 16-core machine
MAX_CONCURRENT_OLLAMA_REQUESTS = 6
CPUS_PER_TASK = 1
```

**Best for:** Lab workstations (12-16 cores)

---

## 📈 Expected Performance Gains

### Sequential (Original Code)

| Task                    | Time      |
|-------------------------|-----------|
| 10 problems baseline    | 30-60 min |
| 10 problems MURPHY      | 60-120 min|
| 164 problems baseline   | 5-8 hours |
| 164 problems MURPHY     | 10-15 hours|
| Full experiment (3 runs)| 48+ hours |

### Parallel (Ray, 16-core workstation)

| Task                    | Time      | Speedup |
|-------------------------|-----------|---------|
| 10 problems baseline    | 5-10 min  | 6x      |
| 10 problems MURPHY      | 10-20 min | 6x      |
| 164 problems baseline   | 1-2 hours | 4-5x    |
| 164 problems MURPHY     | 2-4 hours | 4-5x    |
| Full experiment (3 runs)| 10-15 hours| 3-4x   |

**Why not faster?**
- Ollama is the bottleneck (single model instance)
- Code execution has some overhead
- Some problems are inherently sequential

**Still worth it?** Absolutely! Reducing 48 hours to 15 hours is huge for research.

---

## 🎓 Summary: Original vs Ray

### Original `main.py` (Sequential)

```python
# Processes one problem at a time
for problem in problems:
    result = murphy_solve(problem)
    results.append(result)
```

**Pros:**
- Simple code
- Easy to debug
- Low memory usage

**Cons:**
- Slow (only uses 1 CPU core)
- Wastes 15 CPU cores on a 16-core machine

### Ray `ray_main.py` (Parallel)

```python
# Processes 12 problems simultaneously
futures = [murphy_solve.remote(problem) for problem in problems]
results = ray.get(futures)
```

**Pros:**
- 4-6x faster
- Uses all CPU cores efficiently
- Same accuracy (results identical to sequential)

**Cons:**
- Slightly more complex setup
- Uses more memory
- Requires Ray installation

---

## 🚀 Next Steps

1. **Run demo** to verify Ray works
2. **Run 10-problem comparison** to see the speedup
3. **Scale to full 164 problems** when confident
4. **Run overnight experiments** for publication results

---

## 📞 Getting Help

If you encounter issues:

1. Check Ray dashboard: `http://localhost:8265`
2. Check Ray logs: `cat /tmp/ray/session_*/logs/dashboard.log`
3. Reduce parallelism in `ray_config.py`
4. Ask your lab administrator about hardware specs

---

## 🎉 Conclusion

You now have:
- ✅ Ray installed and configured
- ✅ Parallel evaluator for MURPHY
- ✅ 4-6x speedup on experiments
- ✅ Same results as sequential version

**Your experiments will now run in hours instead of days!** 🚀

Good luck with your MURPHY research! 🧠