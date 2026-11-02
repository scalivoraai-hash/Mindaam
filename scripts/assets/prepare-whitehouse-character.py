"""Prepare vetted CC0 MakeHuman data for the staging character renderer.

Offline conversion only. No upstream source code is imported or executed.
Input: original base.obj/default rig/weights and selected CC0 system assets.
Output: intermediate skinned geometry, not a deployable/accepted character.
"""
import argparse, collections, hashlib, json, math, re
from pathlib import Path

CORE={'base.obj':'8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c',
      'default.mhskel':'99f179bce0aa850b45d4191a1d0d234c5851f881c057439470ded3bddf729a24',
      'default_weights.mhw':'0f3641d651ae3d00ad6b4ccee43142edb109d3bd909d27d9e4139ef1beed8625'}


def obj(path):
    vertices,uv,faces=[],[],[];group=''
    for line in path.read_text().splitlines():
        row=line.split()
        if not row:continue
        if row[0]=='v':vertices.append(list(map(float,row[1:4])))
        elif row[0]=='vt':uv.append(list(map(float,row[1:3])))
        elif row[0]=='g':group=row[1]
        elif row[0]=='f':
            corners=[tuple(int(n)-1 for n in value.split('/')[:2]) for value in row[1:]]
            faces.extend((group,[corners[0],corners[i],corners[i+1]]) for i in range(1,len(corners)-1))
    return vertices,uv,faces


