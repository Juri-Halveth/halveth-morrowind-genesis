import math
import unittest
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path
from scripts.visual_field import branches, build, ground_mesh, layout, time_projection
from scripts.preview_visual_field import assess


class VisualFieldTests(unittest.TestCase):
    def test_layout_is_centered_and_disjoint(self):
        for gap in (1600,2200,10000):
            positions=[layout(i,gap) for i in range(16)]
            self.assertEqual(len(set(positions)),16)
            self.assertEqual(tuple(sum(p[a] for p in positions) for a in range(3)),(0,0,0))
            self.assertGreaterEqual(min(math.dist(a,b) for i,a in enumerate(positions) for b in positions[i+1:]),gap)
        for index,gap in [(-1,2200),(16,2200),(True,2200),(0,float('nan')),(0,1599),(0,10001)]:
            with self.assertRaises(ValueError):layout(index,gap)

    def test_shared_ground_spans_all_display_positions(self):
        root=ET.fromstring(ground_mesh())
        ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
        raw=list(map(float,root.find('.//c:float_array',ns).text.split()))
        points=list(zip(raw[::3],raw[1::3],raw[2::3]))
        self.assertEqual(len(points),129)
        self.assertEqual({p[2] for p in points},{-2})
        self.assertTrue(all(math.hypot(*layout(i)[:2])+500<5500 for i in range(16)))
        self.assertEqual(len(root.findall('.//c:geometry',ns)),1)

    def test_reflection_is_exact_and_depth_bounded(self):
        for seed in range(16):
            for stage in range(5):
                crown,roots=branches(seed,stage)
                self.assertEqual(len(crown),2**(stage+1)-1)
                self.assertLessEqual(len(crown)+len(roots),62)
                self.assertEqual(crown,[(tuple((x,y,-z)),tuple((u,v,-w))) for (x,y,z),(u,v,w) in roots])
                self.assertTrue(all(p[2]>=0 for edge in crown for p in edge))
        self.assertNotEqual(branches(0,3),branches(1,3))

    def test_time_views_keep_endpoints_order_and_distinction(self):
        for mode in ('linear','log'):
            vals=[time_projection(t/100,mode) for t in range(101)]
            self.assertEqual(vals[0],0);self.assertEqual(vals[-1],1)
            self.assertEqual(vals,sorted(set(vals)))
        self.assertGreater(time_projection(.2,'log'),time_projection(.2,'linear'))
        for t,mode in [(-1,'log'),(1.1,'linear'),(float('inf'),'log'),(.5,'invalid')]:
            with self.assertRaises(ValueError):time_projection(t,mode)

    def test_actor_module_is_registered_and_old_tiles_are_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'field'
            receipt=build(output)
            self.assertIn('CUSTOM: scripts/halveth_visual_field/actor.lua',
                (output/'halveth-visual-field.omwscripts').read_text())
            self.assertTrue((output/'meshes/halveth/visual_field/ground.dae').is_file())
            self.assertFalse((output/'meshes/halveth/visual_field/platform.dae').exists())
            self.assertEqual(len(receipt['files']),86)
            with self.assertRaises(FileExistsError):build(output)

    def test_runtime_completion_requires_moving_actors_and_growth(self):
        lines=['HALVETH_FIELD_PAGE page=0 objects=16 entries=3563','HALVETH_FIELD_DONE']
        self.assertFalse(assess('\n'.join(lines),0)['passed'])
        lines += [f'HALVETH_FIELD_GROWTH stage={stage}' for stage in range(1,5)]
        lines += [f'HALVETH_FIELD_MOTION slot={slot} distance=3000' for slot in (1,2,3)]
        self.assertTrue(assess('\n'.join(lines),0)['passed'])
        self.assertFalse(assess('\n'.join(lines[:-1]),0)['passed'])
        self.assertFalse(assess('\n'.join(lines)+'\nERROR: failed',0)['passed'])
        self.assertFalse(assess('\n'.join(lines),1)['passed'])


if __name__=='__main__':unittest.main()
