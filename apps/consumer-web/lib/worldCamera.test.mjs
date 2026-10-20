import {PerspectiveCamera,Vector3} from 'three';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {orbitOffset,indoorOrbit,indoorFocus,stableIndoorOrbit} from './worldCamera.ts';
test('full orbit returns to the same position and opposite view reverses horizontal axes',()=>{for(const a of [0,.4,Math.PI,5]){const p=orbitOffset(a,.6,30),q=orbitOffset(a+2*Math.PI,.6,30),r=orbitOffset(a+Math.PI,.6,30);assert.ok(Math.hypot(p.x-q.x,p.y-q.y,p.z-q.z)<1e-10);assert.ok(Math.abs(p.x+r.x)<1e-10);assert.ok(Math.abs(p.z+r.z)<1e-10)}});
test('authenticated indoor orbit has constant distance and fixed pivot through 360 degrees and pitch',()=>{
 for(const avatar of [{x:0,y:0,z:10.5},{x:10,y:0,z:12},{x:0,y:1.5,z:-10}])for(const zoom of [6,8,10]){
 let first;
 for(let a=0;a<=Math.PI*2;a+=.1)for(const pitch of [.08,.18,.7,1.4]){
  const {focus,position:p}=stableIndoorOrbit(avatar,a,pitch,zoom);first ||= focus;assert.deepEqual(focus,first);
  assert.ok(Math.abs(Math.hypot(p.x-focus.x,p.y-focus.y,p.z-focus.z)-zoom)<1e-8);
  assert.ok(p.x>=-10.501&&p.x<=10.501&&p.y>=.5&&p.y<=7.501&&p.z>=-14.501&&p.z<=14.301);
 }
 }
});
test('low and high pitch keep the camera above ground without inverting and zoom stays bounded',()=>{for(const pitch of [-99,0,.5,Math.PI,99])for(const zoom of [-10,5,30,1000]){const p=orbitOffset(1,pitch,zoom);assert.ok(p.y>0);const radius=Math.hypot(p.x,p.y,p.z);assert.ok(radius>=5-1e-10&&radius<=75+1e-10)}});

test('auditorium orbit stays inside the room without tilting away from the stage',()=>{
 for(const focus of [{x:0,y:1.7,z:8},{x:8,y:1.7,z:12},{x:0,y:3.2,z:-10}])for(const angle of [0,.8,Math.PI,4.5])for(const pitch of [.18,.7,1.4]){
  const offset=orbitOffset(angle,pitch,16.5),desired={x:focus.x+offset.x,y:focus.y+offset.y,z:focus.z+offset.z},p=indoorOrbit(focus,desired);
  assert.ok(p.x>=-10.50001&&p.x<=10.50001&&p.z>=-14.50001&&p.z<=14.30001&&p.y<=7.70001);
  const distance=Math.hypot(p.x-focus.x,p.y-focus.y,p.z-focus.z);
  assert.ok(Math.abs((p.y-focus.y)/distance-Math.sin(pitch))<1e-8,'clipping preserves pitch');
 }
});

test('rear-row views keep the host above the local avatar on desktop and mobile',()=>{
 assert.ok(indoorFocus({x:0,y:1.5,z:-10},0).z>-13.15,'stage focus stays in front of the video wall');
 for(const z of [8,10.5])for(const width of [390,1100]){
  const focus=indoorFocus({x:0,y:0,z},0),offset=orbitOffset(0,.18,16.5),p=indoorOrbit(focus,{x:focus.x+offset.x,y:focus.y+offset.y,z:focus.z+offset.z});
  const camera=new PerspectiveCamera(48,width/844,.2,650);camera.position.set(p.x,p.y,p.z);camera.lookAt(focus.x,focus.y,focus.z);camera.updateMatrixWorld();
  const host=new Vector3(0,4.75,-10).project(camera),self=new Vector3(0,3.25,z).project(camera);
  assert.ok(Math.abs(host.y)<.8&&host.z<1,'host head remains visible');
  assert.ok(host.y-self.y>.15,'local avatar stays below the host');
 }
});
