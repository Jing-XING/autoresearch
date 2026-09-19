"""Check finite-population MSE against every possible sampled subset."""
from itertools import combinations
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_risk_linear_headroom_v1 import moments


def test_exact_mse_against_all_subsets():
    for losses,proxy in [([1.,4.,2.,8.],[0.,1.,3.,2.]),
                         ([1.,4.,2.,8.],[1.,1.,1.,1.]),
                         ([1.,4.,2.,8.],[2.,8.,4.,16.]),
                         ([1.,4.,2.,8.],[-1.,-4.,-2.,-8.])]:
        m=moments(losses,proxy);n=len(losses)
        for b in range(1,n+1):
            for name,c in [('uniform',0),('difference',1),('oracle',m['oracle_coefficient'])]:
                errors=[]
                for subset in combinations(range(n),b):
                    estimate=sum(losses[i] for i in subset)/b+c*(sum(proxy)/n-sum(proxy[i] for i in subset)/b)
                    errors.append((estimate-sum(losses)/n)**2)
                actual=sum(errors)/len(errors)
                expected=(1-b/n)*m['residual_variances'][name]/b
                assert math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12)
        assert m['mse_ratios']['oracle'] <= min(1,m['mse_ratios']['difference'])+1e-12


def test_oracle_unavailable_information_and_degenerate_proxy():
    # These full-population examples check algebra, not a budgeted estimator.
    assert moments([1.,2.,3.],[4.,4.,4.])['oracle_coefficient']==0
    m=moments([1.,2.,3.],[2.,4.,6.])
    assert m['oracle_coefficient']==0.5 and m['mse_ratios']['oracle']==0
    assert moments([1.,2.,3.],[-1.,-2.,-3.])['oracle_coefficient']==-1
