import test from 'node:test';import assert from 'node:assert/strict';
import {architectureRegion,regionalPalette} from './cityArchitecture.ts';
import {buildingStyle} from './buildingStyle.ts';
test('region archetypes preserve mapped building metadata and dimensions',()=>{
 const tags={building:'house',height:'8.4','building:colour':'#aabbcc'},original=structuredClone(tags),style=buildingStyle(tags,'osm-123');
 for(const city of ['london','milton-keynes-centre','dubai','abu-dhabi','mumbai','new-york','sydney']){const p=regionalPalette(city,style.palette,{wall:'#fff',trim:'#fff',roof:'#333',accent:'#444'},tags);assert.equal(p.wall,'#aabbcc');assert.deepEqual(tags,original);assert.equal(buildingStyle(tags,'osm-123').height,8.4)}
 assert.equal(architectureRegion('milton-keynes-whitehouse'),'british');assert.equal(architectureRegion('abu-dhabi'),'gulf');assert.equal(architectureRegion('mumbai'),'indian');assert.equal(architectureRegion('new-york'),'north-american');assert.equal(architectureRegion('unknown'),'international');
});
test('invalid mapped colours cannot become material URLs or CSS',()=>{const p=regionalPalette('london',0,{wall:'#fff',trim:'#fff',roof:'#333',accent:'#444'},{'building:colour':'url(https://example.test/a)'});assert.match(p.wall,/^#[0-9a-f]{6}$/)});
