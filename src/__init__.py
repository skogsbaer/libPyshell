"""

A python module for writing shell-scripts in Python. It introduces
new functionality, bundles functions distributed over several modules of
Python's standard library in one place and provides several auxiliary functions.

The function's provided by the `shell` module are named after the corresponding
Unix commands.

Here's a quick demo:

~~~python
from shell import *

rm('a/b/foo.txt')
mv('X.pdf', f'{HOME}/contents.pdf')

files = ls('Documents', '*.txt', '*.c')
magicFiles = run(['grep', 'magic'] + files, captureStdout=splitLines, onError='ignore').stdout
~~~

* Requirements: Python 3.
* [Homepage](https://github.com/skogsbaer/libPyshell)

"""
import os
import os.path
import subprocess
import re
import sys
import atexit
import tempfile
import shutil
import fnmatch
from threading import Thread
import traceback
from typing import *

_pyshell_debug = os.environ.get('PYSHELL_DEBUG', 'no').lower()
_PYSHELL_DEBUG = _pyshell_debug in ['yes', 'true', 'on']

#: The value of the environment variable `HOME`
HOME = os.environ.get('HOME')

try:
    #: /dev/null
    _devNull = open('/dev/null')
except:
    _devNull = open('nul')

DEV_NULL = _devNull

_FILE = Union[int, IO[Any], None]

atexit.register(lambda: DEV_NULL.close())

def _debug(s: str):
    if _PYSHELL_DEBUG:
        sys.stderr.write('[DEBUG] ' + str(s) + '\n')

def fatal(s: str):
    """Display an error message to stderr."""
    sys.stderr.write('ERROR: ' + str(s) + '\n')

def resolveProg(*l: str) -> Optional[str]:
    """Return the first program in the list that exist and is runnable.
    >>> resolveProg()
    >>> resolveProg('foobarbaz', 'cat', 'grep')
    '/bin/cat'
    >>> resolveProg('foobarbaz', 'padauz')
    """
    for x in l:
        cmd = 'command -v %s' % quote(x)
        result = run(cmd, captureStdout=True, onError='ignore')
        if result.exitcode == 0:
            return result.stdout.strip()
    return None

def gnuProg(p: str):
    """Get the GNU version of program p."""
    prog = resolveProg('g' + p, p)
    if not prog:
        raise ShellError('Program ' + str(p) + ' not found at all')
    res = run('%s --version' % prog, captureStdout=True, onError='ignore')
    if 'GNU' in res.stdout:
        _debug('Resolved program %s as %s' % (p, prog))
        return prog
    else:
        raise ShellError('No GNU variant found for program ' + str(p))

class RunResult:
    """Represents the result of running a program using the `run` function.
    Attribute `exitcode` holds the exit code,
    attribute `stdout` contains the output printed in stdout (only if `run`
    was invoked with `captureStdout=True`).
    """
    def __init__(self, stdout: Any, stderr: Any, exitcode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exitcode = exitcode
    def __repr__(self):
        return 'RunResult(exitcode=%d, stdout=%r, stderr=%r)' % (self.exitcode, self.stdout, self.stderr)
    def __eq__(self, other: Any):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other: Any):
        return not self.__eq__(other)
    def __hash__(self):
        return hash(self.__dict__)

class ShellError(BaseException):
    """The base class for exceptions thrown by this module."""
    def __init__(self, msg: str):
        self.msg = msg
    def __str__(self):
        return self.msg

class RunError(ShellError):
    """
    This exception is thrown if a program invoked with `run(onError='raise')`
    returns a non-zero exit code.

    Attributes:

    * `exitcode`
    * `stderr`: output on stderr (if `run` configured to capture this output)
    """
    def __init__(self, cmd: Union[str, list[str]],
                 exitcode: int,
                 stdout: Union[str,bytes],
                 stderr: Union[str,bytes]):
        self.cmd = cmd
        self.exitcode = exitcode
        self.stderr = stderr
        self.stdout = stdout
        msg = 'Command ' + repr(self.cmd) + " failed with exit code " + str(self.exitcode)
        if stderr:
            msg = msg + '\nstderr:\n' + str(stderr)
        super(RunError, self).__init__(msg)
    def __repr__(self):
        return 'RunError(cmd=%r, exitcode=%d, stdout=%r, stderr=%r)' % \
            (self.cmd, self.exitcode, self.stdout, self.stderr)

