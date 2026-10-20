import test from 'node:test';
import assert from 'node:assert/strict';
import {api,list} from './api.ts';
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});

test('a failed HTTP 200 body is rejected instead of masquerading as application data',async t=>{
 t.mock.method(globalThis,'fetch',async()=>({ok:true,status:200,json:async()=>{throw new DOMException('The operation was aborted','AbortError')}}));
 await assert.rejects(api('/social-activity/event/fixture'),/Unable to read the server response/);
 assert.equal(globalThis.fetch.mock.callCount(),1);
});
test('body transport failures retry GET and return only the complete snapshot',async t=>{
 const snapshot={catalogue:{},recipients:[],gifts:[],reactions:[]};let calls=0;
 t.mock.method(globalThis,'fetch',async()=>({ok:true,status:200,json:async()=>{if(!calls++)throw new TypeError('Connection interrupted');return snapshot}}));
 assert.deepEqual(await api('/social-activity/event/fixture'),snapshot);assert.equal(calls,2);
});
test('mutations are never repeated after a failed response body',async t=>{
 t.mock.method(globalThis,'fetch',async()=>({ok:true,status:200,json:async()=>{throw new TypeError('Connection interrupted')}}));
 await assert.rejects(api('/events','POST',{}),/Connection interrupted/);assert.equal(globalThis.fetch.mock.callCount(),1);
});
test('mission lists accept the endpoint array and wrapped presentation contract, including empty values',()=>{
 const missions=[{id:'fixture',completed:false}];assert.deepEqual(list(missions,'missions'),missions);assert.deepEqual(list({missions},'missions'),missions);
 for(const value of [[],{missions:[]},null,{}, {missions:null}])assert.deepEqual(list(value,'missions'),[]);
});

test('a timeout after headers retries a read instead of returning an error object',async t=>{
 const snapshot={id:'fixture',onboarded:true};let calls=0;
 t.mock.method(AbortSignal,'timeout',()=>calls===0?AbortSignal.abort(new DOMException('Timed out','TimeoutError')):new AbortController().signal);
 t.mock.method(globalThis,'fetch',async()=>({ok:true,status:200,json:async()=>{if(!calls++)throw new DOMException('Aborted','AbortError');return snapshot}}));
 assert.deepEqual(await api('/me'),snapshot);assert.equal(calls,2);
});
