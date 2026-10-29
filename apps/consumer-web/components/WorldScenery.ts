import * as T from 'three';
import {architectureRegion,regionalPalette} from '../lib/cityArchitecture';
import {buildingStyle} from '../lib/buildingStyle';
import {box, material, mesh, oval} from './WorldAssets';

type Feature={id:string;tags:Record<string,string>;points:number[][];holes?:number[][][]};
type Geography={features:Feature[];spawn:number[]};
const palettes=[
  {wall:'#e9dcc7',trim:'#f8eddc',roof:'#4c5965',accent:'#234e51'},
  {wall:'#bd8d74',trim:'#e9d4bb',roof:'#574e53',accent:'#344d6b'},
  {wall:'#d1d9d8',trim:'#f0f0df',roof:'#59636e',accent:'#345d58'},
  {wall:'#c8bca7',trim:'#f4e9d2',roof:'#64544f',accent:'#594871'},
  {wall:'#eed7bd',trim:'#fff1d8',roof:'#775e55',accent:'#255c64'},
  {wall:'#dcbda6',trim:'#f5e2c5',roof:'#5d6470',accent:'#536458'},
  {wall:'#c1ced0',trim:'#e5eef0',roof:'#344251',accent:'#314f6a'},
  {wall:'#d4cbc2',trim:'#f1e9db',roof:'#765650',accent:'#674c54'},
];
const distance=(a:number[],b:number[])=>Math.hypot(a[0]-b[0],a[1]-b[1]);
const hash=(id:string)=>Array.from(id).reduce((h,c)=>(h*31+c.charCodeAt(0))>>>0,7);

