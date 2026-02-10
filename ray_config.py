"""
Ray-specific configuration for distributed MURPHY execution.
This file contains settings for parallel processing and resource management.
"""

# ============================================================
# RAY CLUSTER SETTINGS
# ============================================================

# Set to True to connect to an existing Ray cluster
# Set to False to run Ray locally on your machine
USE_RAY_CLUSTER = False

# Ray cluster address (only used if USE_RAY_CLUSTER = True)
# Example: "ray://123.456.789.0:10001"
RAY_CLUSTER_ADDRESS = None

# ============================================================
# RESOURCE ALLOCATION
# ============================================================

# Number of CPUs to allocate per problem evaluation task
# Recommended: 1-2 CPUs per task
# Higher values = fewer parallel tasks but more resources per task
CPUS_PER_TASK = 1

# Maximum number of parallel tasks to run simultaneously
# Recommended: Set to number of CPU cores - 2 (leave some for system)
# Example: On 16-core machine, set to 14
# Set to None for unlimited (Ray will auto-manage)
MAX_PARALLEL_TASKS = None

# Memory limit per task (in GB)
# Set to None for no limit
# Recommended: 2-4 GB per task for 7B models
MEMORY_PER_TASK_GB = None

# ============================================================
# OLLAMA CONNECTION SETTINGS
# ============================================================

# Ollama server URL
# Use "http://localhost:11434" if Ollama runs on same machine
# Use "http://<server-ip>:11434" if Ollama runs on different machine
OLLAMA_URL = "http://localhost:11434"

# Maximum concurrent Ollama requests
# Too many concurrent requests can overwhelm the Ollama server
# Recommended: 4-8 for single Ollama instance
MAX_CONCURRENT_OLLAMA_REQUESTS = 6

# Timeout for Ollama requests (seconds)
OLLAMA_REQUEST_TIMEOUT = 120

# ============================================================
# RAY RUNTIME SETTINGS
# ============================================================

# Enable Ray dashboard (useful for monitoring)
# Dashboard runs on http://localhost:8265
ENABLE_RAY_DASHBOARD = True

# Ray temporary directory (for logs and data)
# Set to None to use default Ray temp directory
RAY_TEMP_DIR = None

# Logging level for Ray
# Options: "DEBUG", "INFO", "WARNING", "ERROR"
RAY_LOG_LEVEL = "INFO"

# ============================================================
# PERFORMANCE TUNING
# ============================================================

# Batch size for problem distribution
# Problems are sent to workers in batches
# Larger batches = less overhead but less dynamic load balancing
# Recommended: 5-10 for good balance
PROBLEM_BATCH_SIZE = 5

# Enable object store memory management
# Helps prevent out-of-memory errors with large datasets
ENABLE_OBJECT_SPILLING = True

# ============================================================
# FAULT TOLERANCE
# ============================================================

# Number of retries for failed tasks
# If a task fails (e.g., timeout, crash), Ray will retry it
MAX_TASK_RETRIES = 2

# Enable task reconstruction on worker failure
ENABLE_TASK_RECONSTRUCTION = True

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_ray_init_kwargs():
    """
    Returns dictionary of kwargs for ray.init()
    
    Usage:
        import ray
        from ray_config import get_ray_init_kwargs
        ray.init(**get_ray_init_kwargs())
    """
    kwargs = {
        "ignore_reinit_error": True,
        "logging_level": RAY_LOG_LEVEL,
        "include_dashboard": ENABLE_RAY_DASHBOARD,
    }
    
    if USE_RAY_CLUSTER and RAY_CLUSTER_ADDRESS:
        kwargs["address"] = RAY_CLUSTER_ADDRESS
    
    if RAY_TEMP_DIR:
        kwargs["_temp_dir"] = RAY_TEMP_DIR
    
    # Set object store memory (optional)
    if ENABLE_OBJECT_SPILLING:
        kwargs["object_store_memory"] = None  # Use default with spilling
    
    return kwargs


def get_task_options():
    """
    Returns dictionary of options for @ray.remote decorator
    
    Usage:
        @ray.remote(**get_task_options())
        def my_task():
            pass
    """
    options = {
        "max_retries": MAX_TASK_RETRIES,
    }
    
    if CPUS_PER_TASK:
        options["num_cpus"] = CPUS_PER_TASK
    
    if MEMORY_PER_TASK_GB:
        options["memory"] = MEMORY_PER_TASK_GB * 1024 * 1024 * 1024  # Convert to bytes
    
    return options


# ============================================================
# DEPLOYMENT PROFILES
# ============================================================

class DeploymentProfile:
    """Pre-configured settings for different deployment scenarios"""
    
    @staticmethod
    def laptop():
        """Settings for running on a laptop (4-8 cores)"""
        global MAX_PARALLEL_TASKS, MAX_CONCURRENT_OLLAMA_REQUESTS, CPUS_PER_TASK
        MAX_PARALLEL_TASKS = 4
        MAX_CONCURRENT_OLLAMA_REQUESTS = 3
        CPUS_PER_TASK = 1
        print("📱 Configured for LAPTOP (4 parallel tasks)")
    
    @staticmethod
    def workstation():
        """Settings for running on a workstation (16-32 cores)"""
        global MAX_PARALLEL_TASKS, MAX_CONCURRENT_OLLAMA_REQUESTS, CPUS_PER_TASK
        MAX_PARALLEL_TASKS = 12
        MAX_CONCURRENT_OLLAMA_REQUESTS = 6
        CPUS_PER_TASK = 1
        print("🖥️  Configured for WORKSTATION (12 parallel tasks)")
    
    @staticmethod
    def server():
        """Settings for running on a server (64+ cores)"""
        global MAX_PARALLEL_TASKS, MAX_CONCURRENT_OLLAMA_REQUESTS, CPUS_PER_TASK
        MAX_PARALLEL_TASKS = 48
        MAX_CONCURRENT_OLLAMA_REQUESTS = 12
        CPUS_PER_TASK = 1
        print("🖧  Configured for SERVER (48 parallel tasks)")
    
    @staticmethod
    def cluster():
        """Settings for running on a Ray cluster"""
        global USE_RAY_CLUSTER, MAX_PARALLEL_TASKS, MAX_CONCURRENT_OLLAMA_REQUESTS
        USE_RAY_CLUSTER = True
        MAX_PARALLEL_TASKS = None  # Let Ray manage
        MAX_CONCURRENT_OLLAMA_REQUESTS = 20
        print("☁️  Configured for CLUSTER (unlimited parallel tasks)")


# ============================================================
# QUICK SETUP
# ============================================================

def quick_setup(profile="workstation"):
    """
    Quickly configure Ray for your hardware
    
    Usage:
        from ray_config import quick_setup
        quick_setup("laptop")     # For laptops
        quick_setup("workstation") # For lab computers
        quick_setup("server")     # For servers
        quick_setup("cluster")    # For Ray clusters
    """
    if profile == "laptop":
        DeploymentProfile.laptop()
    elif profile == "workstation":
        DeploymentProfile.workstation()
    elif profile == "server":
        DeploymentProfile.server()
    elif profile == "cluster":
        DeploymentProfile.cluster()
    else:
        print(f"❌ Unknown profile: {profile}")
        print("   Valid options: 'laptop', 'workstation', 'server', 'cluster'")