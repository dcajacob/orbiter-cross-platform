#!/usr/bin/env python3
"""Check numerical acceptance and corrupt-observation rejection."""
import copy
import csv
from pathlib import Path
import tempfile
import unittest

from capture import FIELDS, compare


class Comparison(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.rows = []
        for model, maximum in (('Earth', 65340), ('Moon', 13860)):
            for degree in (2, 4, 12, 32):
                for order in (0, degree//2, degree):
                    for _ in range(36):
                        self.rows.append([model, degree, order, len(self.rows), 560, maximum,
                                          7000, 0, 0, .001, -.002, .003])

    def write(self, name, rows):
        path = self.directory/name
        with path.open('w', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(FIELDS)
            writer.writerows(rows)
        return path

    def check(self, change, accepted):
        rows = copy.deepcopy(self.rows)
        change(rows)
        reference = self.write('reference.csv', self.rows)
        candidate = self.write('candidate.csv', rows)
        if accepted:
            self.assertEqual(compare(reference, candidate)['status'], 'passed')
        else:
            with self.assertRaises(ValueError):
                compare(reference, candidate)

    def test_absolute_floor_and_vector_norm(self):
        self.rows[0][9:] = [0, 0, 0]
        self.check(lambda rows: rows[0].__setitem__(9, .5e-12), True)
        # Every component fits the floor, but the vector does not.
        self.check(lambda rows: rows[0].__setitem__(slice(9, 12), [.8e-12]*3), False)

    def test_relative_budget(self):
        self.rows[0][9:] = [3000, 0, 0]
        self.check(lambda rows: rows[0].__setitem__(9, 3000+1e-8), True)
        self.check(lambda rows: rows[0].__setitem__(9, 3000+1e-6), False)

    def test_nonfinite_missing_or_changed_queries(self):
        self.check(lambda rows: rows[0].__setitem__(9, float('nan')), False)
        self.check(lambda rows: rows.pop(), False)
        self.check(lambda rows: rows[0].__setitem__(3, 999), False)
        self.check(lambda rows: rows[0].__setitem__(6, 7000.001), False)
        self.check(lambda rows: rows[0].append(99), False)


if __name__ == '__main__':
    unittest.main()
