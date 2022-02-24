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
import types
import fnmatch
import shutil
from threading import Thread
import traceback
from typing import *

_pyshell_debug = os.environ.get('PYSHELL_DEBUG', 'no').lower()
_PYSHELL_DEBUG = _pyshell_debug in ['yes', 'true', 'on']

#: The value of the environment variable `HOME`
HOME = os.environ.get('HOME')

try:
    #: /dev/null
    DEV_NULL = open('/dev/null')
except:
    DEV_NULL = open('nul')

atexit.register(lambda: DEV_NULL.close())

def _debug(s):
    if _PYSHELL_DEBUG:
        sys.stderr.write('[DEBUG] ' + str(s) + '\n')

def fatal(s):
    """Display an error message to stderr."""
    sys.stderr.write('ERROR: ' + str(s) + '\n')

def resolveProg(*l):
    """Return the first program in the list that exist and is runnable.
    >>> resolveProg()
    >>> resolveProg('foobarbaz', 'python', 'grep')
    'python'
    >>> resolveProg('foobarbaz', 'padauz')
    """
    for x in l:
        ecode = run('command -v %s' % quote(x), captureStdout=DEV_NULL,
                    onError='ignore').exitcode
        if ecode == 0:
            return x
    return None

def gnuProg(p):
    """Get the GNU version of progam p."""
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
    def __init__(self, stdout, exitcode):
        self.stdout = stdout
        self.exitcode = exitcode
    def __repr__(self):
        return 'RunResult(exitcode=%d, stdout=%r) '% (self.exitcode, self.stdout)
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return hash(self.__dict__)

class ShellError(BaseException):
    """The base class for exceptions thrown by this module."""
    def __init__(self, msg):
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
    def __init__(self, cmd, exitcode, stderr=None):
        self.cmd = cmd
        self.exitcode = exitcode
        self.stderr = stderr
        msg = 'Command ' + repr(self.cmd) + " failed with exit code " + str(self.exitcode)
        if stderr:
            msg = msg + '\nstderr:\n' + str(stderr)
        super(RunError, self).__init__(msg)

def splitOn(splitter):
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
    def f(s):
        l = s.split(splitter)
        if l and not l[-1]:
            return l[:-1]
        else:
            return l
    return f

def splitLines(s):
    """
    Split on line endings.
    To be used with the `captureStdout` or `captureStderr` parameter
    of `run`.
    """
    return s.strip().split('\n')