def splitOn(splitter: str) -> Callable[[str], list[str]]:
    """Return a function that splits a string on the given splitter string.

    To be used with the `captureStdout` or `captureStderr` parameter
    of `run`.

    The function returned filters an empty string at the end of the result list.

    >>> splitOn('X')("aXbXcX")
    ['a', 'b', 'c']
    >>> splitOn('X')("aXbXc")
    ['a', 'b', 'c']
    >>> splitOn('X')("abc")
    ['abc']
    >>> splitOn('X')("abcX")
    ['abc']
    """
    def f(s: str) -> list[str]:
        l = s.split(splitter)
        if l and not l[-1]:
            return l[:-1]
        else:
            return l
    return f

def splitLines(s: str) -> list[str]:
    """
    Split on line endings.
    To be used with the `captureStdout` or `captureStderr` parameter
    of `run`.
    """
    s = s.strip()
    if not s:
        return []
    else:
        return s.split('\n')

def run(cmd: Union[list[str], str],
        onError: Literal['raise', 'die', 'ignore']='raise',
        input: Union[str, bytes, None]=None,
        encoding: str='utf-8',
        captureStdout: Union[bool,Callable[[str], Any],_FILE]=False,
        captureStderr: Union[bool,Callable[[str], Any],_FILE]=False,
        stderrToStdout: bool=False,
        cwd: Optional[str]=None,
        env: Optional[Dict[str, str]]=None,
        freshEnv: Optional[Dict[str, str]]=None,
        decodeErrors: str='replace',
        decodeErrorsStdout: Optional[str]=None,
        decodeErrorsStderr: Optional[str]=None
        ) -> RunResult:
    """Runs the given command.

    Parameters:

    * `cmd`: the command, either a list (command with raw args)
         or a string (subject to shell expansion)
    * `onError`: what to do if the child process finishes with an exit code different from 0
        * 'raise': raise an exception (the default)
        * 'die': terminate the whole process
        * 'ignore': just return the result
    * `input`: string or bytes that is send to the stdin of the child process.
    * `encoding`: the encoding for stdin, stdout, and stderr. If `encoding == 'raw'`,
        then the raw bytes are passed/returned. It is an error if input is a string
        and `encoding == 'raw'`
    * `captureStdout` and `captureStderr`: what to do with stdout/stderr of the child process. Possible values:
        * False: stdout is not captured and goes to stdout of the parent process (the default)
        * True: stdout is captured and returned
        * A function: stdout is captured and the result of applying the function to the captured
          output is returned. In this case, encoding must not be `'raw'`.
          Use splitLines as this function to split the output into lines
        * An existing file descriptor or a file object: stdout goes to the file descriptor or file
    * `stderrToStdout`: should stderr be sent to stdout?
    * `cwd`: working directory
    * `env`: dictionary with additional environment variables.
    * `freshEnv`: dictionary with a completely fresh environment.
    * `decodeErrors`: how to handle decoding errors on stdout and stderr.
    * `decodeErrorsStdout` and `decodeErrorsStderr`: overwrite the value of decodeErrors for stdout
        or stderr

    Returns:
      a `RunResult` value, given access to the captured stdout of the child process (if it was
      captured at all) and to the exit code of the child process.

    Raises: a `RunError` if `onError='raise'` and the command terminates with a non-zero exit code.

    Starting with Python 3.5, the `subprocess` module defines a similar function.

    >>> run('/bin/echo foo')
    RunResult(exitcode=0, stdout='', stderr='')
    >>> run('/bin/echo -n foo', captureStdout=True)
    RunResult(exitcode=0, stdout='foo', stderr='')
    >>> run('/bin/echo -n foo', captureStdout=lambda s: s + 'X')
    RunResult(exitcode=0, stdout='fooX', stderr='')
    >>> run('/bin/echo foo', captureStdout=False)
    RunResult(exitcode=0, stdout='', stderr='')
    >>> run('cat', captureStdout=True, input='blub')
    RunResult(exitcode=0, stdout='blub', stderr='')
    >>> try:
    ...     run('/bin/echo -n foo 1>&2; /bin/echo -n bar; false', captureStdout=True, captureStderr=True)
    ...     raise 'exception expected'
    ... except RunError as e:
    ...     print(repr(e))
    ...
    RunError(cmd='/bin/echo -n foo 1>&2; /bin/echo -n bar; false', exitcode=1, stdout='bar', stderr='foo')
    >>> run('false', onError='ignore')
    RunResult(exitcode=1, stdout='', stderr='')
    >>> run('/bin/echo -n foo; /bin/echo -n bar 1>&2', captureStdout=True, captureStderr=True)
    RunResult(exitcode=0, stdout='foo', stderr='bar')
    >>> run('/bin/echo -n foo 1>&2; /bin/echo -n bar', captureStderr=lambda s: s + 'X')
    RunResult(exitcode=0, stdout='', stderr='fooX')
    """
    if type(cmd) != str and type(cmd) != list:
        raise ShellError('cmd parameter must be a string or a list')
    if type(cmd) == str:
        cmd = cmd.replace('\x00', ' ')
        cmd = cmd.replace('\n', ' ')
    if decodeErrorsStdout is None:
        decodeErrorsStdout = decodeErrors
    if decodeErrorsStderr is None:
        decodeErrorsStderr = decodeErrors
    shouldReturnStdout = (isinstance(captureStdout, Callable) or
                            (type(captureStdout) == bool and captureStdout))
    stdout: _FILE = None
    if shouldReturnStdout:
        stdout = subprocess.PIPE
    elif isinstance(captureStdout, int) or isinstance(captureStdout, IO):
        stdout = captureStdout
    stdin = None
    if input:
        stdin = subprocess.PIPE
    stderr = None
    if stderrToStdout:
        stderr = subprocess.STDOUT
    elif captureStderr:
        stderr = subprocess.PIPE
    input_str = 'None'
    inputBytes: Optional[bytes] = None
    if input and isinstance(input, str):
        input_str = '<' + str(len(input)) + ' characters>'
        if encoding != 'raw':
            inputBytes = input.encode(encoding)
        else:
            raise ValueError('Given str object as input, but encoding is raw')
    elif input:
        inputBytes = input
    _debug('Running command ' + repr(cmd) + ' with captureStdout=' + str(captureStdout) +
          ', onError=' + onError + ', input=' + input_str)
    popenEnv = None
    if env:
        popenEnv = os.environ.copy()
        popenEnv.update(env)
    elif freshEnv:
        popenEnv = freshEnv.copy()
        if env:
            popenEnv.update(env)
    # Ensure correct ordering of outputs
    if stdout is None:
        sys.stdout.flush()
    if stderr is None:
        sys.stderr.flush()
    pipe = subprocess.Popen(
        cmd, shell=(type(cmd) == str),
        stdout=stdout, stdin=stdin, stderr=stderr,
        cwd=cwd, env=popenEnv
    )
    (stdoutData, stderrData) = pipe.communicate(input=inputBytes)
    stdoutData = massageOutput(stdoutData, encoding, decodeErrorsStdout, captureStdout)
    stderrData = massageOutput(stderrData, encoding, decodeErrorsStderr, captureStderr)
    exitcode = pipe.returncode
    if onError == 'raise' and exitcode != 0:
        err = RunError(cmd, exitcode, stdoutData, stderrData)
        raise err
    if onError == 'die' and exitcode != 0:
        sys.exit(exitcode)
    return RunResult(stdoutData, stderrData, exitcode)

