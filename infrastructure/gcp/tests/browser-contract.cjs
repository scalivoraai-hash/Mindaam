const assert=require('assert/strict'),fs=require('fs'),path=require('path');
const {safeText,safeUrl,required,validatePolicy}=require('../browser-contract.cjs');
const secret='secret-test-value';assert.ok(!safeText('password='+secret,[secret]).includes(secret));
assert.equal(safeUrl('https://media.mindaam.com/rtc?access_token=abc'),'https://media.mindaam.com/rtc');
assert.ok(!safeText('Bearer abc.def.ghi').includes('abc.def.ghi'));
assert.ok(!safeText('postgresql://user:pass@host/db').includes('user:pass'));
const policy=JSON.parse(fs.readFileSync(path.join(__dirname,'../../../shared/media-policy.json')));
assert.ok(validatePolicy(policy));assert.throws(()=>validatePolicy({...policy,auto_subscribe:true}));
assert.throws(()=>validatePolicy({...policy,avatar_video_max:720}));
for(const key of ['signup','login','onboarding','friends','events','selective_subscription','audience_restrictions'])assert.ok(required.includes(key));
const script=fs.readFileSync(path.join(__dirname,'../browser.cjs'),'utf8');
const flow=fs.readFileSync(path.join(__dirname,'../browser-flow.cjs'),'utf8');
assert.ok(flow.includes("getByRole('heading',{name:'Welcome back, '+name+'.'"));
assert.ok(script.includes('authenticateAndEnter(u,'));
assert.ok(script.includes("await diagnostics(e);throw e"));
assert.ok(!script.includes("res.status()+' '+await res.text()"));
assert.ok(script.includes("local?.candidateType==='relay'"));
assert.ok(script.includes("local.url?.startsWith('turns:')"));
console.log('Browser safety and acceptance contracts passed');

assert.ok(!safeText('{"password":"hidden-value","token":"hidden-token"}').includes('hidden-'));

// Cross-check the harness against source-owned accessible UI contracts.
const root=path.join(__dirname,'../../..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const home=read('apps/consumer-web/components/WelcomeHome.tsx');
assert.ok(home.includes('Welcome back,'));assert.ok(read('apps/consumer-web/components/WorldDiscovery.tsx').includes('Explore worlds'));
const starter=read('apps/consumer-web/components/StarterWorldPicker.tsx');
for(const label of ['Choose your first free world','Destination','as Starter World 1 of 4'])assert.ok(starter.includes(label));
const media=read('apps/consumer-web/components/MediaPanel.tsx');
for(const label of ['Camera On','Unmute','Full Screen','Expand','More media controls'])assert.ok(media.includes(label));
const event=read('apps/consumer-web/components/EventScreenShare.tsx');
assert.ok(event.includes('Share screen'));assert.ok(event.includes('Stop sharing'));

const auth=read('apps/consumer-web/app/page.tsx');
assert.match(auth,/<button className="text-button wide" onClick=\{\(\)=>setAuth/);
for(const label of ['New here? Create an account','Username','Email address','Confirm password','Create your account','Let’s explore','Enter Mindaam'])assert.ok(auth.includes(label));
for(const name of ['adult','terms','privacy'])assert.ok(auth.includes('name="'+name+'"'));
assert.ok(flow.includes("getByRole('heading',{name:'Your Worlds',exact:true})"));
assert.ok(!flow.includes('.first()'));assert.ok(!script.includes('.last()'));
const ui=read('infrastructure/gcp/browser-ui.cjs');
assert.ok(ui.includes('trial:true'));assert.ok(ui.includes('document.elementFromPoint'));
const profile=read('apps/consumer-web/components/UserProfile.tsx');
for(const label of ['Player profile','Follow','Unfollow','Avatar','Close profile'])assert.ok(profile.includes(label));
