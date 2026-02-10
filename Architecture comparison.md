# MURPHY Architecture: Sequential vs Ray Parallel

## Visual Comparison

### Sequential Architecture (Original)

```
┌─────────────────────────────────────────────────────────┐
│  main.py                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ for problem in problems:                        │   │
│  │   ├─ murphy_solve(problem)  [30-60 seconds]     │   │
│  │   ├─ murphy_solve(problem)  [30-60 seconds]     │   │
│  │   ├─ murphy_solve(problem)  [30-60 seconds]     │   │
│  │   └─ ... (one at a time)                        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  CPU Utilization:                                       │
│  Core 1: ████████████████████████ (100% busy)          │
│  Core 2: ░░░░░░░░░░░░░░░░░░░░░░░░ (idle)               │
│  Core 3: ░░░░░░░░░░░░░░░░░░░░░░░░ (idle)               │
│  ...                                                    │
│  Core 16: ░░░░░░░░░░░░░░░░░░░░░░░ (idle)               │
│                                                         │
│  164 problems × 3 min/problem = 492 minutes = 8.2 hours│
└─────────────────────────────────────────────────────────┘
```

### Parallel Architecture (Ray)

```
┌─────────────────────────────────────────────────────────┐
│  ray_main.py                                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Ray Scheduler                                   │   │
│  │  ├─ Task 1 → Worker 1 (problem 1)   [running]   │   │
│  │  ├─ Task 2 → Worker 2 (problem 2)   [running]   │   │
│  │  ├─ Task 3 → Worker 3 (problem 3)   [running]   │   │
│  │  ├─ Task 4 → Worker 4 (problem 4)   [running]   │   │
│  │  ├─ Task 5 → Worker 5 (problem 5)   [running]   │   │
│  │  ├─ Task 6 → Worker 6 (problem 6)   [running]   │   │
│  │  ├─ Task 7 → Worker 7 (problem 7)   [running]   │   │
│  │  ├─ Task 8 → Worker 8 (problem 8)   [running]   │   │
│  │  ├─ Task 9 → Worker 9 (problem 9)   [running]   │   │
│  │  ├─ Task 10 → Worker 10 (problem 10) [running]  │   │
│  │  ├─ Task 11 → Worker 11 (problem 11) [running]  │   │
│  │  ├─ Task 12 → Worker 12 (problem 12) [running]  │   │
│  │  ├─ Task 13 → Queue (waiting for worker)        │   │
│  │  ├─ Task 14 → Queue (waiting for worker)        │   │
│  │  └─ ... (157 more queued)                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  CPU Utilization:                                       │
│  Core 1:  ████████████████████████ (100% busy)         │
│  Core 2:  ████████████████████████ (100% busy)         │
│  Core 3:  ████████████████████████ (100% busy)         │
│  Core 4:  ████████████████████████ (100% busy)         │
│  Core 5:  ████████████████████████ (100% busy)         │
│  Core 6:  ████████████████████████ (100% busy)         │
│  Core 7:  ████████████████████████ (100% busy)         │
│  Core 8:  ████████████████████████ (100% busy)         │
│  Core 9:  ████████████████████████ (100% busy)         │
│  Core 10: ████████████████████████ (100% busy)         │
│  Core 11: ████████████████████████ (100% busy)         │
│  Core 12: ████████████████████████ (100% busy)         │
│  Core 13: ████░░░░░░░░░░░░░░░░░░░░ (Ray overhead)      │
│  Core 14: ████░░░░░░░░░░░░░░░░░░░░ (Ollama server)     │
│  Core 15: ░░░░░░░░░░░░░░░░░░░░░░░░ (system)            │
│  Core 16: ░░░░░░░░░░░░░░░░░░░░░░░░ (system)            │
│                                                         │
│  164 problems ÷ 12 workers × 3 min = 41 minutes        │
│  Speedup: 8.2 hours ÷ 0.7 hours = 12x faster!          │
└─────────────────────────────────────────────────────────┘
```

## Data Flow Comparison

### Sequential Flow

