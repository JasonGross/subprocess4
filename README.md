# subprocess4

Python subprocess wrapper using `os.wait4()` to get resource usage. Requires Python 3.8+ and POSIX.

```python
import subprocess4

result = subprocess4.run(['ls', '-l'], capture_output=True)
print(result.rusage.ru_utime)  # User CPU time

returncode, rusage = subprocess4.call4(['python', '--version'])
proc = subprocess4.Popen(['cmd'])
returncode, rusage = proc.wait4()
```
