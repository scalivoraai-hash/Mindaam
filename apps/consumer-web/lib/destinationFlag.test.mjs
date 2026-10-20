import test from 'node:test';
import assert from 'node:assert/strict';
import {destinationFlag} from './destinationFlag.ts';
test('shared flags use canonical metadata across users and have a nonblank fallback',()=>{
 for(const [code,flag] of Object.entries({GB:'🇬🇧',FR:'🇫🇷',AE:'🇦🇪',US:'🇺🇸',IN:'🇮🇳',JP:'🇯🇵',AU:'🇦🇺'})){
  assert.equal(destinationFlag({country:code}),flag);
  assert.equal(destinationFlag({country_code:code,country:'XX'}),flag);
 }
 assert.equal(destinationFlag({id:'local-invalid-fixture'}),'🌐');
 assert.equal(destinationFlag({country:'INVALID',id:'local-invalid-fixture'}),'🌐');
});
