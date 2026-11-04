import test from 'node:test';
import assert from 'node:assert/strict';
import {whitehouseArchitecture,frontageEdge} from './whitehouseArchitecture.ts';
const footprint=[[0,0],[8,0],[8,10],[0,10],[0,0]];
const building={id:'house',tags:{building:'yes'},points:footprint};
test('only a contained mapped business supplies commercial facade classification',()=>{
 const poi={id:'source-shop',tags:{shop:'convenience',name:'Mapped shop'},points:[[4,4]]};
 const before=JSON.stringify(building),style=whitehouseArchitecture(building,[poi],[]);
 assert.equal(style.family,'shop');assert.equal(style.poi,poi.id);assert.equal(style.height,6.2);assert.equal(style.name,poi.tags.name);
 assert.equal(JSON.stringify(building),before);
 assert.equal(whitehouseArchitecture(building,[{...poi,points:[[9,4]]}],[]).family,'neutral');
});
test('a courtyard POI cannot reclassify the enclosing building',()=>{
 const withHole={...building,holes:[[[2,2],[6,2],[6,6],[2,6],[2,2]]]};
 assert.equal(whitehouseArchitecture(withHole,[{id:'cafe',tags:{amenity:'cafe'},points:[[4,4]]}],[]).family,'neutral');
});
test('residential context is explicitly an approximation and does not invent a building use',()=>{
 const style=whitehouseArchitecture(building,[],[{id:'area',tags:{landuse:'residential'},points:[[-1,-1],[11,-1],[11,11],[-1,11],[-1,-1]]}]);
 assert.equal(style.family,'neutral');assert.equal(style.residentialContext,true);assert.match(style.confidence,/use unverified/);
});
test('entrances select a route-facing facade consistently for either polygon winding',()=>{
 const road=[[[12,-4],[12,14]]];
 const i=frontageEdge(footprint,road);assert.equal(i,1);
 const reversed=footprint.slice().reverse(),j=frontageEdge(reversed,road);
 assert.equal(reversed[j][0],8);assert.equal(reversed[j+1][0],8);
 assert.equal(frontageEdge(footprint,[[[100,0],[100,10]]]),0);
});
