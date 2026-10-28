/* Disposable local UI/admin acceptance; never a staging funding or media proof. */
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');const fs=require('fs');
const {spawn,execFileSync}=require('child_process');const root=require('path').resolve(__dirname,'../..');const out=process.env.QA_OUTPUT||'/tmp/mindaam-private-admin';fs.mkdirSync(out,{recursive:true});const python=process.env.QA_PYTHON||'python3';const env={...process.env,APP_ENV:'local',PUBLIC_ORIGIN:'http://127.0.0.1:3000',DATABASE_URL:'sqlite:////tmp/mylil-multi-operator-'+Date.now()+'.db'};for(const key of ['SUPER_ADMIN_EMAIL','SUPER_ADMIN_USERNAME','SUPER_ADMIN_INITIAL_PASSWORD'])delete env[key];delete env.STRIPE_SECRET_KEY;delete env.STRIPE_WEBHOOK_SECRET;delete env.LIVEKIT_API_KEY;delete env.LIVEKIT_API_SECRET;execFileSync(python,['-m','scripts.tests.multiplayer_fixture','init','{}'],{cwd:root,env});env.SUPER_ADMIN_EMAIL='owner@example.test';env.SUPER_ADMIN_USERNAME='private_owner';env.SUPER_ADMIN_INITIAL_PASSWORD=require('crypto').randomBytes(32).toString('base64url');const children=[spawn(python,['-m','uvicorn','backend.api.main:app','--host','127.0.0.1','--port','8000'],{cwd:root,env,stdio:['ignore',fs.openSync(out+'/ui-api.log','w'),fs.openSync(out+'/ui-api-err.log','w')]}),spawn(process.execPath,['node_modules/next/dist/bin/next','start','apps/consumer-web','--hostname','127.0.0.1'],{cwd:root,env,stdio:['ignore',fs.openSync(out+'/ui-web.log','w'),fs.openSync(out+'/ui-web-err.log','w')]})];
process.on('exit',()=>children.forEach(p=>p.kill()));
const assert=require('assert/strict');
(async()=>{
 for(let i=0;i<90;i++){try{if((await fetch('http://127.0.0.1:3000')).ok&&(await fetch('http://127.0.0.1:8000/api/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,1000))}
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/mindaam-chromium/chromium',args:['--no-sandbox']});
 try{
 const ctx=await browser.newContext(),p=await ctx.newPage(),origin='http://127.0.0.1:3000',errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 assert.equal((await p.goto(origin+'/super-admin')).status(),404);
 await p.goto(origin+'/eluvathingal');await p.waitForURL('**/eluvathingal/login');
 await p.getByRole('heading',{name:'Admin sign in',exact:true}).waitFor();
 await p.getByLabel('Email or username',{exact:true}).fill('owner@example.test');
 await p.getByLabel('Password',{exact:true}).fill('incorrect');await p.getByRole('button',{name:'Sign In',exact:true}).click();await p.getByRole('alert').waitFor();
 await p.getByRole('button',{name:'Show password',exact:true}).click();assert.equal(await p.getByLabel('Password',{exact:true}).getAttribute('type'),'text');
 await p.getByRole('button',{name:'Hide password',exact:true}).click();
 await p.getByLabel('Password',{exact:true}).fill(env.SUPER_ADMIN_INITIAL_PASSWORD);await p.getByRole('button',{name:'Sign In',exact:true}).click();
 await p.getByRole('heading',{name:'Set your permanent password',exact:true}).waitFor();
 await p.locator('summary').filter({hasText:'Change password'}).click();
 const permanent=require('crypto').randomBytes(32).toString('base64url');
 await p.getByLabel('Current password',{exact:true}).fill(env.SUPER_ADMIN_INITIAL_PASSWORD);await p.getByLabel('New password',{exact:true}).fill(permanent);await p.getByLabel('Confirm new password',{exact:true}).fill(permanent);
 await p.getByRole('button',{name:'Change password',exact:true}).click();await p.waitForURL('**/eluvathingal/login');
 await p.getByLabel('Email or username',{exact:true}).fill('owner@example.test');await p.getByLabel('Password',{exact:true}).fill(permanent);await p.getByRole('button',{name:'Sign In',exact:true}).click();
 await p.getByRole('heading',{name:'Overview',exact:true}).waitFor();await p.reload();await p.getByRole('heading',{name:'Overview',exact:true}).waitFor();
 for(const name of ['Users','Live Operations','Revenue','Collectibles','Audit']){await p.getByRole('button',{name,exact:true}).click();await p.getByRole('heading',{name,exact:true}).waitFor()}
 await p.getByRole('button',{name:'Sign out',exact:true}).click();await p.waitForURL('**/eluvathingal/login');
 assert.equal((await ctx.request.get(origin+'/api/super-admin/overview')).status(),401);
 const regular=await browser.newContext();const r=await regular.request.post(origin+'/api/auth/register',{headers:{Origin:origin,'X-Pulse-Client':'web'},data:{email:'ordinary-browser@example.test',username:'ordinary_browser',password:permanent,adult:true,accepted_terms:true,accepted_privacy:true,confirm_password:permanent}});assert.equal(r.status(),201);
 const denied=await regular.newPage();await denied.goto(origin+'/eluvathingal');await denied.getByRole('heading',{name:'Access restricted',exact:true}).waitFor();assert.equal((await regular.request.get(origin+'/api/super-admin/overview')).status(),403);
 assert.deepEqual(errors,[]);console.log('PASS: private route, legacy 404, wrong password, visibility, bootstrap first change, session persistence, dashboard modules, logout and ordinary-user denial. Local disposable accounts only.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>children.forEach(p=>p.kill()));