def main(source,output):
    manifest=json.loads(Path(__file__).with_name('whitehouse-character-sources.json').read_text())
    for relative,expected in manifest['files'].items():
        if hashlib.sha256((source/relative).read_bytes()).hexdigest()!=expected:raise ValueError('Unreviewed source asset: '+relative)
    for name,expected in CORE.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=expected:raise ValueError('Unreviewed core asset: '+name)
    base,base_uv,base_faces=obj(source/'base.obj')
    rig=json.loads((source/'default.mhskel').read_text());weights=json.loads((source/'default_weights.mhw').read_text())
    if rig['license']!='CC0' or weights['license']!='CC0':raise ValueError('Unexpected asset licence')
    keep={'root','head','neck01',*[f'spine0{i}' for i in range(1,6)]}
    keep.update(f'{name}.{side}' for side in ['L','R'] for name in ['clavicle','upperarm01','lowerarm01','wrist','upperleg01','lowerleg01','foot'])
    def ancestor(name):
        while name and name not in keep:name=rig['bones'][name]['parent']
        return name or 'root'
    names=sorted(keep);index={name:i for i,name in enumerate(names)}
    heads={name:[sum(base[i][axis] for i in rig['joints'][rig['bones'][name]['head']])/len(rig['joints'][rig['bones'][name]['head']]) for axis in range(3)] for name in names}
    influences=[collections.defaultdict(float) for _ in base]
    for name,items in weights['weights'].items():
        target=index[ancestor(name)]
        for vertex,weight in items:influences[vertex][target]+=weight
    min_y=min(base[c[0]][1] for g,f in base_faces if g=='body' for c in f)
    max_y=max(base[c[0]][1] for g,f in base_faces if g=='body' for c in f)
    scale=2.3/(max_y-min_y)
    def transform(p):return [round(p[0]*scale,7),round((p[1]-min_y)*scale,7),round(p[2]*scale,7)]
    def skin(values):
        values=sorted(((i,max(0,w)) for i,w in values.items()),key=lambda row:-row[1])[:4]
        total=sum(w for _,w in values)
        if total<=0:values=[(index['root'],1)];total=1
        return [i for i,_ in values]+[0]*(4-len(values)),[round(w/total,7) for _,w in values]+[0]*(4-len(values))
    meshes=[];hidden=set();provenance=[]
    def proxy(relative,semantic):
        path=source/'selected'/relative;raw=path.read_text()
        if 'released as CC0' not in raw:raise ValueError('Unreviewed garment licence')
        lines=raw.splitlines();factors=[1.,1.,1.];mapping=[];section='';obj_file=''
        for line in lines:
            row=line.split()
            if not row or row[0].startswith('#'):continue
            if row[0]=='obj_file':obj_file=row[1]
            if row[0] in ['x_scale','y_scale','z_scale']:
                axis='xyz'.index(row[0][0]);factors[axis]=abs(base[int(row[1])][axis]-base[int(row[2])][axis])/float(row[3])
            if row[0]=='verts':section='verts';continue
            if row[0]=='delete_verts':section='delete';continue
            if section=='verts' and row[0].isdigit():
                if len(row)==1:mapping.append(([int(row[0])],[1.],[0.,0.,0.]))
                elif len(row)==9:mapping.append((list(map(int,row[:3])),list(map(float,row[3:6])),list(map(float,row[6:9]))))
                else:raise ValueError('Unsupported proxy mapping')
        if '\ndelete_verts\n' in raw:
            tokens=raw.split('\ndelete_verts\n',1)[1].split();i=0
            while i<len(tokens):
                start=int(tokens[i]);i+=1;end=start
                if i<len(tokens) and tokens[i]=='-':end=int(tokens[i+1]);i+=2
                hidden.update(range(start,end+1))
        original,uv,faces=obj(path.parent/obj_file)
        if len(mapping)!=len(original):raise ValueError('Proxy mapping/mesh vertex mismatch')
        positions=[];weighted=[]
        for ids,amounts,offset in mapping:
            positions.append([sum(base[i][axis]*w for i,w in zip(ids,amounts))+offset[axis]*factors[axis] for axis in range(3)])
            values=collections.defaultdict(float)
            for i,w in zip(ids,amounts):
                for bone,weight in influences[i].items():values[bone]+=weight*w
            weighted.append(values)
        if semantic=='shoes':
            # This wardrobe pairs long trousers with low shoes. The source shoe's
            # concealed ankle upper protrudes through the narrower trouser cuff.
            # Remove only faces entirely above the covered 19 cm ankle region;
            # retain the sole, toe, heel and boundary-crossing faces.
            faces=[(group,face) for group,face in faces if not all(transform(positions[c[0]])[1]>.19 for c in face)]
        if semantic=='casual-clothing':
            # Partition the existing outfit at its waist; no faces are duplicated
            # or removed. Independent material names preserve shirt/pants colours.
            trousers=[];shirt=[]
            for group,face in faces:
                (trousers if sum(transform(positions[c[0]])[1] for c in face)/3<1.19 else shirt).append((group,face))
            emit('casual-clothing',positions,uv,shirt,weighted)
            emit('pants',positions,uv,trousers,weighted)
        else:emit(semantic,positions,uv,faces,weighted)
        for p in [path,path.parent/obj_file]:provenance.append({'file':str(p.relative_to(source)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'licence':'CC0-1.0'})
    def emit(name,vertices,uv,faces,weighted):
        meshes.append({'name':name,'positions':[transform(p) for p in vertices],'uv':uv,'triangles':[[list(c) for c in f] for _,f in faces],
                       'joints':[skin(w)[0] for w in weighted],'weights':[skin(w)[1] for w in weighted]})
    proxy('clothes/male_casualsuit01/male_casualsuit01.mhclo','casual-clothing')
    proxy('clothes/shoes02/shoes02.mhclo','shoes')
    proxy('hair/short02/short02.mhclo','hair')
    proxy('eyes/low-poly/low-poly.mhclo','eyes')
    body=[(g,f) for g,f in base_faces if g=='body' and not any(c[0] in hidden for c in f)]
    emit('skin',base,base_uv,body,influences)
    bones=[]
    for name in names:
        parent=rig['bones'][name]['parent'];parent=ancestor(parent) if parent else None
        bones.append({'name':name,'parent':index[parent] if parent else None,'position':transform(heads[name])})
    result={'status':'UNVERIFIED INTERMEDIATE — not a release asset','licence':'CC0-1.0','source':'MakeHuman Community core assets; no MakeHuman program code',
            'height':2.3,'bones':bones,'meshes':meshes,'provenance':provenance,'core_sha256':CORE}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'bones':len(bones),'triangles':{m['name']:len(m['triangles']) for m in meshes},'bytes':output.stat().st_size}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();main(args.source,args.output)
