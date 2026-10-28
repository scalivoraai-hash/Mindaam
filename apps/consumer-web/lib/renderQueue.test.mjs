import test from 'node:test';
import assert from 'node:assert/strict';
import {RenderQueue} from './renderQueue.ts';
function context(){return {TIMEOUT_EXPIRED:1,CONDITION_SATISFIED:2,SYNC_GPU_COMMANDS_COMPLETE:3,status:1,submitted:0,deleted:0,flushed:0,fenceSync(){this.submitted++;return {}},flush(){this.flushed++},clientWaitSync(_sync,flags,timeout){assert.equal(flags,0);assert.equal(timeout,0);return this.status},deleteSync(){this.deleted++}}}
test('a slow GPU admits one frame and polls without blocking until it completes',()=>{
 const gl=context(),queue=new RenderQueue();assert(queue.ready(gl));queue.submitted(gl);
 for(let i=0;i<120;i++)assert.equal(queue.ready(gl),false);
 assert.equal(gl.submitted,1);assert.equal(gl.flushed,1);assert.equal(gl.deleted,0);
 gl.status=gl.CONDITION_SATISFIED;assert(queue.ready(gl));assert.equal(gl.deleted,1);
 queue.submitted(gl);assert.equal(gl.submitted,2);
});
test('a scene transition shares pending work while final disposal releases it once',()=>{
 const gl=context(),queue=new RenderQueue();queue.submitted(gl);assert.equal(queue.ready(gl),false);
 queue.dispose(gl);queue.dispose(gl);assert.equal(gl.deleted,1);assert(queue.ready(gl));
});
test('a failed sync does not permanently freeze rendering after context recovery',()=>{
 const gl=context(),queue=new RenderQueue();queue.submitted(gl);gl.status=4;
 assert(queue.ready(gl));assert.equal(gl.deleted,1);
});

test('contexts without fence support retain their existing rendering path',()=>{const queue=new RenderQueue();assert(queue.ready({}));queue.submitted({});queue.dispose({});assert(queue.ready({}))});
