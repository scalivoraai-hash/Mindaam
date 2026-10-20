import test from 'node:test';import assert from 'node:assert/strict';import {buildingSignSpecs} from './BuildingSigns.ts';
const building={id:'1',tags:{building:'yes',name:'QA Public Library'},points:[[0,0],[10,0],[10,10],[0,10],[0,0]]};
const road={id:'2',tags:{highway:'residential'},points:[[-20,-3],[20,-3]]};
test('named facade faces adjacent street and respects frontage',()=>{const [s]=buildingSignSpecs([building,road]);assert.equal(s.name,'QA Public Library');assert.ok(s.z<0);assert.ok(Math.cos(s.angle)<-.99);assert.ok(s.width<=8)});
test('unnamed building receives no invented name',()=>{assert.equal(buildingSignSpecs([{...building,tags:{building:'yes'}},road]).length,0)});
test('licensed shop POI attaches to containing footprint without duplicates',()=>{const signs=buildingSignSpecs([{...building,tags:{building:'yes'}},road,{id:'3',tags:{name:'QA Cafe',shop:'coffee'},points:[[5,5]]}]);assert.equal(signs.length,1);assert.equal(signs[0].name,'QA Cafe')});
