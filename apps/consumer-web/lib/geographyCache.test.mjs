import test from 'node:test';
import assert from 'node:assert/strict';
import {loadGeography} from './geographyCache.ts';
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});

test('a failed separate profile request cannot downgrade the authoritative map',async t=>{
 const map={city:'profile-regression',features:[],visual_profile:'cinematic-world-v2'};
 t.mock.method(globalThis,'fetch',async url=>{
  if(url.includes('/visual-profile/'))throw new DOMException('Timed out','TimeoutError');
  return {ok:true,status:200,json:async()=>map};
 });
 const first=loadGeography('profile-regression');
 assert.equal(loadGeography('profile-regression'),first);
 assert.deepEqual(await first,map);
 assert.equal(globalThis.fetch.mock.callCount(),1);
});

test('failed geography is not cached and a subsequent request can recover',async t=>{
 let failed=true;
 t.mock.method(globalThis,'fetch',async()=>({ok:!failed,status:failed?403:200,json:async()=>failed?{detail:'Unavailable'}:{visual_profile:'standard',features:[]}}));
 await assert.rejects(loadGeography('retry-regression'),/Unavailable/);
 failed=false;
 assert.deepEqual(await loadGeography('retry-regression'),{visual_profile:'standard',features:[]});
 assert.equal(globalThis.fetch.mock.callCount(),2);
});

test('an older backend remains compatible during gradual rollout',async t=>{
 t.mock.method(globalThis,'fetch',async url=>({ok:true,status:200,json:async()=>url.includes('/visual-profile/')?{city:'older-backend',profile:'cinematic-world-v2'}:{features:[]}}));
 assert.deepEqual(await loadGeography('older-backend'),{features:[],visual_profile:'cinematic-world-v2'});
 assert.equal(globalThis.fetch.mock.callCount(),2);
});
