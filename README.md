# subprocess4

Python subprocess wrapper using `os.wait4()` to get resource usage information.

## Installation

```bash
pip install subprocess4
```

## Requirements

- Python 3.7+
- POSIX system with `os.wait4()` support (Linux, macOS, BSD, etc.)

On non-POSIX systems (like Windows), the module will issue a warning but continue to work without resource usage information.

## Features

`subprocess4` extends Python's standard `subprocess` module to provide resource usage information (CPU time, memory, etc.) for executed processes. It provides drop-in replacements for common subprocess functions with added `rusage` information.

## Usage Examples

### Basic Usage with `run()`

The `run()` function is similar to `subprocess.run()`, but returns a `CompletedProcess` object with a `rusage` attribute:

```python
import subprocess4

# Run a command and get resource usage
result = subprocess4.run(['ls', '-l'], capture_output=True)

print(f"Return code: {result.returncode}")
print(f"Output: {result.stdout.decode()}")
print(f"User CPU time: {result.rusage.ru_utime}")
print(f"System CPU time: {result.rusage.ru_stime}")
```

### Using `call4()` for Simple Commands

`call4()` returns both the return code and resource usage:

```python
import subprocess4

returncode, rusage = subprocess4.call4(['python', '--version'])

print(f"Process exited with code: {returncode}")
print(f"Total CPU time: {rusage.ru_utime + rusage.ru_stime} seconds")
```

### Using `check_call4()` for Error Handling

`check_call4()` raises `CalledProcessError` on non-zero exit codes, with `rusage` available in the exception:

```python
import subprocess4

try:
    returncode, rusage = subprocess4.check_call4(['false'])
except subprocess4.CalledProcessError as e:
    print(f"Command failed with code {e.returncode}")
    print(f"Resource usage: {e.rusage}")
```

### Using `Popen` for More Control

For more advanced use cases, use `Popen` directly:

```python
import subprocess4

# Create a process
proc = subprocess4.Popen(['python', '-c', 'import time; time.sleep(0.1)'])

# Wait and get resource usage
returncode, rusage = proc.wait4()

print(f"Process completed with return code: {returncode}")
print(f"User time: {rusage.ru_utime}s")
print(f"System time: {rusage.ru_stime}s")
print(f"Max RSS: {rusage.ru_maxrss} KB")  # Maximum resident set size
```

### Using `communicate4()` for I/O

`communicate4()` handles stdin/stdout/stderr communication and returns resource usage:

```python
import subprocess4

proc = subprocess4.Popen(
    ['python', '-c', 'import sys; sys.stdout.write(sys.stdin.read().upper())'],
    stdin=subprocess4.PIPE,
    stdout=subprocess4.PIPE
)

stdout, stderr, rusage = proc.communicate4(input=b'hello world')

print(f"Output: {stdout.decode()}")  # "HELLO WORLD"
print(f"CPU time: {rusage.ru_utime + rusage.ru_stime}s")
```

### Context Manager Usage

`Popen` can be used as a context manager:

```python
import subprocess4

with subprocess4.Popen(['ls', '-l']) as proc:
    returncode, rusage = proc.wait4()
    print(f"Resource usage available: {rusage is not None}")

# rusage is still available after the context exits
print(f"Process used {rusage.ru_utime}s of user CPU time")
```

### Timeout Handling

All functions support timeouts, and `TimeoutExpired` exceptions include `rusage`:

```python
import subprocess4

try:
    result = subprocess4.run(
        ['python', '-c', 'import time; time.sleep(10)'],
        timeout=1.0
    )
except subprocess4.TimeoutExpired as e:
    print(f"Process timed out after {e.timeout} seconds")
    if e.rusage:
        print(f"Resource usage before timeout: {e.rusage}")
```

### Accessing Resource Usage Fields

The `rusage` object provides detailed resource usage information:

```python
import subprocess4

result = subprocess4.run(['python', '--version'], capture_output=True)
rusage = result.rusage

# Time information
print(f"User CPU time: {rusage.ru_utime}")
print(f"System CPU time: {rusage.ru_stime}")

# Memory information (if available)
if hasattr(rusage, 'ru_maxrss'):
    print(f"Maximum resident set size: {rusage.ru_maxrss} KB")

# I/O statistics (if available)
if hasattr(rusage, 'ru_inblock'):
    print(f"Block input operations: {rusage.ru_inblock}")
if hasattr(rusage, 'ru_oublock'):
    print(f"Block output operations: {rusage.ru_oublock}")

# Context switches (if available)
if hasattr(rusage, 'ru_nvcsw'):
    print(f"Voluntary context switches: {rusage.ru_nvcsw}")
if hasattr(rusage, 'ru_nivcsw'):
    print(f"Involuntary context switches: {rusage.ru_nivcsw}")
```

### Non-POSIX Systems

On systems without `os.wait4()` support (like Windows), the module will warn but continue:

```python
import subprocess4
import warnings

# By default, a warning is issued
result = subprocess4.run(['echo', 'hello'])
# Warning: Popen with rusage is not supported on this system.

# To raise an exception instead:
try:
    proc = subprocess4.Popen(['echo', 'hello'], allow_non_posix=False)
except NotImplementedError as e:
    print(f"Not supported: {e}")

# On non-POSIX systems, rusage will be None
if result.rusage is None:
    print("Resource usage not available on this system")
```

### Complete Example: Benchmarking a Command

```python
import subprocess4
import time

def benchmark_command(cmd):
    """Run a command and report its resource usage."""
    start = time.time()

    try:
        result = subprocess4.run(
            cmd,
            capture_output=True,
            timeout=30.0
        )

        wall_time = time.time() - start
        rusage = result.rusage

        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"Wall clock time: {wall_time:.3f}s")
        print(f"User CPU time: {rusage.ru_utime:.3f}s")
        print(f"System CPU time: {rusage.ru_stime:.3f}s")
        print(f"Total CPU time: {rusage.ru_utime + rusage.ru_stime:.3f}s")

        if hasattr(rusage, 'ru_maxrss'):
            print(f"Peak memory usage: {rusage.ru_maxrss} KB")

        return result

    except subprocess4.TimeoutExpired as e:
        print(f"Command timed out after {e.timeout}s")
        if e.rusage:
            print(f"CPU time before timeout: {e.rusage.ru_utime + e.rusage.ru_stime:.3f}s")
        raise

# Example usage
benchmark_command(['python', '-c', 'sum(range(1000000))'])
```

## API Reference

### Functions

- **`run(*popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs)`**
  - Run a command and return a `CompletedProcess` instance with `rusage` attribute.

- **`call4(*popenargs, timeout=None, **kwargs)`**
  - Run a command and return `(returncode, rusage)` tuple.

- **`check_call4(*popenargs, **kwargs)`**
  - Run a command and return `(returncode, rusage)`. Raises `CalledProcessError` on non-zero exit.

### Classes

- **`Popen(*args, allow_non_posix=True, **kwargs)`**
  - Extended `subprocess.Popen` with resource usage support.
  - Methods: `wait4(timeout=None)`, `communicate4(input=None, timeout=None)`
  - Property: `rusage` - Resource usage object (available after process completes)

- **`CompletedProcess`**
  - Extended `subprocess.CompletedProcess` with `rusage` attribute.

- **`CalledProcessError`**
  - Extended `subprocess.CalledProcessError` with `rusage` attribute.

- **`TimeoutExpired`**
  - Extended `subprocess.TimeoutExpired` with `rusage` attribute.

## License

See LICENSE file for details.
