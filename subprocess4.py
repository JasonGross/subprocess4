import os
import subprocess
import warnings
from typing import Optional, Union
from subprocess import (
    PIPE,
    STDOUT,
    call,
    check_call,
    getstatusoutput,
    getoutput,
    check_output,
    DEVNULL,
    SubprocessError,
)

__all__ = [
    "Popen",
    "PIPE",
    "STDOUT",
    "call",
    "call4",
    "check_call",
    "check_call4",
    "getstatusoutput",
    "getoutput",
    "check_output",
    "run",
    "CalledProcessError",
    "DEVNULL",
    "SubprocessError",
    "TimeoutExpired",
    "CompletedProcess",
]

# use presence of msvcrt to detect Windows-like platforms (see bpo-8110)
try:
    import msvcrt
except ModuleNotFoundError:
    _mswindows = False
else:
    _mswindows = True

# Mimic the subprocess module's internal platform check
_IS_POSIX = os.name == "posix"

if hasattr(subprocess, "_del_safe"):
    if subprocess._del_safe.waitpid is not None and hasattr(os, "wait4"):
        subprocess._del_safe.wait4 = os.wait4
    else:
        subprocess._del_safe.wait4 = None

class CalledProcessError(subprocess.CalledProcessError):
    """Raised when run() is called with check=True and the process
    returns a non-zero exit status.

    Attributes:
      cmd, returncode, stdout, stderr, output, rusage
    """

    def __init__(self, returncode, cmd, output=None, stderr=None, rusage=None):
        super().__init__(returncode, cmd, output, stderr)
        self.rusage = rusage


class TimeoutExpired(subprocess.TimeoutExpired):
    """This exception is raised when the timeout expires while waiting for a
    child process.

    Attributes:
        cmd, output, stdout, stderr, timeout
    """

    def __init__(self, cmd, timeout, output=None, stderr=None, rusage=None):
        super().__init__(cmd, timeout, output, stderr)
        self.rusage = rusage


def call4(*popenargs, timeout=None, **kwargs):
    """Run command with arguments.  Wait for command to complete or
    for timeout seconds, then return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode, rusage = call4(["ls", "-l"])
    """
    with Popen(*popenargs, **kwargs) as p:
        try:
            return p.wait4(timeout=timeout)
        except:  # Including KeyboardInterrupt, wait handled that.
            p.kill()
            # We don't call p.wait() again as p.__exit__ does that for us.
            raise


def check_call4(*popenargs, **kwargs):
    """Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the call function.  Example:

    check_call4(["ls", "-l"])
    """
    retcode, rusage = call4(*popenargs, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, rusage=rusage)
    return (0, rusage)