def massageOutput(data: Any, encoding: str, decodeErrors: str,
                  capture: Union[bool,Callable[[str], Any],_FILE]):
    if data and encoding != 'raw':
        data = data.decode(encoding, errors=decodeErrors)
    if not data:
        data = ''
    if isinstance(capture, Callable) and isinstance(data, str):
        data = capture(data)
    return data

# the quote function is stolen from https://hg.python.org/cpython/file/3.5/Lib/shlex.py
_find_unsafe = re.compile(r'[^\w@%+=:,./-]').search
def quote(s: str) -> str:
    """Return a shell-escaped version of the string `s`.
    """
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s
    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"

def listAsArgs(l: list[str]) -> str:
    """
    Converts a list of command arguments to a single argument string.
    """
    return ' '.join([quote(x) for x in l])

def mergeDicts(*l: dict[Any, Any]) -> dict[Any, Any]:
    """
    Merges a list of dictionaries. Useful for e.g. merging environment dictionaries.
    """
    res: dict[Any, Any] = {}
    for d in l:
        res.update(d)
    return res

#: The directory where the script is located.
THIS_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

#: export
basename = os.path.basename

#: export
filename = os.path.basename

#: export
dirname = os.path.dirname

#: export
abspath = os.path.abspath

#: export
realpath = os.path.realpath

