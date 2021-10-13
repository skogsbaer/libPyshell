import unittest
import shell
import time
import sys

class ShellTest(unittest.TestCase):

    def testTee(self):
        with shell.tempDir() as d:
            p1 = shell.pjoin(d, "f1.txt")
            p2 = shell.pjoin(d, "f2.txt")
            with shell.createTee([p1, p2, shell.TEE_STDERR]) as t:
                t.write('Hello World!')
            time.sleep(0.1)
            s1 = shell.readFile(p1)
            s2 = shell.readFile(p2)
            self.assertEqual('Hello World!', s1)
            self.assertEqual('Hello World!', s2)

if __name__ == "__main__":
    import doctest
    doctest.testmod(m=shell, verbose=False)
    print("Running unittests")
    unittest.main(argv=['unused'], exit=True)
