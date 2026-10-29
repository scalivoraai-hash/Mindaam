import test from 'node:test';
import assert from 'node:assert/strict';
import {terrainNavigator} from './terrain.ts';
const square=(kind,x,z,size,holes=[])=>({kind,points:[[x,z],[x+size,z],[x+size,z+size],[x,z+size],[x,z]],holes});
test('preview walks from road to public grass and slides without crossing restricted polygons',()=>{
 const nav=terrainNavigator({radius:50,features:[{kind:'road',points:[[0,-30],[0,30]],holes:[]},square('public',4,-20,40),square('building',18,0,5),square('blocked',28,0,5),{kind:'barrier',points:[[10,-15],[10,-5]],holes:[]}]});
 const point=nav.step(0,0,15,0);assert.ok(Math.abs(point.x-15)<1e-8);assert.equal(point.z,0);
 assert.ok(nav.step(15,0,-15,0).x<1e-8);assert.equal(nav.permits(20,2),false);assert.equal(nav.permits(30,2),false);assert.equal(nav.permits(51,0),false);assert.equal(nav.permits(NaN,0),false);assert.equal(nav.permits(-20,20),false);assert.ok(nav.step(8,-10,5,0).x<9.66);assert.equal(nav.grass(0,0),false);assert.equal(nav.grass(15,0),true);
});
test('holes do not acquire public-ground permission',()=>{
 const nav=terrainNavigator({radius:50,features:[square('public',0,0,40,[square('',10,10,10).points])]});assert(nav.permits(5,5));assert.equal(nav.permits(15,15),false);
});