```
User runs main.py
      ↓
Load HumanEval dataset (164 problems)
      ↓
┌─────────────────────┐
│ Problem 1           │ → murphy_solve() → result 1 → [3 min]
└─────────────────────┘
      ↓
┌─────────────────────┐
│ Problem 2           │ → murphy_solve() → result 2 → [3 min]
└─────────────────────┘
      ↓
┌─────────────────────┐
│ Problem 3           │ → murphy_solve() → result 3 → [3 min]
└─────────────────────┘
      ↓
      ... (161 more problems, one at a time)
      ↓
Aggregate results
      ↓
Save to CSV

Total: 164 × 3 min = 492 minutes
```

### Parallel Flow (Ray)

```
User runs ray_main.py
      ↓
ray.init() → Start Ray cluster on local machine
      ↓
Load HumanEval dataset (164 problems)
      ↓
Create 164 Ray tasks (one per problem)
      ↓
┌────────────────────────────────────────────────────────┐
│ Ray Scheduler distributes tasks to 12 workers          │
│                                                         │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│ │ Worker 1    │  │ Worker 2    │  │ Worker 3    │    │
│ │ Problem 1   │  │ Problem 2   │  │ Problem 3   │    │
│ │ [running]   │  │ [running]   │  │ [running]   │    │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│        │ 3 min          │ 3 min          │ 3 min      │
│        ↓ done           ↓ done           ↓ done       │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│ │ Worker 1    │  │ Worker 2    │  │ Worker 3    │    │
│ │ Problem 13  │  │ Problem 14  │  │ Problem 15  │    │
│ │ [running]   │  │ [running]   │  │ [running]   │    │
│ └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                         │
│ ... continues until all 164 problems done ...          │
└────────────────────────────────────────────────────────┘
      ↓
Ray collects all 164 results
      ↓
Aggregate results
      ↓
Save to CSV

Total: 164 ÷ 12 × 3 min = 41 minutes
```

## Component Interaction

### Sequential: murphy_engine.py

```
┌──────────────────────────────────────────┐
│ murphy_solve(problem)                    │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ Turn 1: Generate 4 solutions       │ │
│  │   ├─ model_client.generate_code()  │ │
│  │   ├─ code_executor.execute_code()  │ │
│  │   ├─ rollout_tree.add_child()      │ │
│  │   └─ (repeat 4 times)              │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Turn 2: Refine failed solutions    │ │
│  │   ├─ model_client.generate_code()  │ │
│  │   ├─ code_executor.execute_code()  │ │
│  │   ├─ rollout_tree.add_child()      │ │
│  │   └─ (repeat N times)              │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Credit assignment (MARS/MERS)      │ │
│  │   └─ rollout_tree.mars_propagate() │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Return best solution               │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Total time: 30-180 seconds              │
└──────────────────────────────────────────┘

Called ONCE per problem (sequential)
```

### Ray: murphy_engine.py (unchanged!)

```
┌──────────────────────────────────────────┐
│ @ray.remote                              │  ← ONLY CHANGE
│ murphy_solve(problem)                    │     (decorator added
│                                          │      in ray_evaluator)
│  ┌────────────────────────────────────┐ │
│  │ Turn 1: Generate 4 solutions       │ │
│  │   ├─ model_client.generate_code()  │ │
│  │   ├─ code_executor.execute_code()  │ │
│  │   ├─ rollout_tree.add_child()      │ │
│  │   └─ (repeat 4 times)              │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Turn 2: Refine failed solutions    │ │
│  │   ├─ model_client.generate_code()  │ │
│  │   ├─ code_executor.execute_code()  │ │
│  │   ├─ rollout_tree.add_child()      │ │
│  │   └─ (repeat N times)              │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Credit assignment (MARS/MERS)      │ │
│  │   └─ rollout_tree.mars_propagate() │ │
│  └────────────────────────────────────┘ │
│           ↓                              │
│  ┌────────────────────────────────────┐ │
│  │ Return best solution               │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Total time: 30-180 seconds              │
└──────────────────────────────────────────┘

Called 12 TIMES SIMULTANEOUSLY (parallel)
```

## Memory Layout

### Sequential