#: export
exists = os.path.exists

isfile = os.path.isfile # DEPRECATED

#: export
isFile = os.path.isfile

isdir = os.path.isdir # DEPRECATED

#: export
isDir = os.path.isdir

islink = os.path.islink # DEPRECATED

#: export
isLink = os.path.islink

splitext = os.path.splitext # DEPRECATED

#: export
splitExt = os.path.splitext

def removeExt(p: str) -> str:
    """Removes the extension of a filename."""
    return splitext(p)[0]

def getExt(p: str) -> str:
    """Returns the extension of a filename."""
    return splitext(p)[1]

#: export
expandEnvVars = os.path.expandvars

#: export
pjoin = os.path.join

def mv(src: str, target: str):
    """
    Renames src to target.
    If target is an existing directory, src is move into target
    """
    if isDir(target):
        target = pjoin(target, basename(src))
    os.rename(src, target)

def removeFile(path: str):
    """
    Removes the given file. Throws an error if `path` is not a file.
    """
    if isFile(path):
        os.remove(path)
    else:
        raise ShellError(f"{path} is not a file")

def cp(src: str, target: str):
    """
    Copy `src` to `target`.

    * If `src` is a file and `target` is a file: overwrites `target`.
    * If `src` is a file and `target` is a dirname: places the copy in directory `target`,
      with the basename of `src.
    * If `src` is a directory then `target` must also be a directory: copies
      the `src` directory (*not* its content) to `target`.
    """
    if isFile(src):
        if isDir(target):
            fname = basename(src)
            targetfile = pjoin(target, fname)
        else:
            targetfile = target
        return shutil.copyfile(src, targetfile)
    else:
        if isDir(target):
            name = basename(src)
            targetDir = pjoin(target, name)
            return shutil.copytree(src, targetDir)
        elif exists(target):
            raise ValueError(f'Cannot copy directory {src} to non-directory {target}')
        else:
            return shutil.copytree(src, target)

def abort(msg: str):
    """Print an error message and abort the shell script."""
    sys.stderr.write('ERROR: ' + msg + '\n')
    sys.exit(1)

def mkdir(d: str, mode: int=0o777, createParents: bool=False):
    """
    Creates directory `d` with `mode`.
    """
    if createParents:
        os.makedirs(d, mode, exist_ok=True)
    else:
        os.mkdir(d, mode)

def mkdirs(d: str, mode: int=0o777):
    """
    Creates directory `d` and all missing parent directories with `mode`.
    """
    mkdir(d, mode, createParents=True)

def touch(path: str):
    """
    Create an empty file at `path`.
    """
    run(['touch', path])

def cd(x: str):
    """Changes the working directory."""
    _debug('Changing directory to ' + x)
    os.chdir(x)

def pwd():
    """
    Return the current working directory.
    """
    return os.getcwd()

class workingDir:
    """
    Scoped change of working directory, to be used in a `with`-block:

    ```
    with workingDir(path):
        # working directory is now path
    # previous working directory is restored
    ```
    """
    def __init__(self, new_dir: str):
        self.new_dir = new_dir
    def __enter__(self):
        self.old_dir = pwd()
        cd(self.new_dir)
    def __exit__(self, exc_type: Any, value: Any, traceback: Any):
        cd(self.old_dir)
        return False # reraise expection

