import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_CAMERA, dragCamera, smoothCamera,CameraGesture,boundedZoom} from './cameraMotion.ts';
test('mouse and touch drag are controlled and retain unlimited 360 rotation', () => {
  for (const touch of [false, true]) {
    const p=dragCamera(DEFAULT_CAMERA, 50, 0, touch);
    assert.ok(Math.abs(p.angle-DEFAULT_CAMERA.angle)<.15);
    let all={...DEFAULT_CAMERA}; for(let i=0;i<1000;i++)all=dragCamera(all,10,0,touch);
    assert.ok(Math.abs(all.angle-DEFAULT_CAMERA.angle)>Math.PI*2);
    const jump=dragCamera(DEFAULT_CAMERA,10000,-10000,touch);
    assert.ok(Math.abs(jump.angle-DEFAULT_CAMERA.angle)<.23);
    assert.ok(jump.pitch>=.08);
  }
});
test('player drag preserves zoom with lower sensitivity; pinch release and unknown UI pointers never orbit',()=>{
 const player=dragCamera(DEFAULT_CAMERA,50,20,false,true),preview=dragCamera(DEFAULT_CAMERA,50,20);
 assert.equal(player.zoom,DEFAULT_CAMERA.zoom);assert.ok(Math.abs(player.angle-DEFAULT_CAMERA.angle)<Math.abs(preview.angle-DEFAULT_CAMERA.angle));
 const g=new CameraGesture();g.down(1,100,100);
 assert.deepEqual(g.move(1,120,110),{dx:20,dy:10,ratio:1});assert.equal(g.move(99,10,10),null);
 g.down(2,220,110);const pinch=g.move(2,230,110);assert.equal(pinch.dx,0);assert.equal(pinch.dy,0);assert.ok(pinch.ratio<1);
 g.up(2);assert.equal(g.move(1,150,100),null);g.up(1);
 g.down(3,0,0);assert.equal(g.move(3,10,0).dx,10);g.reset();assert.equal(g.move(3,20,0),null);
 assert.equal(boundedZoom(-100),6);assert.equal(boundedZoom(100),38);assert.equal(boundedZoom(100,true),10);
});
test('damping is frame-rate independent and takes the short path across yaw wrap',()=>{
  const target={angle:1.5,pitch:.7,zoom:30};
  const samples=[30,60,120].map(hz=>{let p={angle:0,pitch:.2,zoom:12};for(let i=0;i<hz;i++)p=smoothCamera(p,target,1/hz);return p});
  for(const p of samples)for(const key of ['angle','pitch','zoom'])assert.ok(Math.abs(p[key]-samples[0][key])<1e-8);
  const p=smoothCamera({angle:Math.PI-.01,pitch:.2,zoom:12},{angle:-Math.PI+.01,pitch:.2,zoom:12},1/60);
  assert.ok(p.angle>Math.PI-.01&&p.angle<Math.PI+.01);
  assert.deepEqual(smoothCamera(DEFAULT_CAMERA,target,0),DEFAULT_CAMERA);
});
