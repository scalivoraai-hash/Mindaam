"""Offline asset admission regressions; no downloads or application state."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


prepare = module('prepare-whitehouse-character')
texture = module('texture-whitehouse-character')


class AssetAdmission(unittest.TestCase):
    def test_obj_quad_preserves_uv_seams_and_winding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'quad.obj'
            path.write_text('v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\ng body\nf 1/4 2/3 3/2 4/1\n')
            vertices, uv, faces = prepare.obj(path)
            self.assertEqual(len(vertices), 4)
            self.assertEqual(uv[0], [0, 0])
            self.assertEqual(faces, [('body', [(0,3),(1,2),(2,1)]), ('body', [(0,3),(2,1),(3,0)])])

    def test_source_changed_after_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = json.loads(Path(__file__).with_name('whitehouse-character-sources.json').read_text())
            first = next(iter(manifest['files']))
            path = root/first
            path.parent.mkdir(parents=True)
            path.write_text('unreviewed replacement')
            with self.assertRaisesRegex(ValueError, 'Unreviewed source asset'):
                prepare.main(root, root/'output.json')
            self.assertFalse((root/'output.json').exists())

    def test_invalid_glb_container_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'input.glb'
            path.write_bytes(struct.pack('<III', 0, 2, 12))
            with self.assertRaisesRegex(ValueError, 'Invalid GLB'):
                texture.embed(root, path, root/'output.glb')
            self.assertFalse((root/'output.glb').exists())

    def test_cc0_header_does_not_allow_changed_texture_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            licence = root/'selected/eyes/low-poly/low-poly.mhclo'
            licence.parent.mkdir(parents=True)
            licence.write_text('released as CC0')
            (root/'brown_eye.png').write_bytes(b'unreviewed texture')
            doc = json.dumps({'materials':[{'name':'eyes'}], 'buffers':[{'byteLength':0}], 'bufferViews':[]}).encode()
            doc += b' '*(-len(doc)%4)
            raw = struct.pack('<III',0x46546C67,2,28+len(doc))+struct.pack('<II',len(doc),0x4E4F534A)+doc+struct.pack('<II',0,0x004E4942)
            path = root/'input.glb'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'Unreviewed texture content'):
                texture.embed(root,path,root/'output.glb')
            self.assertFalse((root/'output.glb').exists())


if __name__ == '__main__':
    unittest.main()