def rm(path: str, force: bool=False):
    """
    Remove the file at `path`.
    """
    if force and not exists(path):
        return
    os.remove(path)

def rmdir(d: str, recursive: bool=False):
    """
    Remove directory `d`. Set `recursive=True` if the directory is not empty.
    """
    if recursive:
        shutil.rmtree(d)
    else:
        os.rmdir(d)

# See https://stackoverflow.com/questions/9741351/how-to-find-exit-code-or-reason-when-atexit-callback-is-called-in-python
class _ExitHooks(object):
    def __init__(self):
        self.exitCode = None
        self.exception = None

    def hook(self):
        self._origExit = sys.exit
        self._origExcHandler = sys.excepthook
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code: Optional[int]=0):
        if code is None:
            myCode = 0
        elif type(code) != int:
            myCode = 1
        else:
            myCode = code
        self.exitCode = myCode
        self._origExit(code)

    def exc_handler(self, exc_type: Any, exc: Any, *args: Any):
        self.exception = exc
        self._origExcHandler(exc_type, exc, *args)

    def isExitSuccess(self):
        return (self.exitCode is None or self.exitCode == 0) and self.exception is None

    def isExitFailure(self):
        return not self.isExitSuccess()

_hooks = _ExitHooks()
_hooks.hook()

AtExitMode = Literal[True, False, 'ifSuccess', 'ifFailure']

def _registerAtExit(action: Any, mode: AtExitMode):
    def f():
        _debug(f'Running exit hook, exit code: {_hooks.exitCode}, mode: {mode}')
        if mode is True:
            action()
        elif mode in ['ifSuccess'] and _hooks.isExitSuccess():
            action()
        elif mode in ['ifFailure'] and _hooks.isExitFailure():
            action()
        else:
            _debug('Not running exit action')
    atexit.register(f)

def mkTempFile(suffix: str='', prefix: str='',
               dir:Optional[str]=None,
               deleteAtExit:AtExitMode=True):
    """Create a temporary file.

    `deleteAtExit` controls if and how the file is deleted once the shell sript terminates.
   It has one of the following values.

    * True: the file is deleted unconditionally on exit.
    * 'ifSuccess': the file is deleted if the program exists with code 0
    * 'ifFailure': the file is deleted if the program exists with code != 0
    """


    f = tempfile.mktemp(suffix, prefix, dir)
    if deleteAtExit:
        def action():
            if isFile(f):
                rm(f)
        _registerAtExit(action, deleteAtExit)
    return f

def mkTempDir(suffix: str='', prefix: str='tmp',
              dir: Optional[str]=None,
              deleteAtExit: AtExitMode=True):
    """Create a temporary directory. The `deleteAtExit` parameter
    has the same meaning as for `mkTempFile`.
    """
    d = tempfile.mkdtemp(suffix, prefix, dir)
    if deleteAtExit:
        def action():
            if isDir(d):
                rmdir(d, True)
        _registerAtExit(action, deleteAtExit)
    return d

class tempDir:
    """
    Scoped creation of a temporary directory, to be used in a `with`-block:

    ```
    with tempDir() as d:
        # do something with d
    # d gets deleted at the end of the with-block
    ```

    Per default, the temporary directory is deleted at the end of the `with`-block.
    With `delete=False`, deletion is deactivated. With `onException=False`, deletion
    is only performed if the `with`-block finishes without an exception.
    """
    def __init__(self, suffix: str='', prefix: str='tmp', dir: Optional[str]=None,
                 onException: bool=True, delete: bool=True):
        self.suffix = suffix
        self.prefix = prefix
        self.dir = dir
        self.onException = onException
        self.delete = delete
    def __enter__(self):
        self.dir_to_delete = mkTempDir(suffix=self.suffix,
                                       prefix=self.prefix,
                                       dir=self.dir,
                                       deleteAtExit=False)
        return self.dir_to_delete
    def __exit__(self, exc_type: Any, value: Any, traceback: Any):
        if exc_type is not None and not self.onException:
            return False # reraise
        if self.delete:
            if isDir(self.dir_to_delete):
                rmdir(self.dir_to_delete, recursive=True)
        return False # reraise expection

