import * as T from 'three';
/** One shared shader uniform per district. No scene rebuild or per-vertex CPU work. */
export function seasonalSurfaces(district:T.Object3D){
 const uniforms={snow:{value:0},autumn:{value:0},spring:{value:0},wet:{value:0},night:{value:0},time:{value:0},wind:{value:0}},clones=new Map<T.Material,T.MeshStandardMaterial>();
 district.traverse(o=>{if(!(o instanceof T.Mesh))return;const convert=(source:T.Material)=>{
  if(!(source instanceof T.MeshStandardMaterial)||source.userData.outdoorGround)return source;
  if(clones.has(source))return clones.get(source)!;
  const mat=source.clone();mat.userData.cityOwned=true;clones.set(source,mat);
  mat.onBeforeCompile=shader=>{
   Object.assign(shader.uniforms,{mSnow:uniforms.snow,mAutumn:uniforms.autumn,mSpring:uniforms.spring,mWet:uniforms.wet,mNight:uniforms.night,mSeasonTime:uniforms.time,mSeasonWind:uniforms.wind});
   shader.vertexShader='varying float mUp; uniform float mSeasonTime; uniform float mSeasonWind;\n'+shader.vertexShader;
   shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nmUp = clamp((modelMatrix * vec4(normal,0.0)).y,0.0,1.0);\n#ifdef USE_COLOR\nfloat foliage=step(color.r*1.12,color.g)*step(color.b*1.12,color.g);vec3 wp=(modelMatrix*vec4(position,1.0)).xyz;transformed.x+=foliage*smoothstep(2.0,6.0,wp.y)*sin(mSeasonTime+wp.x*.3+wp.z*.2)*mSeasonWind*.18;\n#endif');
   shader.fragmentShader='varying float mUp; uniform float mSnow; uniform float mAutumn; uniform float mSpring; uniform float mWet; uniform float mNight;\n'+shader.fragmentShader;
   shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
    float greenery=step(diffuseColor.r*1.12,diffuseColor.g)*step(diffuseColor.b*1.12,diffuseColor.g);
    diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.62,.22,.045),greenery*mAutumn*.8);
    diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.35,.61,.24),greenery*mSpring*.35);
    diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.83,.9,.96),mSnow*smoothstep(.65,.96,mUp)*.85);
    diffuseColor.rgb*=1.0-mWet*mUp*.14;`);
   shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,max(.3,roughnessFactor*.6),mWet*mUp);');
   shader.fragmentShader=shader.fragmentShader.replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\nfloat glass=step(diffuseColor.r*1.3,diffuseColor.b)*step(diffuseColor.g*1.08,diffuseColor.b);float lamp=1.0-smoothstep(.015,.045,distance(diffuseColor.rgb,vec3(.922,.855,.680)));totalEmissiveRadiance+=(vec3(.20,.17,.09)*glass*(1.0-mUp)+vec3(.6,.45,.2)*lamp)*mNight;');
  };mat.customProgramCacheKey=()=> 'mindaam-seasons-v2';return mat;
 };o.material=Array.isArray(o.material)?o.material.map(convert):convert(o.material);});
 return {update(season:number,rain:boolean,night:boolean,dt:number,seconds=0,wind=0,reduce=false){uniforms.time.value=seconds;uniforms.wind.value=reduce?0:wind;const k=Math.min(1,dt*.2);for(const [name,target] of Object.entries({snow:season===3?1:0,autumn:season===2?1:0,spring:season===0?1:0,wet:rain?1:0,night:night?1:0})){const uniform=uniforms[name as keyof typeof uniforms];uniform.value+=(target-uniform.value)*k;}},dispose(){clones.forEach(m=>m.dispose());}};
}