/** Fixed-size atlases and shared materials, batched by the existing world tile renderer. */
export function buildCityEnvironment(parent:T.Group,geo:Geography,city=''){
  const region=architectureRegion(city);
  const textures:T.Texture[]=[],materials:T.Material[]=[],buildings:T.Group[]=[];
  function atlas(index:number){
    const p={wall:'#ffffff',trim:'#f0f0ec'},canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;
    const c=canvas.getContext('2d')!;c.fillStyle=p.wall;c.fillRect(0,0,256,256);
    // Deterministic original masonry variation. No fetched or traced map imagery.
    if(index!==2){for(let row=0;row<16;row++)for(let col=-1;col<9;col++){const shade=(row*17+col*31+index*11)%7;c.fillStyle=`rgba(90,70,50,${.025+Math.abs(shade)*.008})`;c.fillRect(col*32+(row%2)*16+1,row*16+1,30,14)}}
    // Shallow masonry joints, lintels and shaded glazed recesses.
    c.strokeStyle='#49352816';c.lineWidth=1;
    for(let y=0;y<256;y+=16){c.beginPath();c.moveTo(0,y);c.lineTo(256,y);c.stroke();for(let x=(y%32?16:0);x<256;x+=32){c.beginPath();c.moveTo(x,y);c.lineTo(x,y+16);c.stroke()}}
    c.fillStyle='#3e465320';c.fillRect(0,245,256,7);c.fillStyle=p.trim;c.fillRect(0,250,256,6);
    for(const x of index===2?[6,132]:index===3?[57]:[25,151]){
      c.fillStyle='#28333955';c.fillRect(x-5,35,84,160);
      c.fillStyle=p.trim;c.fillRect(x-8,29,88,8);c.fillRect(x-8,190,88,10);
      const reflection=c.createLinearGradient(x,40,x+72,190);reflection.addColorStop(0,'#b8d7dd');reflection.addColorStop(.45,'#4d7789');reflection.addColorStop(.5,'#3c6074');reflection.addColorStop(1,'#253d53');
      c.fillStyle=reflection;c.fillRect(x,index===1?60:42,index===2?114:67,index===1?113:144);
      c.fillStyle='#eaf6ee25';c.beginPath();c.moveTo(x,42);c.lineTo(x+36,42);c.lineTo(x,150);c.fill();
      c.fillStyle='#13233138';c.fillRect(x+3,49,4,132);c.fillStyle=p.trim;c.fillRect(x+31,42,4,144);c.fillRect(x,114,67,4);
      c.fillStyle='#1b26344d';c.fillRect(x,42,67,8);
    }
    if(index===1){c.fillStyle='#485766';c.fillRect(15,174,220,8);c.fillStyle='#c3cfcd';c.fillRect(15,184,220,6)}
    if(index===3){c.fillStyle='#e6e6e2';c.fillRect(0,205,256,42);for(let x=0;x<256;x+=16){c.fillStyle='#c2c5c4';c.fillRect(x,0,2,256)}}
    const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;texture.wrapS=texture.wrapT=T.RepeatWrapping;texture.anisotropy=4;textures.push(texture);
    const mat=new T.MeshStandardMaterial({map:texture,roughness:index===2?.35:.79,metalness:index===2?.2:0,vertexColors:true});materials.push(mat);return mat;
  }
  const facades=[0,1,2,3].map(atlas);
  const glass=new T.MeshStandardMaterial({color:'#40677e',metalness:.32,roughness:.24});materials.push(glass);
  const asphaltCanvas=document.createElement('canvas');asphaltCanvas.width=asphaltCanvas.height=128;
  const ac=asphaltCanvas.getContext('2d')!;ac.fillStyle='#303a46';ac.fillRect(0,0,128,128);
  let seed=19;for(let i=0;i<1600;i++){seed=(seed*1664525+1013904223)>>>0;const x=seed%128;seed=(seed*1664525+1013904223)>>>0;ac.fillStyle=i%2?'#ffffff04':'#00000004';ac.fillRect(x,seed%128,1,1)}
  const asphaltTex=new T.CanvasTexture(asphaltCanvas);asphaltTex.colorSpace=T.SRGBColorSpace;asphaltTex.wrapS=asphaltTex.wrapT=T.RepeatWrapping;asphaltTex.repeat.set(2,8);textures.push(asphaltTex);
  const asphalt=new T.MeshStandardMaterial({map:asphaltTex,roughness:.96});materials.push(asphalt);
  const shapeFor=(f:Feature,c=[0,0])=>{const shape=new T.Shape(f.points.map(p=>new T.Vector2(p[0]-c[0],-(p[1]-c[1]))));for(const hole of f.holes||[])shape.holes.push(new T.Path(hole.map(p=>new T.Vector2(p[0]-c[0],-(p[1]-c[1])))));return shape};
  const roadStrip=(a:number[],b:number[],width:number,y:number,mat:T.Material,height=.08)=>{
    const length=distance(a,b);if(length<.01)return;
    const m=new T.Mesh(new T.BoxGeometry(width,height,length+.12),mat);m.position.set((a[0]+b[0])/2,y,(a[1]+b[1])/2);m.rotation.y=Math.atan2(b[0]-a[0],b[1]-a[1]);m.receiveShadow=true;parent.add(m);return m;
  };
  for(const f of geo.features){
    if(f.tags.highway==='traffic_signals'&&f.points.length===1){const [x,z]=f.points[0],g=new T.Group();g.position.set(x,0,z);parent.add(g);mesh(new T.CylinderGeometry(.07,.09,3.3,8),'#334b55',g,0,1.65,0);box(g,'#20343e',0,3.02,0,.31,.91,.24);for(const [i,c] of ['#ed796f','#bfaa62','#88b6a1'].entries())oval(g,c,0,3.31-i*.28,.127,.082,.082,.02)}
    if(f.points.length<2)continue;
    if(f.tags.natural==='water'||['park','playground','pitch','garden'].includes(f.tags.leisure)){
      const colour=f.tags.natural==='water'?'#559da9':f.tags.leisure==='pitch'?'#608c74':f.tags.leisure==='playground'?'#c9a77b':'#72976e';
      const m=mesh(new T.ShapeGeometry(shapeFor(f)),colour,parent,0,.01,0);m.rotation.x=-Math.PI/2;m.userData.grassSurface=f.tags.natural!=='water'&&f.tags.leisure!=='playground';
    }
    if(!f.tags.highway)continue;
    const foot=['footway','pedestrian','path','steps','cycleway'].includes(f.tags.highway);
    for(let i=1;i<f.points.length;i++){
      const a=f.points[i-1],b=f.points[i],len=distance(a,b);if(len<.1)continue;
      const nx=(b[1]-a[1])/len,nz=-(b[0]-a[0])/len,angle=Math.atan2(b[0]-a[0],b[1]-a[1]);
      if(foot&&(f.tags.footway==='crossing'||f.tags.crossing)){for(let k=.6;k<len;k+=1.1){const m=box(parent,'#f5efdd',a[0]+(b[0]-a[0])*k/len,.226,a[1]+(b[1]-a[1])*k/len,2.8,.022,.52);m.rotation.y=angle}continue}
      roadStrip(a,b,foot?4.6:12,foot?.08:.025,material('#b9bbaf'),foot?.15:.04);
      if(foot)continue;
      roadStrip(a,b,7,.09,asphalt,.08);
      // Kerbs keep the existing traversable road/pavement widths exactly intact.
      for(const side of [-1,1]){
        const shift=(p:number[])=>[p[0]+nx*3.6*side,p[1]+nz*3.6*side];
        roadStrip(shift(a),shift(b),.18,.16,material('#e4ddce'),.19);const pavement=(p:number[])=>[p[0]+nx*4.8*side,p[1]+nz*4.8*side];roadStrip(pavement(a),pavement(b),2.2,.14,material('#b9bbaf'),.13);
        for(let k=3;k<len;k+=3){const x=a[0]+(b[0]-a[0])*k/len+nx*4.8*side,z=a[1]+(b[1]-a[1])*k/len+nz*4.8*side;const seam=box(parent,'#a9a799',x,.211,z,2.2,.01,.025);seam.rotation.y=angle}
      }
      for(let k=4;k<len;k+=8){const m=box(parent,region==='north-american'?'#d9bc72':'#f3ecd8',a[0]+(b[0]-a[0])*k/len,.146,a[1]+(b[1]-a[1])*k/len,.13,.018,3);m.rotation.y=angle}
      // Crossing marks appear only where the licensed map explicitly marks a crossing.
      if(f.tags.footway==='crossing'||f.tags.crossing){for(let k=-3;k<=3;k++){const m=box(parent,'#f5efdd',a[0]+nx*k,.16,a[1]+nz*k,.55,.02,2.8);m.rotation.y=angle}}
    }
  }
  let details=0;
  for(const f of geo.features){
    if(!f.tags.building||f.points.length<4)continue;
    const points=f.points.slice(0,-1),c=points.reduce((v,p)=>[v[0]+p[0]/points.length,v[1]+p[1]/points.length],[0,0]);
    const style=buildingStyle(f.tags,f.id),n=style.hash,palette=regionalPalette(city,style.palette,palettes[style.palette],f.tags),height=style.height;
    if(region==='gulf'&&!f.tags['roof:shape'])style.roof='flat';
    const group=new T.Group();group.position.set(c[0],0,c[1]);parent.add(group);buildings.push(group);
    const shape=shapeFor(f,c),positions:number[]=[],uvs:number[]=[];
    for(const ring of [f.points,...(f.holes||[])]){
      const area=ring.slice(0,-1).reduce((sum,p,i)=>sum+p[0]*ring[i+1][1]-ring[i+1][0]*p[1],0);
      for(let i=1;i<ring.length;i++){
        let a=ring[i-1],b=ring[i];if((area>0)===(ring===f.points)){const swap=a;a=b;b=swap}
        const bay=style.family==='home'?(f.tags.building==='terrace'?3.7:4.8):style.family==='office'?4.1:5.6,u=distance(a,b)/bay;
        positions.push(a[0]-c[0],0,a[1]-c[1],b[0]-c[0],0,b[1]-c[1],b[0]-c[0],height,b[1]-c[1],a[0]-c[0],0,a[1]-c[1],b[0]-c[0],height,b[1]-c[1],a[0]-c[0],height,a[1]-c[1]);
        uvs.push(0,0,u,0,u,height/3.1,0,0,u,height/3.1,0,height/3.1);
      }
    }
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setAttribute('uv',new T.Float32BufferAttribute(uvs,2));geometry.computeVertexNormals();
    const colours=new Float32Array(positions.length),colour=new T.Color(palette.wall);for(let i=0;i<colours.length;i+=3){colours[i]=colour.r;colours[i+1]=colour.g;colours[i+2]=colour.b}geometry.setAttribute('color',new T.BufferAttribute(colours,3));
    const wall=new T.Mesh(geometry,facades[style.atlas]);wall.castShadow=true;wall.receiveShadow=true;group.add(wall);
    const roof=mesh(new T.ExtrudeGeometry(shape,{depth:.22,bevelEnabled:false}),palette.roof,group,0,height,0);roof.rotation.x=-Math.PI/2;
    const bounds=new T.Box2().setFromPoints(shape.getPoints()),w=bounds.max.x-bounds.min.x,d=bounds.max.y-bounds.min.y;
    // Respect irregular footprint edges; no oversized rectangular roof over an arbitrary polygon.
    const area=Math.abs(points.reduce((a,p,i)=>a+p[0]*points[(i+1)%points.length][1]-points[(i+1)%points.length][0]*p[1],0))/2;
    if(style.roof!=='flat'&&points.length===4&&!f.holes?.length&&height<13){
      const [a,b,e]=[points[0],points[1],points[3]],u=[b[0]-a[0],b[1]-a[1]],v=[e[0]-a[0],e[1]-a[1]],uw=Math.hypot(...u),vd=Math.hypot(...v);
      if(Math.abs(u[0]*v[0]+u[1]*v[1])<uw*vd*.06&&area/(uw*vd)>.94){
       const corners=points.map(p=>[p[0]-c[0],height+.2,p[1]-c[1]]),ridge=Math.min(2.8,Math.min(uw,vd)*.3);
       const first=uw<vd?[0,1]:[0,3],second=uw<vd?[3,2]:[1,2];
       const midpoint=(ids:number[])=>[(corners[ids[0]][0]+corners[ids[1]][0])/2,height+ridge,(corners[ids[0]][2]+corners[ids[1]][2])/2];
       const r=midpoint(first),q=midpoint(second),[a0,b0]=first.map(i=>corners[i]),[d0,c0]=second.map(i=>corners[i]);
       const positions=[a0,b0,r,d0,q,c0,a0,r,q,a0,q,d0,b0,c0,q,b0,q,r].flat();const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.computeVertexNormals();
       const roof=mesh(geometry,palette.roof,group);roof.material=material(palette.roof);(roof.material as T.Material).side=T.DoubleSide;
      }
    }
    const near=Math.hypot(c[0]-geo.spawn[0],c[1]-geo.spawn[1])<450;
    if(!near||details++>700)continue;
    for(let i=1;i<f.points.length;i++){
      const a=f.points[i-1],b=f.points[i],len=distance(a,b);if(len<2)continue;
      const edge=new T.Group();edge.position.set((a[0]+b[0])/2-c[0],0,(a[1]+b[1])/2-c[1]);edge.rotation.y=Math.atan2(b[0]-a[0],b[1]-a[1])+Math.PI/2;group.add(edge);
      box(edge,palette.trim,0,height-.16,0,len,.23,.23);box(edge,'#b3ada0',0,.2,0,len,.4,.16);
      if(height>9)box(edge,palette.trim,0,3.1,0,len,.16,.2);
    }
    const commercial=style.family==='shop',office=style.family==='office',civic=style.family==='civic';
    const edge=f.points.slice(0,-1).map((a,i)=>({a,b:f.points[i+1],len:distance(a,f.points[i+1])})).sort((a,b)=>b.len-a.len)[0];
    if(!edge||edge.len<3)continue;
    const frontage=new T.Group();frontage.position.set((edge.a[0]+edge.b[0])/2-c[0],0,(edge.a[1]+edge.b[1])/2-c[1]);
    const outward=new T.Vector2(frontage.position.x,frontage.position.z);const angle=Math.atan2(edge.b[0]-edge.a[0],edge.b[1]-edge.a[1])+Math.PI/2;
    frontage.rotation.y=angle+(Math.sin(angle)*outward.x+Math.cos(angle)*outward.y<0?Math.PI:0);group.add(frontage);
    const width=Math.min(commercial?10:office||civic?6:3.4,edge.len*.8);
    if(style.family==='apartments'&&height>8){
      for(let floor=1;floor<Math.min(5,height/3.1-1);floor++)for(const x of [-Math.min(3,edge.len*.22),Math.min(3,edge.len*.22)]){
       box(frontage,palette.trim,x,3.1*floor+.22,.28,2.1,.16,.8);box(frontage,'#566775',x,3.1*floor+.74,.66,2.1,.72,.06);
       for(const side of [-1,1])box(frontage,'#394b58',x+side,3.1*floor+.74,.3,.06,.8,.8);
      }
    }
    if(civic){for(const x of [-width/2,width/2]){box(frontage,palette.trim,x,2,.25,.38,4,.6)}box(frontage,palette.trim,0,4.1,.3,width+.8,.35,1)}
    box(frontage,palette.accent,0,1.5,.07,width,2.9,.2);
    const window=(x:number,w:number)=>{const panel=box(frontage,'#40677e',x,1.5,.2,w,2.2,.06);panel.material=glass;box(frontage,palette.trim,x,2.63,.23,w+.12,.1,.1);box(frontage,palette.trim,x,.37,.23,w+.12,.1,.1)};
    if(commercial||office){window(-width*.3,width*.3);window(width*.3,width*.3);box(frontage,palette.accent,0,3.05,.55,width+.1,.22,commercial?1.3:.6);box(frontage,'#dfc193',0,2.89,1.18,width+.1,.12,.07)}
    else window(-width*.26,width*.25);
    box(frontage,'#233c4b',commercial?0:width*.24,1.25,.21,.95,2.45,.12);box(frontage,'#b8d3d7',commercial?0:width*.24,1.7,.28,.65,1.18,.03);
    box(frontage,'#d9bb85',(commercial?0:width*.24)+.3,1.08,.3,.05,.2,.05);
    if(commercial){for(const x of [-width/2,width/2]){box(frontage,'#645344',x,.33,1.2,.7,.65,.7);oval(frontage,'#558069',x,.88,1.2,.48,.43,.45)}}
  }
  return {buildings,dispose:()=>{textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose())}};
}
