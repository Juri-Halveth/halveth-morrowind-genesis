import math
import unittest

from scripts.refine_morrowind_head import interpolate, topology, sculpt_point, sculpt_rest, validate_brushes


class HeadRefinementTests(unittest.TestCase):
    def test_sculpt_is_local_and_keeps_normals_valid(self):
        brushes = [{'center': [0, 0, 0], 'radius': [2, 2, 2], 'displacement': [0, .2, 0]}]
        self.assertEqual(sculpt_point((0, 0, 0), brushes), (0, .2, 0))
        self.assertEqual(sculpt_point((2, 0, 0), brushes), (2, 0, 0))
        self.assertEqual(sculpt_point((5, 0, 0), brushes), (5, 0, 0))
        points, normals = sculpt_rest([(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (0, 1, 0)], brushes)
        for n in normals:
            self.assertAlmostEqual(sum(x*x for x in n), 1)
        self.assertGreater(normals[1][0], 0)
        with self.assertRaises(ValueError):
            validate_brushes({'schemaVersion': 1, 'sourceSha256': 'wrong', 'brushes': brushes}, 'bound')
        with self.assertRaises(ValueError):
            validate_brushes({'schemaVersion': 1, 'sourceSha256': 'bound', 'brushes': [
                {'center': [0,0,0], 'radius': [0,1,1], 'displacement': [0,0,0]}]}, 'bound')

    def test_boundaries_stay_fixed_and_uvs_only_split(self):
        masks, uv_masks, triangles, boundary = topology(3, [(0, 1, 2)], 1.0)
        self.assertEqual(boundary, 3)
        self.assertEqual(masks[:3], [{0: 1.0}, {1: 1.0}, {2: 1.0}])
        self.assertEqual(len(triangles), 4)
        self.assertEqual(masks, uv_masks)

    def test_animation_blending_commutes_with_subdivision(self):
        # A tetrahedron has no boundary and genuinely curves during refinement.
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        base = [(0., 0., 0.), (2., 0., 0.), (0., 2., 0.), (0., 0., 2.)]
        delta = [(0., 0., 0.), (.4, -.2, .1), (0., .5, 0.), (0., 0., .7)]
        masks, _, triangles, boundary = topology(4, faces, .65)
        self.assertEqual((len(masks), len(triangles), boundary), (10, 16, 0))
        self.assertNotEqual(interpolate(base, masks)[0], base[0])
        for mask in masks:
            self.assertAlmostEqual(sum(mask.values()), 1.)
            self.assertGreaterEqual(min(mask.values()), 0.)
        for weight in (0., .3, 1.):
            animated = [tuple(x + weight * y for x, y in zip(a, b)) for a, b in zip(base, delta)]
            actual = interpolate(animated, masks)
            expected = [tuple(x + weight * y for x, y in zip(a, b))
                        for a, b in zip(interpolate(base, masks), interpolate(delta, masks))]
            for a, b in zip(actual, expected):
                for x, y in zip(a, b):
                    self.assertAlmostEqual(x, y)

    def test_invalid_topology_and_nonfinite_input_are_rejected(self):
        for faces in ([(0, 0, 1)], [(0, 1, 8)], [(0, 1, 2), (2, 1, 0)],
                      [(0, 1, 2), (1, 0, 3), (0, 1, 4)]):
            with self.assertRaises(ValueError):
                topology(5, faces, .65)
        for strength in (-1, 2, math.nan, math.inf):
            with self.assertRaises(ValueError):
                topology(3, [(0, 1, 2)], strength)
        with self.assertRaises(ValueError):
            interpolate([(math.nan, 0, 0)], [{0: 1}])


if __name__ == '__main__':
    unittest.main()