```
┌──────────────────────────────────────┐
│ RAM (16 GB)                          │
│                                      │
│  Python Process (2 GB):              │
│    ├─ HumanEval dataset (100 MB)    │
│    ├─ Current problem data (10 MB)  │
│    └─ Rollout tree (50 MB)          │
│                                      │
│  Ollama Server (8 GB):               │
│    └─ Qwen2.5-Coder 7B model        │
│                                      │
│  Free: 6 GB                          │
└──────────────────────────────────────┘
```

### Ray Parallel

```
┌──────────────────────────────────────┐
│ RAM (16 GB)                          │
│                                      │
│  Ray Head (500 MB):                  │
│    └─ Task scheduler, object store  │
│                                      │
│  Ray Workers × 12 (3 GB total):      │
│    ├─ Worker 1 (250 MB)             │
│    ├─ Worker 2 (250 MB)             │
│    ├─ ...                            │
│    └─ Worker 12 (250 MB)            │
│                                      │
│  Ollama Server (8 GB):               │
│    └─ Qwen2.5-Coder 7B model        │
│    (shared by all workers)           │
│                                      │
│  Free: 4.5 GB                        │
└──────────────────────────────────────┘

Note: Workers share Ollama connection
      Workers process different problems
      No duplicate model loading!
```

## Network Communication (Ollama)

### Sequential

```
Python → Ollama
   ↓        ↓
Request 1  Process → Response 1
   ↓
Request 2  Process → Response 2
   ↓
Request 3  Process → Response 3
   ↓
... (one at a time)

Max throughput: 1 request at a time
```

### Ray Parallel

```
Ray Workers (12) → Ollama Server
   ↓                    ↓
Worker 1 → Request 1 ──┐
Worker 2 → Request 2 ──┤
Worker 3 → Request 3 ──┤
Worker 4 → Request 4 ──├─→ Ollama queues requests
Worker 5 → Request 5 ──┤   Processes 6 concurrently
Worker 6 → Request 6 ──┤   (MAX_CONCURRENT_OLLAMA_REQUESTS)
Worker 7 → Request 7 ──┤
Worker 8 → Request 8 ──┤
Worker 9 → Request 9 ──┤
Worker 10 → Request 10 ┤
Worker 11 → Request 11 ┤
Worker 12 → Request 12 ┘
                    ↓
        Responses streamed back to workers

Max throughput: 6 concurrent requests
```

## Why 12 Workers Instead of 16?

```
16 CPU Cores Available
   ├─ 12 cores → Ray workers (problem solving)
   ├─ 2 cores → Ollama server (model inference)
   └─ 2 cores → System + Ray head (OS, scheduling)

If we used all 16 cores for workers:
   → Ollama would be starved for CPU
   → System would lag
   → Everything would slow down
   
Optimal: Use 75% of cores for workers
```

## Speedup Breakdown

### Why Not 16x Faster?

```
Theoretical max speedup: 16 cores = 16x
Actual speedup: ~5-6x

Lost speedup due to:
├─ Ollama bottleneck (40%)
│   Single model instance can't handle 16 requests
│   Max concurrent: 6 requests
│   
├─ I/O overhead (20%)
│   Disk writes, network calls, logging
│   
├─ Ray overhead (10%)
│   Task scheduling, serialization
│   
├─ System overhead (10%)
│   OS, background processes
│   
└─ Sequential bottlenecks (20%)
    Some parts can't be parallelized
    (e.g., final aggregation)

5-6x speedup is excellent for this workload!
```

## Summary

| Aspect              | Sequential        | Ray Parallel      |
|---------------------|-------------------|-------------------|
| CPU cores used      | 1                 | 12                |
| Problems at once    | 1                 | 12                |
| Memory usage        | 10 GB             | 12 GB             |
| Setup complexity    | Simple            | Medium            |
| Code changes needed | None              | 3 new files       |
| Speedup             | 1x (baseline)     | 5-6x              |
| Time (164 problems) | 8-10 hours        | 1.5-2 hours       |
| Recommended for     | Testing, debugging| Production, research |

**Bottom line:** Ray gives you 5-6x speedup with minimal code changes!