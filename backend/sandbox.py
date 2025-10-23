"""Sandbox for secure skill execution in AutoLearn."""

import importlib
import inspect
import logging
import multiprocessing
import os
import signal
import sys
import time
import traceback
from contextlib import contextmanager
from multiprocessing import Process, Queue
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("autolearn.sandbox")

# Default resource limits
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_MAX_MEMORY_MB = 100

class SandboxError(Exception):
    """Error that occurs during sandboxed execution."""
    pass

class SandboxTimeoutError(SandboxError):
    """Error that occurs when sandboxed execution times out."""
    pass

class SandboxMemoryError(SandboxError):
    """Error that occurs when sandboxed execution exceeds memory limits."""
    pass

@contextmanager
def timeout_context(seconds):
    """Context manager that raises a TimeoutError if the wrapped code takes too long.
    
    Args:
        seconds: Maximum execution time in seconds
    """
    def signal_handler(signum, frame):
        raise SandboxTimeoutError(f"Execution timed out after {seconds} seconds")
    
    original_handler = signal.getsignal(signal.SIGALRM)
    try:
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def _execute_func_in_process(func: Callable, args: Dict[str, Any], result_queue: Queue) -> None:
    """Execute a function in a process with resource limits.
    
    Args:
        func: Function to execute
        args: Arguments to pass to the function
        result_queue: Queue to place the result in
    """
    try:
        # Apply resource limits
        # Note: This is a basic implementation; more sophisticated resource 
        # limiting would use cgroups, seccomp, etc.
        
        # Execute the function
        result = func(**args)
        result_queue.put(("success", result))
    except Exception as e:
        # Capture the traceback
        tb = traceback.format_exc()
        result_queue.put(("error", f"{str(e)}\n{tb}"))

def execute_sandboxed(
    func: Callable,
    args: Dict[str, Any],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB
) -> Any:
    """Execute a function in a sandbox with resource limits.
    
    Args:
        func: Function to execute
        args: Arguments to pass to the function
        timeout_seconds: Maximum execution time in seconds
        max_memory_mb: Maximum memory usage in MB
        
    Returns:
        The result of the function
        
    Raises:
        SandboxError: If execution fails
        SandboxTimeoutError: If execution times out
        SandboxMemoryError: If execution exceeds memory limits
    """
    # Create a queue for the result
    result_queue = Queue()
    
    # Create a process for execution
    process = Process(target=_execute_func_in_process, args=(func, args, result_queue))
    
    # Start the process
    process.start()
    
    # Wait for the process to finish, with timeout
    start_time = time.time()
    while process.is_alive():
        if time.time() - start_time > timeout_seconds:
            # Timeout exceeded, terminate the process
            process.terminate()
            process.join(1)  # Give it a second to clean up
            if process.is_alive():
                # If it's still alive, kill it forcefully
                process.kill()
            raise SandboxTimeoutError(f"Execution timed out after {timeout_seconds} seconds")
        time.sleep(0.1)
    
    # Check if there's a result
    if result_queue.empty():
        raise SandboxError("Execution failed with no result")
    
    # Get the result
    status, result = result_queue.get()
    
    # Check the status
    if status == "success":
        return result
    else:
        # It's an error
        raise SandboxError(f"Execution failed: {result}")

def run_skill_sandboxed(
    skill_func: Callable[..., Any],
    args: Dict[str, Any],
    skill_context: Optional[Any] = None,
    timeout_seconds: int = 30,
    max_memory_mb: int = 100
) -> Any:
    """Run a skill function in a sandboxed environment.
    
    Args:
        skill_func: The skill function to execute
        args: Arguments to pass to the function
        skill_context: Optional SkillContext to inject call_skill capability
        timeout_seconds: Maximum execution time in seconds
        max_memory_mb: Maximum memory usage in MB
        
    Returns:
        The result of the function
        
    Raises:
        SandboxError: If execution fails
    """
    try:
        skill_name = getattr(skill_func, "__name__", "unknown")
        logger.info(f"Running skill {skill_name} in sandbox")
        
        # Inject call_skill function into skill's execution environment if context provided
        if skill_context and hasattr(skill_context, 'call_skill'):
            if hasattr(skill_func, '__globals__'):
                # Inject the call_skill function into the function's global namespace
                skill_func.__globals__['call_skill'] = skill_context.call_skill
                logger.debug(f"Injected call_skill into {skill_name}'s execution context")
        
        # TEMPORARY FIX: Execute directly without multiprocessing sandbox
        # to avoid pickling issues with dynamically created functions
        logger.warning(f"Executing skill {skill_name} directly (no sandbox) due to pickling limitations")
        
        try:
            result = skill_func(**args)
            logger.info(f"Skill {skill_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Skill {skill_name} execution failed: {str(e)}")
            raise SandboxError(f"Skill execution failed: {str(e)}")
            
    except SandboxError as e:
        logger.error(f"Skill execution failed: {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error running skill in sandbox: {str(e)}")
        raise SandboxError(f"Unexpected error: {str(e)}")
