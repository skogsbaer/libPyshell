Module shell
============
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

Assumes Python 3.

Variables
---------

    
`HOME`
:   The value of the environment variable `HOME`

    
`TEE_STDERR`
:   Special value for `createTee`.

    
`TEE_STDOUT`
:   Special value for `createTee`.

    
`THIS_DIR`
:   The directory where the script is located.

Functions
---------

    
`abort(msg)`
:   Print an error message and abort the shell script.

    
`abspath(path)`
:   Return an absolute path.

    
`basename(p)`
:   Returns the final component of a pathname

    
`cd(x)`
:   Changes the working directory.

    
`cp(src, target)`
:   Copy `src` to `target`.
    
    * If `src` is a file and `target` is a file: overwrites `target`.
    * If `src` is a file and `target` is a dirname: places the copy in directory `target`,
      with the name of `src.
    * If `src` is a directory then `target` must also be a directory: copies
      the whole `src` directory to `target`.

    
`createTee(files, bufferSize=128)`
:   Get a file object that will mirror writes across multiple files.
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

    
`dirname(p)`
:   Returns the directory component of a pathname

    
`exists(path)`
:   Test whether a path exists.  Returns False for broken symbolic links

    
`exit(code)`
:   Exit the program with the given exit `code`.

    
`expandEnvVars(path)`
:   Expand shell variables of form $var and ${var}.  Unknown variables
    are left unchanged.

    
`fatal(s)`
:   Display an error message to stderr.

    
`fileSize(filename)`
:   Return the size of a file, reported by os.stat().

    
`filename(p)`
:   Returns the final component of a pathname

    
`getExt(p)`
:   Returns the extension of a filename.

    
`gnuProg(p)`
:   Get the GNU version of progam p.

    
`isDir(s)`
:   Return true if the pathname refers to an existing directory.

    
`isFile(path)`
:   Test whether a path is a regular file

    
`isLink(path)`
:   Test whether a path is a symbolic link

    
`listAsArgs(l)`
:   Converts a list of command arguments to a single argument string.

    
`ls(d, *globs)`
:   Returns a list of pathnames contained in `d`, matching any of the the given `globs`.
    
    If no globs are given, all files are returned.
    
    The pathnames in the result list contain the directory part `d`.
    
    >>> '../src/shell.py' in ls('../src/', '*.py', '*.txt')
    True

    
`mergeDicts(*l)`
:   Merges a list of dictionaries. Useful for e.g. merging environment dictionaries.

    
`mkTempDir(suffix='', prefix='tmp', dir=None, deleteAtExit=True)`
:   Create a temporary directory. The `deleteAtExit` parameter
    has the same meaning as for `mkTempFile`.

    
`mkTempFile(suffix='', prefix='', dir=None, deleteAtExit=True)`
:   Create a temporary file.
    
     `deleteAtExit` controls if and how the file is deleted once the shell sript terminates.
    It has one of the following values.
    
     * True: the file is deleted unconditionally on exit.
     * 'ifSuccess': the file is deleted if the program exists with code 0
     * 'ifFailure': the file is deleted if the program exists with code != 0

    
`mkdir(d, mode=511, createParents=False)`
:   Creates directory `d` with `mode`.

    
`mv(src, dst, *, src_dir_fd=None, dst_dir_fd=None)`
:   Rename a file or directory.
    
    If either src_dir_fd or dst_dir_fd is not None, it should be a file
      descriptor open to a directory, and the respective path string (src or dst)
      should be relative; the path will then be relative to that directory.
    src_dir_fd and dst_dir_fd, may not be implemented on your platform.
      If they are unavailable, using them will raise a NotImplementedError.

    
`pjoin(a, *p)`
:   Join two or more pathname components, inserting '/' as needed.
    If any component is an absolute path, all previous path components
    will be discarded.  An empty last part will result in a path that
    ends with a separator.

    
`pwd()`
:   Return the current working directory.

    
`quote(s)`
:   Return a shell-escaped version of the string `s`.

    
`readBinaryFile(name)`
:   Return the binary content of file `name`.

    
`readFile(name)`
:   Return the textual content of file `name`.

    
`removeExt(p)`
:   Removes the extension of a filename.

    
`removeFile(path)`
:   Removes the given file. Throws an error if `path` is not a file.

    
`resolveProg(*l)`
:   Return the first program in the list that exist and is runnable.
    >>> resolveProg()
    >>> resolveProg('foobarbaz', 'python', 'grep')
    'python'
    >>> resolveProg('foobarbaz', 'padauz')

    
`rm(path)`
:   Remove the file at `path`.

    
`rmdir(d, recursive=False)`
:   Remove directory `d`. Set `recursive=True` if the directory is not empty.

    
`run(cmd: Union[str, list[str]], onError: Literal['raise', 'die', 'ignore'] = 'raise', input: Optional[str] = None, encoding: str = 'utf-8', captureStdout: Union[bool, Callable, TextIO, BinaryIO] = False, captureStderr: bool = False, stderrToStdout: bool = False, cwd: Optional[str] = None, env: Optional[dict] = None, freshEnv: Optional[dict] = None, decodeErrors: Literal['strict', 'ignore', 'replace'] = 'replace', decodeErrorsStdout: Optional[Literal['strict', 'ignore', 'replace']] = None, decodeErrorsStderr: Optional[Literal['strict', 'ignore', 'replace']] = None)`
:   Runs the given command.
    
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
    >>> run('/bin/echo -n foo', captureStdout=lambda s: s + 'X') ==         RunResult(exitcode=0, stdout='fooX')
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

    
`splitExt(p)`
:   Split the extension from a pathname.
    
    Extension is everything from the last dot to the end, ignoring
    leading dots.  Returns "(root, ext)"; ext may be empty.

    
`splitLines(s)`
:   Split on line endings.
    To be used with the `captureStdout` or `captureStderr` parameter
    of `run`.

    
`splitOn(splitter)`
:   Return a function that splits a string on the given splitter string.
    
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

    
`touch(path)`
:   Create an empty file at `path`.

    
`writeBinaryFile(name, content)`
:   Write binary string `content` to file `name`.

    
`writeFile(name, content)`
:   Write text `content` to file `name`.

Classes
-------

`RunError(cmd, exitcode, stderr=None)`
:   This exception is thrown if a program invoked with `run(onError='raise')`
    returns a non-zero exit code.
    
    Attributes:
    
    * `exitcode`
    * `stderr`: output on stderr (if `run` configured to capture this output)

    ### Ancestors (in MRO)

    * shell.ShellError
    * builtins.BaseException

`RunResult(stdout, exitcode)`
:   Represents the result of running a program using the `run` function.
    Attribute `exitcode` holds the exit code,
    attribute `stdout` contains the output printed in stdout (only if `run`
    was invoked with `captureStdout=True`).

`ShellError(msg)`
:   The base class for exceptions thrown by this module.

    ### Ancestors (in MRO)

    * builtins.BaseException

    ### Descendants

    * shell.RunError

`tempDir(suffix='', prefix='tmp', dir=None, onException=True, delete=True)`
:   Scoped creation of a temporary directory, to be used in a `with`-block:
    
    ```
    with tempDir() as d:
        # do something with d
    # d gets deleted at the end of the with-block
    ```
    
    Per default, the temporary directory is deleted at the end of the `with`-block.
    With `delete=False`, deletion is deactivated. With `onException=False`, deletion
    is only performed if the `with`-block finishes without an exception.

`workingDir(new_dir)`
:   Scoped change of working directory, to be used in a `with`-block:
    
    ```
    with workingDir(path):
        # working directory is now path
    # previous working directory is restored
    ```
