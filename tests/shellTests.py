import unittest
import shell
import time
import sys
from typing import *

class ShellTest(unittest.TestCase):

    def testTee(self):
        with shell.tempDir() as d:
            p1 = shell.pjoin(d, "f1.txt")
            p2 = shell.pjoin(d, "f2.txt")
            l: list[Any] = [p1, p2, shell.TEE_STDERR]
            with shell.createTee(l) as t:
                t.write('Hello World!')
            time.sleep(0.1)
            s1 = shell.readFile(p1)
            s2 = shell.readFile(p2)
            self.assertEqual('Hello World!', s1)
            self.assertEqual('Hello World!', s2)

    def testMv1(self):
        with shell.tempDir() as d:
            a = shell.pjoin(d, 'a')
            b = shell.pjoin(d, 'b')
            ax = shell.pjoin(a, 'x')
            shell.mkdir(a)
            shell.mkdir(b)
            shell.writeFile(ax, 'abc')
            shell.mv(ax, b)
            bx = shell.pjoin(b, 'x')
            self.assertEqual('abc', shell.readFile(bx))

    def testMv2(self):
        with shell.tempDir() as d:
            a = shell.pjoin(d, 'a')
            b = shell.pjoin(d, 'b')
            ax = shell.pjoin(a, 'x')
            bx = shell.pjoin(b, 'x')
            shell.mkdir(a)
            shell.mkdir(b)
            shell.writeFile(ax, 'abc')
            shell.mv(ax, bx)
            self.assertEqual('abc', shell.readFile(bx))

if __name__ == "__main__":
    print("Running doctests")
    import doctest
    r = doctest.testmod(m=shell, verbose=False)
    if r.failed > 0:
        print('At least one doctest failed')
        sys.exit(1)
    print("Running unittests")
    unittest.main(argv=['unused'], exit=True)
