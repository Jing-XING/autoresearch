from fractions import Fraction
from itertools import product
import unittest
from scripts.analyze_expansion_complete_sensitivity_v1 import exact_bootstrap


class BootstrapTests(unittest.TestCase):
    def test_matches_exhaustive_stratified_resampling(self):
        strata=[[-1,1,0],[1,0]];counts={};denominator=0
        for a in product(strata[0],repeat=3):
            for b in product(strata[1],repeat=2):
                total=sum(a)+sum(b);counts[total]=counts.get(total,0)+1;denominator+=1
        got=exact_bootstrap(strata)
        self.assertEqual({r['net_gain']:Fraction(r['probability']) for r in got['pmf']},
                         {k:Fraction(v,denominator) for k,v in counts.items()})

    def test_degenerate_pairs(self):
        self.assertEqual(exact_bootstrap([[0,0],[0]])['interval_percentage_points'],[0,0])
        self.assertEqual(exact_bootstrap([[1,1],[1]])['interval_percentage_points'],[100,100])


if __name__=='__main__':unittest.main()
