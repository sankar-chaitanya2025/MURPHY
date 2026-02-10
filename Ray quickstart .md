# MURPHY Ray Quick Reference

## 🚀 One-Page Cheat Sheet

### Installation
```bash
pip install ray[default]
```

### Basic Commands

```bash
# Demo (1 problem, test Ray works)
python ray_main.py --mode demo --profile workstation

# Baseline (10 problems, single-turn)
python ray_main.py --mode baseline --problems 10 --profile workstation

# MURPHY (10 problems, multi-turn with MARS)
python ray_main.py --mode murphy --problems 10 --strategy mars --profile workstation

# MURPHY (10 problems, multi-turn with MERS)
python ray_main.py --mode murphy --problems 10 --strategy mers --profile workstation

# Side-by-side comparison
python ray_main.py --mode compare --problems 10 --strategy mars --profile workstation

# Full experiment (164 problems, 3 runs, all methods)
python ray_main.py --mode experiment --problems 164 --runs 3 --profile workstation
```

### Profiles (Hardware Optimization)

```bash
--profile laptop       # 4 parallel tasks (4-8 core machines)
--profile workstation  # 12 parallel tasks (16 core lab computers) ← RECOMMENDED
--profile server       # 48 parallel tasks (64+ core servers)
--profile cluster      # Unlimited (Ray cluster deployment)
```

### Monitoring

```bash
# Ray Dashboard (open in browser)
http://localhost:8265

# Check Ray status (in terminal)
ray status

# View Ray logs
cat /tmp/ray/session_*/logs/dashboard.log
```

### Troubleshooting Quick Fixes

```bash
# Out of memory? Edit ray_config.py:
MAX_PARALLEL_TASKS = 6  # Reduce from 12
MAX_CONCURRENT_OLLAMA_REQUESTS = 3  # Reduce from 6

# Ray won't start?
ray stop  # Kill old instances
python ray_main.py --mode demo

# Ollama errors?
# Check Ollama is running: ollama serve
# Reduce MAX_CONCURRENT_OLLAMA_REQUESTS in ray_config.py
```

### Expected Runtimes (16-core workstation)

| Task                           | Sequential | Ray Parallel | Speedup |
|--------------------------------|------------|--------------|---------|
| 10 problems (baseline)         | 30-60 min  | 5-10 min     | 6x      |
| 10 problems (MURPHY)           | 60-120 min | 10-20 min    | 6x      |
| 164 problems (baseline)        | 5-8 hours  | 1-2 hours    | 4-5x    |
| 164 problems (MURPHY)          | 10-15 hours| 2-4 hours    | 4-5x    |
| Full experiment (3 runs each)  | 48+ hours  | 10-15 hours  | 3-4x    |

### File Structure

```
murphy-project/
├── Original files (don't modify):
│   ├── config.py
│   ├── model_client.py
│   ├── code_executor.py
│   ├── rollout_tree.py
│   ├── murphy_engine.py
│   ├── evaluator.py
│   └── main.py
│
└── Ray files (new):
    ├── ray_config.py          ← Configure parallelism here
    ├── ray_evaluator.py       ← Parallel evaluation logic
    ├── ray_main.py            ← Run this instead of main.py
    └── RAY_DEPLOYMENT_GUIDE.md ← Full documentation
```

### Configuration (ray_config.py)

```python
# Edit these based on your hardware:

# For 16-core lab computer (RECOMMENDED):
MAX_PARALLEL_TASKS = 12              # CPUs - 4
MAX_CONCURRENT_OLLAMA_REQUESTS = 6   # Half of parallel tasks
CPUS_PER_TASK = 1

# For 8-core laptop:
MAX_PARALLEL_TASKS = 4
MAX_CONCURRENT_OLLAMA_REQUESTS = 2
CPUS_PER_TASK = 1

# For 64-core server:
MAX_PARALLEL_TASKS = 48
MAX_CONCURRENT_OLLAMA_REQUESTS = 12
CPUS_PER_TASK = 1
```

### Results Files

All results saved to `results/` directory:

```
results/
├── ray_baseline_20250210_143022.csv      # Baseline run
├── ray_murphy_mars_20250210_151533.csv   # MURPHY MARS run
├── ray_murphy_mers_20250210_160044.csv   # MURPHY MERS run
└── ray_results_20250210_183015.csv       # Full experiment summary
```

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot connect to Ray` | Ray not started | `ray stop && python ray_main.py --mode demo` |
| `Out of memory` | Too many parallel tasks | Reduce `MAX_PARALLEL_TASKS` in ray_config.py |
| `Connection refused (Ollama)` | Ollama not running | Run `ollama serve` in separate terminal |
| `ModuleNotFoundError: ray` | Ray not installed | `pip install ray[default]` |
| `Task failed` | Model timeout/crash | Reduce `MAX_CONCURRENT_OLLAMA_REQUESTS` |

### Performance Tips

1. **Always run Ollama in a separate terminal** before starting Ray experiments
2. **Use `--profile workstation`** for 16-core lab computers
3. **Monitor Ray dashboard** at http://localhost:8265 to see CPU usage
4. **Start small** (10 problems) before scaling to 164
5. **Run overnight** for full 164-problem experiments

### Comparison: Original vs Ray

```python
# ORIGINAL main.py (Sequential)
python main.py --mode murphy --problems 164
# Time: 10-15 hours
# Uses: 1 CPU core

# RAY ray_main.py (Parallel)
python ray_main.py --mode murphy --problems 164 --profile workstation
# Time: 2-4 hours
# Uses: 12 CPU cores simultaneously
```

### Emergency Shutdown

```bash
# If Ray hangs or crashes:
Ctrl+C  # Interrupt the process
ray stop --force  # Force kill all Ray processes
pkill -9 ray  # Nuclear option (kills everything)
```

### Workflow for Full Experiment

```bash
# 1. Install Ray (one time)
pip install ray[default]

# 2. Start Ollama (in separate terminal, keep running)
ollama serve

# 3. Test with demo (verify everything works)
python ray_main.py --mode demo --profile workstation

# 4. Run small test (10 problems)
python ray_main.py --mode compare --problems 10 --profile workstation

# 5. Run full experiment (overnight/weekend)
python ray_main.py --mode experiment --problems 164 --runs 3 --profile workstation

# 6. Results automatically saved to results/ directory
ls results/
```

### Remember

- ✅ Ray = **4-6x faster experiments**
- ✅ Results are **identical** to sequential version
- ✅ Uses **all CPU cores** instead of just one
- ✅ **Same code** (murphy_engine.py unchanged)
- ✅ **Easy setup** (just 3 new files)

---

**Questions?** Check RAY_DEPLOYMENT_GUIDE.md for detailed explanations.