class CompletedProcess(subprocess.CompletedProcess):
    """A process that has finished running.

    This is returned by run4().

    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
      rusage: The resource usage object after the process has terminated.
    """

    def __init__(self, args, returncode, stdout=None, stderr=None, rusage=None):
        super().__init__(args, returncode, stdout, stderr)
        self.rusage = rusage

    def __repr__(self):
        args = [
            "args={!r}".format(self.args),
            "returncode={!r}".format(self.returncode),
            "rusage={!r}".format(self.rusage),
        ]
        if self.stdout is not None:
            args.append("stdout={!r}".format(self.stdout))
        if self.stderr is not None:
            args.append("stderr={!r}".format(self.stderr))
        return "{}({})".format(type(self).__name__, ", ".join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero."""
        if self.returncode:
            raise CalledProcessError(
                self.returncode, self.args, self.stdout, self.stderr, self.rusage
            )


def run(
    *popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs
):
    """Run command with arguments and return a CompletedProcess4 instance.

    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them,
    or pass capture_output=True to capture both.

    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.

    If timeout (seconds) is given and the process takes too long,
     a TimeoutExpired exception will be raised.

    There is an optional argument "input", allowing you to
    pass bytes or a string to the subprocess's stdin.  If you use this argument
    you may not also use the Popen constructor's "stdin" argument, as
    it will be used internally.

    By default, all communication is in bytes, and therefore any "input" should
    be bytes, and the stdout and stderr will be bytes. If in text mode, any
    "input" should be a string, and stdout and stderr will be strings decoded
    according to locale encoding, or by "encoding" if set. Text mode is
    triggered by setting any of text, encoding, errors or universal_newlines.

    The other arguments are the same as for the Popen constructor.
    """
    if input is not None:
        if kwargs.get("stdin") is not None:
            raise ValueError("stdin and input arguments may not both be used.")
        kwargs["stdin"] = PIPE

    if capture_output:
        if kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
            raise ValueError(
                "stdout and stderr arguments may not be used with capture_output."
            )
        kwargs["stdout"] = PIPE
        kwargs["stderr"] = PIPE

    with Popen(*popenargs, **kwargs) as process:
        try:
            stdout, stderr, rusage = process.communicate4(input, timeout=timeout)
        except TimeoutExpired as exc:
            process.kill()
            if subprocess._mswindows:
                # Windows accumulates the output in a single blocking
                # read() call run on child threads, with the timeout
                # being done in a join() on those threads.  communicate()
                # _after_ kill() is required to collect that and add it
                # to the exception.
                exc.stdout, exc.stderr, exc.rusage = process.communicate4()
            else:
                # POSIX _communicate already populated the output so
                # far into the TimeoutExpired exception.
                process.wait()
            raise
        except:  # Including KeyboardInterrupt, communicate handled that.
            process.kill()
            # We don't call process.wait() as .__exit__ does that for us.
            raise
        retcode = process.poll()
        if check and retcode:
            raise CalledProcessError(
                retcode, process.args, output=stdout, stderr=stderr, rusage=rusage
            )
    return CompletedProcess(process.args, retcode, stdout, stderr, rusage)


class Popen(subprocess.Popen):
    """
    A POSIX-only subclass of subprocess.Popen that captures resource usage
    information using os.wait4().

    This class provides two new methods and one new property:
      - wait4(timeout=None):
        Returns a tuple of (returncode, rusage).
      - communicate4(input=None, timeout=None):
        Returns a tuple of (stdout, stderr, rusage).
      - rusage (property):
        The resource usage object after the process has terminated.

    If allow_non_posix is False, this class will raise NotImplementedError if instantiated on a non-POSIX
    system or one that lacks os.wait4().
    """

    def __init__(self, *args, allow_non_posix=True, **kwargs):
        """
        Initializes the Popen object and verifies system compatibility.
        """
        if not _IS_POSIX or not hasattr(os, "wait4"):
            if allow_non_posix:
                warnings.warn(
                    "Popen with rusage is not supported on this system. Continuing anyway."
                )
            else:
                raise NotImplementedError(
                    "Popen with rusage is only supported on POSIX systems "
                    "with os.wait4() available. "
                    "Set allow_non_posix=True to continue anyway."
                )

        # This will be populated when the child process is reaped.
        self._rusage = None

        # Call the parent constructor.
        super().__init__(*args, **kwargs)

    @property
    def rusage(self):
        """The os.rusage object captured when the process terminated."""
        return self._rusage

    def _try_wait(self, wait_flags):
        """
        An override of the internal _try_wait method to use os.wait4()
        instead of os.waitpid(). This is the core of the modification.

        os.wait4() returns a 3-tuple: (pid, status, rusage) when a child
        terminates, or (0, 0) if WNOHANG is used and the child is still running.
        This method captures the rusage object and returns the expected
        (pid, status) tuple to the parent class's waiting logic.
        """
        if not hasattr(os, "wait4"):
            return super()._try_wait(wait_flags)
        try:
            # Call os.wait4() to get resource usage info.
            pid, sts, rusage = os.wait4(self.pid, wait_flags)
        except ChildProcessError:
            # This can happen if the process has already been reaped.
            # We mimic the behavior of the parent class in this case.
            return (self.pid, 0)

        # If the PID matches our child, it means the process has been
        # successfully waited on, so we store its resource usage.
        if pid == self.pid:
            self._rusage = rusage

        return (pid, sts)

    def wait4(self, timeout: Union[float, None] = None):
        """
        Waits for the child process to terminate.

        Args:
            timeout (float, optional): The time to wait in seconds. If None,
                                       waits indefinitely.

        Returns:
            tuple: A tuple containing (returncode, rusage_object).
        """
        # The parent's wait() method internally calls our overridden _try_wait(),
        # which populates self._rusage. We simply return the result along
        # with the captured rusage data.
        returncode = self.wait(timeout=timeout)
        return (returncode, self._rusage)

    def communicate4(
        self,
        input: Optional[Union[bytes, str]] = None,
        timeout: Union[float, None] = None,
    ):
        """
        Interacts with the process: sends data to stdin, reads from stdout/stderr,
        and waits for termination.

        Args:
            input (bytes or str, optional): Data to be sent to stdin.
            timeout (float, optional): The timeout in seconds for the entire
                                       communication.

        Returns:
            tuple: A tuple containing (stdout_data, stderr_data, rusage_object).
        """
        # The parent's communicate() method also calls wait() internally,
        # which triggers our _try_wait() override.
        try:
            stdout, stderr = self.communicate(input=input, timeout=timeout)
            return (stdout, stderr, self._rusage)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutExpired(
                self.args, timeout, exc.stdout, exc.stderr, self._rusage
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise CalledProcessError(
                exc.returncode, self.args, exc.stdout, exc.stderr, self._rusage
            ) from exc

    if _IS_POSIX and hasattr(os, "wait4"):

        def _internal_poll(self, _deadstate=None, _del_safe=os):
            """Check if child process has terminated.  Returns returncode
            attribute.

            This method is called by __del__, so it cannot reference anything
            outside of the local scope (nor can any methods it calls).

            """
            if self.returncode is None:
                if not self._waitpid_lock.acquire(False):
                    # Something else is busy calling waitpid.  Don't allow two
                    # at once.  We know nothing yet.
                    return None
                try:
                    if self.returncode is not None:
                        return self.returncode  # Another thread waited.
                    if hasattr(_del_safe, "wait4") and _del_safe.wait4 is not None:
                        try:
                            pid, sts, rusage = _del_safe.wait4(
                                self.pid, _del_safe.WNOHANG
                            )
                        except OSError as e:
                            if _deadstate is not None:
                                self.returncode = _deadstate
                            elif e.errno == _del_safe.ECHILD:
                                # This happens if SIGCLD is set to be ignored or
                                # waiting for child processes has otherwise been
                                # disabled for our process.  This child is dead, we
                                # can't get the status.
                                self.returncode = 0
                            return self.returncode
                        if pid == self.pid:
                            self._rusage = rusage
                            self._handle_exitstatus(sts)
                    else:
                        # Fallback to waitpid if wait4 is not available (though we already checked in __init__).
                        pid, sts = _del_safe.waitpid(self.pid, _del_safe.WNOHANG)
                        if pid == self.pid:
                            self._handle_exitstatus(sts)
                finally:
                    self._waitpid_lock.release()
            return self.returncode
