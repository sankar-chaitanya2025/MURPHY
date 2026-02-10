"""
config.py — MURPHY Project Configuration
All settings in one place. Change values here, not in other files.
"""

# ─────────────────────────────────────────────
# MODEL SETTINGS
# ─────────────────────────────────────────────
# Which model to use in Ollama
MODEL_NAME = "qwen2.5-coder:7b"

# Ollama runs a local server on this URL
OLLAMA_URL = "http://localhost:11434/api/generate"

# How creative the model should be (0.0 = same every time, 1.0 = very random)
TEMPERATURE = 0.6

# Maximum tokens (words/symbols) the model can generate per response
MAX_TOKENS = 2048

# How long to wait for the model to respond (seconds)
TIMEOUT = 120

# ─────────────────────────────────────────────
# MURPHY SETTINGS
# ─────────────────────────────────────────────
# G = number of code attempts per turn
NUM_GENERATIONS = 4

# S = number of turns (1 = initial, 2+ = refinement rounds)
NUM_TURNS = 2

# b = pruning budget (max failed branches to keep for next turn)
PRUNING_BUDGET = 3

# Discount factor for MERS (Mean Reward Strategy)
MERS_GAMMA = 0.9

# ─────────────────────────────────────────────
# EXECUTION SETTINGS
# ─────────────────────────────────────────────
# Maximum seconds to let generated code run before killing it
CODE_TIMEOUT = 10

# Imports that are NOT allowed in generated code (safety)
BLOCKED_IMPORTS = ["shutil", "pathlib"]

# ─────────────────────────────────────────────
# EVALUATION SETTINGS
# ─────────────────────────────────────────────
# How many HumanEval problems to test (max 164). Use 10 for testing.
NUM_PROBLEMS = 10

# How many times to repeat the experiment (for mean ± std calculation)
NUM_RUNS = 3

# Where to save results
RESULTS_DIR = "results"

# ─────────────────────────────────────────────
# OPENROUTER FALLBACK (if Ollama doesn't work)
# ─────────────────────────────────────────────
USE_OPENROUTER = False
OPENROUTER_API_KEY = "your-key-here"
OPENROUTER_MODEL = "qwen/qwen-2.5-coder-7b-instruct"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
