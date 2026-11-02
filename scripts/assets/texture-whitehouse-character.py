"""Embed bounded, locally vetted CC0 textures into the development GLB.

No network access. The original material licence is checked for every pack image.
This does not publish the asset or make it an accepted runtime character.
"""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image


def embed(source, input_path, output):
    approved = json.loads(Path(__file__).with_name('whitehouse-character-sources.json').read_text())['files']
    raw = input_path.read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    if (magic, version, length) != (0x46546C67, 2, len(raw)):
        raise ValueError('Invalid GLB input')
    size, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A:
        raise ValueError('Missing JSON chunk')
    doc = json.loads(raw[20:20+size])
    binary_size, kind = struct.unpack_from('<II', raw, 20+size)
    if kind != 0x004E4942:
        raise ValueError('Missing geometry chunk')
    binary = bytearray(raw[28+size:28+size+binary_size])
    materials = {
        'skin': ('skins/young_caucasian_male2/young_lightskinned_male_diffuse2.png', 'skins/young_caucasian_male2/young_caucasian_male2.mhmat', 1024),
        'casual-clothing': ('clothes/male_casualsuit01/male_casualsuit01_diffuse.png', 'clothes/male_casualsuit01/male_casualsuit01.mhmat', 1024),
        'pants': ('clothes/male_casualsuit01/male_casualsuit01_diffuse.png', 'clothes/male_casualsuit01/male_casualsuit01.mhmat', 1024),
        'shoes': ('clothes/shoes02/shoes02_diffuse.png', 'clothes/shoes02/shoes02.mhmat', 512),
        'hair': ('hair/short02/short02_diffuse.png', 'hair/short02/short02.mhmat', 512),
        'eyes': ('../brown_eye.png', 'eyes/low-poly/low-poly.mhclo', 256),
    }
    doc['images'], doc['textures'] = [], []
    doc['samplers'] = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
    provenance = []
    cached = {}
    for material in doc['materials']:
        name = material['name']
        relative, licence, maximum = materials[name]
        if relative in cached:
            material['pbrMetallicRoughness']['baseColorFactor'] = [1, 1, 1, 1]
            material['pbrMetallicRoughness']['baseColorTexture'] = {'index': cached[relative]}
            continue
        if 'released as CC0' not in (source/'selected'/licence).read_text():
            raise ValueError('Unreviewed texture licence: ' + name)
        path = source/'selected'/relative
        source_key = str(path.resolve().relative_to(source.resolve()))
        if hashlib.sha256(path.read_bytes()).hexdigest() != approved.get(source_key):
            raise ValueError('Unreviewed texture content: ' + name)
        image = Image.open(path).convert('RGBA' if name == 'hair' else 'RGB')
        image.thumbnail((maximum, maximum), Image.Resampling.LANCZOS)
        # OBJ UVs use a lower-left origin; glTF embedded images use upper-left.
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        stream = io.BytesIO()
        image.save(stream, format='PNG' if name == 'hair' else 'JPEG', quality=85, optimize=True)
        payload = stream.getvalue()
        binary.extend(b'\0' * (-len(binary) % 4))
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload)})
        binary.extend(payload)
        index = len(doc['images'])
        cached[relative] = index
        doc['images'].append({'bufferView': view, 'mimeType': 'image/png' if name == 'hair' else 'image/jpeg'})
        doc['textures'].append({'source': index, 'sampler': 0})
        material['pbrMetallicRoughness']['baseColorFactor'] = [1, 1, 1, 1]
        material['pbrMetallicRoughness']['baseColorTexture'] = {'index': index}
        if name == 'hair':
            material.update(alphaMode='MASK', alphaCutoff=0.4, doubleSided=True)
        provenance.append({'material': name, 'source': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': list(image.size), 'bytes': len(payload), 'licence': 'CC0-1.0'})
    doc['buffers'][0]['byteLength'] = len(binary)
    doc.setdefault('extras', {})['textureProvenance'] = provenance
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    output.write_bytes(struct.pack('<III', magic, 2, 28+len(encoded)+len(binary)) + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + struct.pack('<II', len(binary), 0x004E4942) + binary)
    print(json.dumps({'bytes': output.stat().st_size, 'textures': provenance, 'status': 'development asset; not runtime accepted'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    embed(args.source, args.input, args.output)
