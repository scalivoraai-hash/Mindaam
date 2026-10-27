const assert=require('assert/strict');
const {act,waitUI}=require('./browser-ui.cjs');
async function authenticateAndEnter(u,{origin,city,index,password,identifier,name,reusable,until,setStage}){
 const {page,api,states}=u;
 await page.goto(origin,{waitUntil:'domcontentloaded'});
 await waitUI(page);
 if(reusable){
 await act(u,page.locator('.auth-card').getByLabel('Email or username',{exact:true}),'fill auth/world control','fill',identifier);await act(u,page.locator('.auth-card').getByLabel('Password',{exact:true}),'fill auth/world control','fill',password);await act(u,page.locator('.auth-card').getByRole('button',{name:'Enter Mindaam',exact:true}),'click auth/world control','click');await until(async()=>{try{return (await api('/me')).onboarded}catch{return false}},'Funded host login');u.authExpected=true;const account=await api('/me');u.id=account.id;name=account.username;assert.equal(account.onboarded,true);
 }else{
 await act(u,page.locator('.auth-card').getByRole('button',{name:'New here? Create an account',exact:true}),'click auth/world control','click');
 await act(u,page.locator('.auth-card').getByLabel('Username',{exact:true}),'fill auth/world control','fill',name);
 await act(u,page.locator('.auth-card').getByLabel('Email address',{exact:true}),'fill auth/world control','fill',name+'@example.test');
 await act(u,page.locator('.auth-card').getByLabel('Password',{exact:true}),'fill auth/world control','fill',password);await act(u,page.locator('.auth-card').getByLabel('Confirm password',{exact:true}),'fill auth/world control','fill',password);
 for(const field of ['adult','terms','privacy'])await act(u,page.locator('.auth-card').locator('input[name="'+field+'"]'),'check auth/world control','check');
 await act(u,page.locator('.auth-card').getByRole('button',{name:'Create your account',exact:true}),'click auth/world control','click');
 await page.getByRole('group',{name:'Choose your first free world'}).waitFor();
 u.authExpected=true;const registered=await api('/me');u.id=registered.id;assert.equal(registered.onboarded,false);
 setStage('onboarding-'+index);
 await act(u,page.getByRole('group',{name:'Choose your first free world'}).locator('select[name="city"]'),'selectOption auth/world control','selectOption',city);
 await act(u,page.locator('.onboarding').getByRole('checkbox',{name:/as Starter World 1 of 4/}),'check auth/world control','check');
 await act(u,page.locator('.onboarding').getByRole('checkbox',{name:'Music',exact:true}),'check auth/world control','check');
 await act(u,page.locator('.onboarding').getByRole('button',{name:'Let’s explore',exact:true}),'click auth/world control','click');
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 assert.equal((await api('/me')).onboarded,true);
 }
 setStage('login-session-'+index);
 u.authExpected=false;await api('/auth/logout',{});await page.reload({waitUntil:'domcontentloaded'});
 await act(u,page.locator('.auth-card').getByLabel('Email or username',{exact:true}),'fill auth/world control','fill',name);await act(u,page.locator('.auth-card').getByLabel('Password',{exact:true}),'fill auth/world control','fill',password);
 await act(u,page.locator('.auth-card').getByRole('button',{name:'Enter Mindaam',exact:true}),'click auth/world control','click');
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 await page.reload({waitUntil:'domcontentloaded'});
 await page.getByRole('heading',{name:'Welcome back, '+name+'.',exact:true}).waitFor();
 u.authExpected=true;assert.equal((await api('/me')).id,u.id,'Browser cookie session persists across reload');
 setStage('world-entry-'+index);
 const cities=await api('/cities'),destination=cities.find(c=>c.id===city);assert.ok(destination);
 await act(u,page.getByRole('region',{name:'Explore worlds'}).getByRole('heading',{name:'Your Worlds',exact:true}).locator('xpath=following-sibling::div[1]').getByRole('button').filter({hasText:destination.name}),'click auth/world control','click');
 await act(u,page.getByRole('dialog',{name:'Choose a world'}).getByRole('button',{name:'Enter '+destination.name,exact:true}),'click auth/world control','click');
 await page.locator('.world-playing').waitFor();
 await page.locator('.world-canvas[data-ready="true"]').waitFor({timeout:90000});
 await until(()=>states.at(-1)?.city===city,'Authenticated realtime world state '+city,60000);
 u.username=name;return u;
}
module.exports={authenticateAndEnter};