def run(cmd,
        onError='raise',
        input=None,
        encoding='utf-8',
        captureStdout=False,
        captureStderr=False,
        stderrToStdout=False,
        cwd=None,
        env=None,
        freshEnv=None,
        decodeErrors='replace',
        decodeErrorsStdout=None,
        decodeErrorsStderr=None
        ):
    """Runs the given command.

    Parameters:

    * `cmd`: the command, either a list (command with raw args)
         or a string (subject to shell expansion)
    * `onError`: what to do if the child process finishes with an exit code different from 0
        * 'raise': raise an exception (the default)
        * 'die': terminate the whole process
        * 'ignore'
    * `input`: string that is send to the stdin of the child process.
    * `encoding`: the encoding for stdin, stdout, and stderr. If `encoding == 'raw'`,
        then the raw bytes are passed/returned.
    * `captureStdout` and `captureStderr`: what to do with stdout/stderr of the child process. Possible values:
        * False: stdout is not captured and goes to stdout of the parent process (the default)
        * True: stdout is captured and returned
        * A function: stdout is captured and the result of applying the function to the captured
          output is returned. Use splitLines as this function to split the output into lines
        * An existing file descriptor or a file object: stdout goes to the file descriptor or file
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

    >>> run('/bin/echo foo') == RunResult(exitcode=0, stdout='')
    True
    >>> run('/bin/echo -n foo', captureStdout=True) == RunResult(exitcode=0, stdout='foo')
    True
    >>> run('/bin/echo -n foo', captureStdout=lambda s: s + 'X') == \
        RunResult(exitcode=0, stdout='fooX')
    True
    >>> run('/bin/echo foo', captureStdout=False) == RunResult(exitcode=0, stdout='')
    True
    >>> run('cat', captureStdout=True, input='blub') == RunResult(exitcode=0, stdout='blub')
    True
    >>> try:
    ...     run('false')
    ...     raise 'exception expected'
    ... except RunError:
    ...     pass
    ...
    >>> run('false', onError='ignore') == RunResult(exitcode=1, stdout='')
    True
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
    stdoutIsFileLike = type(captureStdout) == int or hasattr(captureStdout, 'write')
    stdoutIsProcFun = not stdoutIsFileLike and hasattr(captureStdout, '__call__')
    shouldReturnStdout = (stdoutIsProcFun or
                            (type(captureStdout) == bool and captureStdout))
    stdout = None
    if shouldReturnStdout:
        stdout = subprocess.PIPE
    elif stdoutIsFileLike:
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
    if input:
        input_str = '<' + str(len(input)) + ' characters>'
        if encoding != 'raw':
            input = input.encode(encoding)
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
    pipe = subprocess.Popen(
        cmd, shell=(type(cmd) == str),
        stdout=stdout, stdin=stdin, stderr=stderr,
        cwd=cwd, env=popenEnv
    )
    (stdoutData, stderrData) = pipe.communicate(input=input)
    if stdoutData is not None and encoding != 'raw':
        stdoutData = stdoutData.decode(encoding, errors=decodeErrorsStdout)
    if stderrData is not None and encoding != 'raw':
        stderrData = stderrData.decode(encoding, errors=decodeErrorsStderr)
    exitcode = pipe.returncode
    if onError == 'raise' and exitcode != 0:
        d = stderrData
        if stderrToStdout:
            d = stdoutData
        err = RunError(cmd, exitcode, d)
        raise err
    if onError == 'die' and exitcode != 0:
        sys.exit(exitcode)
    stdoutRes = stdoutData
    if stdoutRes is None:
        stdoutRes = ''
    if stdoutIsProcFun:
        stdoutRes = captureStdout(stdoutData)
    return RunResult(stdoutRes, exitcode)

# the quote function is stolen from https://hg.python.org/cpython/file/3.5/Lib/shlex.py
_find_unsafe = re.compile(r'[^\w@%+=:,./-]').search
def quote(s):
    """Return a shell-escaped version of the string `s`.
    """
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s
    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"

def listAsArgs(l):
    """
    Converts a list of command arguments to a single argument string.
    """
    return ' '.join([quote(x) for x in l])

def mergeDicts(*l):
    """
    Merges a list of dictionaries. Useful for e.g. merging environment dictionaries.
    """
    res = {}
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

def removeExt(p):
    """Removes the extension of a filename."""
    return splitext(p)[0]

def getExt(p):
    """Returns the extension of a filename."""
    return splitext(p)[1]

#: export
expandEnvVars = os.path.expandvars

#: export
pjoin = os.path.join

#: export
mv = os.rename

def removeFile(path):
    """
    Removes the given file. Throws an error if `path` is not a file.
    """
    if isFile(path):
        os.remove(path)
    else:
        raise ShellError(f"{path} is not a file")

def cp(src, target):
    """
    Copy `src` to `target`.

    * If `src` is a file and `target` is a file: overwrites `target`.
    * If `src` is a file and `target` is a dirname: places the copy in directory `target`,
      with the name of `src.
    * If `src` is a directory then `target` must also be a directory: copies
      the whole `src` directory to `target`.
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
        else:
            raise ValueError(f'Cannot copy directory {src} to non-directory {target}')

def abort(msg):
    """Print an error message and abort the shell script."""
    sys.stderr.write('ERROR: ' + msg + '\n')
    sys.exit(1)

def mkdir(d, mode=0o777, createParents=False):
    """
    Creates directory `d` with `mode`.
    """
    if createParents:
        os.makedirs(d, mode, exist_ok=True)
    else:
        os.mkdir(d, mode)

def touch(path):
    """
    Create an empty file at `path`.
    """
    run(['touch', path])

def cd(x):
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
    def __init__(self, new_dir):
        self.new_dir = new_dir
    def __enter__(self):
        self.old_dir = pwd()
        cd(self.new_dir)
    def __exit__(self, exc_type, value, traceback):
        cd(self.old_dir)
        return False # reraise expection

def rm(path):
    """
    Remove the file at `path`.
    """
    os.remove(path)

def rmdir(d, recursive=False):
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

    def exit(self, code=0):
        if code is None:
            myCode = 0
        elif type(code) != int:
            myCode = 1
        else:
            myCode = code
        self.exitCode = myCode
        self._origExit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc
        self._origExcHandler(exc_type, exc, *args)

    def isExitSuccess(self):
        return (self.exitCode is None or self.exitCode == 0) and self.exception is None

    def isExitFailure(self):
        return not self.isExitSuccess()

_hooks = _ExitHooks()
_hooks.hook()

def _registerAtExit(action, mode):
    def f():
        _debug(f'Running exit hook, exit code: {e}, mode: {mode}')
        if mode is True:
            action()
        elif mode in ['ifSuccess'] and _hooks.isExitSuccess():
            action()
        elif mode in ['ifFailure'] and _hooks.isExitFailure():
            action()
        else:
            _debug('Not running exit action')
    atexit.register(f)

def mkTempFile(suffix='', prefix='', dir=None, deleteAtExit=True):
    """Create a temporary file.

    `deleteAtExit` controls if and how the file is deleted once the shell sript terminates.
   It has one of the following values.

    * True: the file is deleted unconditionally on exit.
    * 'ifSuccess': the file is deleted if the program exists with code 0
    * 'ifFailure': the file is deleted if the program exists with code != 0
    """


    f = tempfile.mktemp(suffix, prefix, dir)
    if deleteAtExit:
        _registerAtExit(lambda: rm(f), deleteAtExit)
    return f

def mkTempDir(suffix='', prefix='tmp', dir=None, deleteAtExit=True):
    """Create a temporary directory. The `deleteAtExit` parameter
    has the same meaning as for `mkTempFile`.
    """
    d = tempfile.mkdtemp(suffix, prefix, dir)
    if deleteAtExit:
        _registerAtExit(lambda: rmdir(d, True), deleteAtExit)
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
    def __init__(self, suffix='', prefix='tmp', dir=None, onException=True, delete=True):
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
    def __exit__(self, exc_type, value, traceback):
        if exc_type is not None and not self.onException:
            return False # reraise
        if self.delete:
            rmdir(self.dir_to_delete, recursive=True)
        return False # reraise expection

def ls(d, *globs):
    """
    Returns a list of pathnames contained in `d`, matching any of the the given `globs`.

    If no globs are given, all files are returned.

    The pathnames in the result list contain the directory part `d`.

    >>> '../src/shell.py' in ls('../src/', '*.py', '*.txt')
    True
    """
    res = []
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

def readBinaryFile(name):
    """Return the binary content of file `name`."""
    with open(name, 'rb') as f:
        return f.read()

def readFile(name):
    """Return the textual content of file `name`."""
    with open(name, 'r', encoding='utf-8') as f:
        return f.read()

def writeFile(name, content):
    """Write text `content` to file `name`."""
    with open(name, 'w', encoding='utf-8') as f:
        f.write(content)

def writeBinaryFile(name, content):
    """Write binary string `content` to file `name`."""
    with open(name, 'wb') as f:
        f.write(content)

def _openForTee(x):
    if type(x) == str:
        return open(x, 'wb')
    elif type(x) == tuple:
        (name, mode) = x
        if mode == 'w':
            return open(name, 'wb')
        elif mode == 'a':
            return open(name, 'wa')
        raise ValueError(f'Bad mode: {mode}')
    elif x == TEE_STDERR:
        return sys.stderr
    elif x == TEE_STDOUT:
        return sys.stdout
    else:
        raise ValueError(f'Invalid file argument: {x}')

def _teeChildWorker(pRead, pWrite, fileNames, bufferSize):
    _debug('child of tee started')
    files = []
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

def _teeChild(pRead, pWrite, files, bufferSize):
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

def createTee(files, bufferSize=128):
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

def exit(code):
    """Exit the program with the given exit `code`.
    """
    sys.exit(code)

#: export
fileSize = os.path.getsize
