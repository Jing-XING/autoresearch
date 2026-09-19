from types import SimpleNamespace
import unittest
from autolab.local_smoke import LocalTransformersModel, loading_options


class PlacementTests(unittest.TestCase):
    def test_no_silent_fallback_from_two_gpu_registration(self):
        for count in (0, 1, 3, 4):
            with self.assertRaises(ValueError):
                loading_options('two_gpu_balanced', count)
        options = loading_options('two_gpu_balanced', 2)
        self.assertEqual(options['max_memory']['cpu'], 0)
        self.assertEqual(set(options['max_memory']), {0, 1, 'cpu'})

    def test_timing_waits_for_both_devices(self):
        synced = []
        model = object.__new__(LocalTransformersModel)
        model.cuda_devices = (0, 1)
        model.torch = SimpleNamespace(cuda=SimpleNamespace(synchronize=synced.append))
        model.synchronize()
        self.assertEqual(synced, [0, 1])

    def test_original_placement_stays_on_gpu_zero(self):
        self.assertEqual(loading_options('single_gpu', 4), {'device_map': 'cuda:0'})


if __name__ == '__main__':
    unittest.main()
