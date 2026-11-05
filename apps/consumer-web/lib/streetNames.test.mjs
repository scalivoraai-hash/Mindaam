import test from 'node:test';import assert from 'node:assert/strict';
import {streetPlates} from './streetNames.ts';
test('streets beyond the old first 45 remain indexed and repeated segments are deduplicated',()=>{
 const roads=Array.from({length:80},(_,i)=>({id:'road'+i,tags:{highway:'residential',name:'Street '+i},points:[[0,i*25],[80,i*25]]}));
 const plates=streetPlates([...roads,...roads]);assert.equal(new Set(plates.map(p=>p.name)).size,80);assert.equal(plates.length,80);
});
test('long streets retain nameplates away from spawn and unnamed roads are not invented',()=>{
 const plates=streetPlates([{id:'long',tags:{highway:'residential',name:'Borrasa Way'},points:[[0,0],[800,0]]},{id:'unnamed',tags:{highway:'residential'},points:[[0,100],[100,100]]}]);
 assert(plates.some(p=>p.x>600));assert(plates.every(p=>p.name==='Borrasa Way'));
});
test('a building at the first roadside position selects the opposite verge',()=>{
 const plates=streetPlates([{id:'r',tags:{highway:'residential',name:'Mapped street'},points:[[0,0],[20,0]]},{id:'b',tags:{building:'yes'},points:[[0,-20],[20,-20],[20,-1],[0,-1],[0,-20]]}]);
 assert.equal(plates.length,1);assert(plates[0].z>0);
});
