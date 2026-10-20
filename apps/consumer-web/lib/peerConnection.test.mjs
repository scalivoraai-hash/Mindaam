import test from 'node:test';
import assert from 'node:assert/strict';
import {peerConnection} from './peerConnection.ts';
test('connection CTA follows consent and group membership, independent of local view',()=>{
 const root={id:'r',state:'accepted',members:[{id:'me'},{id:'peer'},{id:'third'}]};
 assert.equal(peerConnection([root],'third'),'connected');
 assert.equal(peerConnection([{...root,state:'ended'}],'third'),null);
 assert.equal(peerConnection([{state:'pending',peer:{id:'peer'}}],'peer'),'pending');
 assert.equal(peerConnection([{...root,event_id:'auditorium'}],'third'),null);
 assert.equal(peerConnection([root,{state:'pending',peer:{id:'peer'}}],'peer'),'connected');
});
