// Track-source routing and playback ownership. Actual WebRTC is tested separately.
const fs=require('fs'),ts=require('typescript'),assert=require('assert/strict');
const {chromium}=require((process.env.QA_NODE_MODULES||process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES)+'/playwright');
(async()=>{const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||'/tmp/mylil-chromium/chromium',headless:true,args:['--no-sandbox']});try{const page=await browser.newPage();const source=fs.readFileSync('apps/consumer-web/lib/mediaTiles.ts','utf8').replace(/^import[^\n]*\n/,'').replace(/^export type[^\n]*\n/m,'').replace('export class MediaTiles','class MediaTiles');const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;const result=await page.evaluate(code=>{
 const Track={Kind:{Audio:'audio',Video:'video'},Source:{Camera:'camera',Microphone:'microphone',ScreenShare:'screen_share',ScreenShareAudio:'screen_share_audio'}};
 const MediaTiles=new Function('Track',code+';return MediaTiles;')(Track);const host=document.createElement('div');document.body.append(host);let stage;window.addEventListener('pulse-stage-media',e=>stage=e.detail.video);
 const track=kind=>({kind,attached:0,detached:0,attach(){this.attached++;const e=document.createElement(kind);e.play=()=>Promise.resolve();return e},detach(element){this.detached++;return [element]}});
 const video=track('video'),audio=track('audio'),screen=track('video'),screenAudio=track('audio'),speaker={identity:'speaker',name:'Speaker',isLocal:false,trackPublications:new Map([['v',{trackSid:'v',source:'camera',track:video,isMuted:false}],['a',{trackSid:'a',source:'microphone',track:audio,isMuted:false}]])};
 const tiles=new MediaTiles(host,()=>false,()=>{});tiles.sync([speaker],'liveface',['speaker']);const original=host.querySelector('audio'),camera=stage;const videoDisplayed=stage instanceof HTMLVideoElement;
 tiles.sync([speaker],'liveface',['speaker']);const stable=host.querySelector('audio')===original&&audio.attached===1&&audio.detached===0;
 speaker.trackPublications.set('share',{trackSid:'share',source:'screen_share',track:screen,isMuted:false});speaker.trackPublications.set('sound',{trackSid:'sound',source:'screen_share_audio',track:screenAudio,isMuted:false});
 tiles.sync([speaker],'liveface',['speaker']);const unauthorisedIgnored=stage===camera&&screen.attached===0;
 const presentation={presenter_id:'speaker',screen_track_id:'share',screen_audio_track_id:'sound'};
 tiles.sync([speaker],'liveface',['speaker'],presentation);const screenOnWall=stage!==camera&&stage?.dataset.trackSource==='screen_share';const cameraStays=host.querySelector('.media-tile video')===camera&&video.detached===0;const microphoneStays=host.querySelector('.media-tile audio')===original&&audio.detached===0;
 const separateAudio=host.querySelectorAll('audio').length===2&&screenAudio.attached===1;
 speaker.trackPublications.delete('share');speaker.trackPublications.delete('sound');tiles.sync([speaker],'liveface',['speaker'],presentation);const cameraRestored=stage===camera;
 speaker.trackPublications.delete('v');tiles.sync([speaker],'liveface',['speaker']);const cleared=stage===null&&!host.querySelector('video');const audioContinued=host.querySelector('audio')===original&&audio.detached===0;
 tiles.dispose();return {videoDisplayed,stable,unauthorisedIgnored,screenOnWall,cameraStays,microphoneStays,separateAudio,cameraRestored,cleared,audioContinued,disposed:audio.detached===1};
 },code);for(const [key,value] of Object.entries(result))assert.equal(value,true,key);console.log('Media tile regressions passed',result)}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
