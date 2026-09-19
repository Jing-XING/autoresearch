import numpy as np
import unittest

from autolab.risk_development import Difference, Uniform, evaluate
from scripts.analyze_risk_median_objective_v1 import compare, sampled_components


def test_error_components_match_label_query_driver():
    target=np.array([[.2,.8],[.7,.3],[.6,.4],[.9,.1],[.3,.7],[.45,.55]])
    surrogate=np.array([[.4,.6],[.5,.5],[.8,.2],[.7,.3],[.4,.6],[.1,.9]])
    labels=np.array([0,0,1,1,1,0])
    logs=-np.log(target);loss=logs[np.arange(6),labels];proxy=(logs*surrogate).sum(1)
    for seed in range(5):
        for budget in (1,3,6):
            a,b=sampled_components(loss,proxy,budget,seed)
            for factory,c in ((Uniform,0),(Difference,1)):
                r=evaluate(factory,target,surrogate,labels,budget,seed)
                assert r['status']=='ok'
                assert abs(a+c*b-(r['estimate']-r['true_risk'])) < 1e-14


def test_evaluation_block_does_not_choose_coefficient():
    x=np.array([[[1.,-1.],[1.,-1.],[1.,-1.]],[[2.,-1.],[2.,-1.],[2.,-1.]]])
    result=compare(x,[0,1,2],.5)
    assert result['selected_coefficient']==1
    assert result['controls']['selected_grid']['median_squared_error']==[0,1]
    assert result['controls']['selected_grid']['ratio_to_uniform']==[0,.25]
    x[1,:,0]=3
    assert compare(x,[0,1,2],.5)['selected_coefficient']==1
    tied=np.array([[[1.,0.],[1.,0.]],[[1.,0.],[1.,0.]]])
    assert compare(tied,[0,1,2],1)['selected_coefficient']==0


class MedianObjectiveTests(unittest.TestCase):
    def test_driver(self):
        test_error_components_match_label_query_driver()

    def test_selection(self):
        test_evaluation_block_does_not_choose_coefficient()


if __name__ == "__main__":
    unittest.main()