def ls(d: str, *globs: str) -> list[str]:
    """
    Returns a list of pathnames contained in `d`, matching any of the the given `globs`.

    If no globs are given, all files are returned.

    The pathnames in the result list contain the directory part `d`.

    >>> '../src/__init__.py' in ls('../src/', '*.py', '*.txt')
    True
    """
    res: list[str] = []
    if not d:
        d = '.'
    for f in os.listdir(d):
        if len(globs) == 0:
            res.append(os.path.join(d, f))
        else:
            for g in globs:
                if fnmatch.fnmatch(f, g):
                    res.append(os.path.join(d, f))
                    break
    return res

def readBinaryFile(name: str):
    """Return the binary content of file `name`."""
    with open(name, 'rb') as f:
        return f.read()

def readFile(name: str):
    """Return the textual content of file `name`."""
    with open(name, 'r', encoding='utf-8') as f:
        return f.read()

def writeFile(name: str, content: str):
    """Write text `content` to file `name`."""
    with open(name, 'w', encoding='utf-8') as f:
        f.write(content)

def writeBinaryFile(name: str, content: bytes):
    """Write binary string `content` to file `name`."""
    with open(name, 'wb') as f:
        f.write(content)

def _openForTee(x: Any) -> _FILE:
    if type(x) == str:
        return open(x, 'wb')
    elif type(x) == tuple:
        name: Any = x[0]
        mode: Any = x[1]
        if mode == 'w':
            return open(name, 'wb')
        elif mode == 'a':
            return open(name, 'ab')
        raise ValueError(f'Bad mode: {mode}')
    elif x == TEE_STDERR:
        return sys.stderr
    elif x == TEE_STDOUT:
        return sys.stdout
    else:
        raise ValueError(f'Invalid file argument: {x}')

def _teeChildWorker(pRead: Any, pWrite: Any, fileNames: Any, bufferSize: int):
    _debug('child of tee started')
    files: list[Any] = []
    try:
        for x in fileNames:
            files.append(_openForTee(x))
        bytes = os.read(pRead, bufferSize)
        while(bytes):
            for f in files:
                if f is sys.stderr or f is sys.stdout:
                    data = bytes.decode('utf8', errors='replace')
                else:
                    data = bytes
                f.write(data)
                f.flush()
                _debug(f'Wrote {data} to {f}')
            bytes = os.read(pRead, bufferSize)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        sys.stderr.write(f'ERROR: tee failed with an exception: {e}\n')
        for l in lines:
            sys.stderr.write(l)
    finally:
        for f in files:
            if f is not sys.stderr and f is not sys.stdout:
                try:
                    _debug(f'closing {f}')
                    f.close()
                except:
                    pass
            _debug(f'Closed {f}')
        _debug('child of tee finished')

def _teeChild(pRead: Any, pWrite: Any, files: Any, bufferSize: Any):
    try:
        _teeChildWorker(pRead, pWrite, files, bufferSize)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        print(''.join('BUG in shell.py ' + line for line in lines))

#: Special value for `createTee`.
TEE_STDOUT = object()

#: Special value for `createTee`.
TEE_STDERR = object()

def createTee(files: list[Any], bufferSize: int=128):
        """Get a file object that will mirror writes across multiple files.
        The result can be used for the `captureStdout` or `captureStderr` parameter
        of `run` to mimic the behavior of the `tee` command.

        Parameters:

        * `files`: A list where each element is one of the following:
             * A file name, to be opened for writing
             * A pair `(fileName, mode)`, where mode is `'w'` or `'a'`
             * One of the constants `TEE_STDOUT` or `TEE_STDERR`. Output then goes
               to stdout/stderr.

        *  `bufferSize`:   Control the size of the buffer between writes to the
                         resulting file object and the list of files.

        Result: a file-like object
        """
        pRead, pWrite = os.pipe()
        p = Thread(target=_teeChild, args=(pRead, pWrite, files, bufferSize))
        p.start()
        return os.fdopen(pWrite,'w')

def exit(code: int):
    """Exit the program with the given exit `code`.
    """
    sys.exit(code)

#: export
fileSize = os.path.getsize
