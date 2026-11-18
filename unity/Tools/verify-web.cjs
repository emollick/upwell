const http=require("node:http");
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const zlib=require("node:zlib");
const {chromium}=require("playwright");
const fractureInputs=require("./fracture-inputs.cjs");
const selectMomentRow=require("./moment-row.cjs");
const project=path.resolve(__dirname,"..");
const site=process.env.UPWELL_WEB_ROOT?path.resolve(process.env.UPWELL_WEB_ROOT):path.resolve(project,"../web");
const hosted=process.argv.find(arg=>arg.startsWith("https://"));
const output=hosted?path.resolve(project,"../qa/zero-g/production-unity"):path.join(project,"Verification");
const graphicsFolder=path.join(output,"graphics");fs.mkdirSync(graphicsFolder,{recursive:true});
if(hosted)fs.mkdirSync(path.join(output,"gravity"),{recursive:true});
const server=http.createServer((req,res)=>{
    const pathname=decodeURIComponent(new URL(req.url,"http://localhost").pathname);
    const file=path.resolve(site,"."+pathname+(pathname.endsWith("/")?"index.html":""));
    if(!file.startsWith(site+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}
    const ext=path.extname(file);
    const mime={".html":"text/html",".js":"application/javascript",".unityweb":"application/octet-stream",".wasm":"application/wasm",".data":"application/octet-stream"};
    const encoded=process.argv.includes("--encoded-host")&&ext===".unityweb";
    if(encoded)res.setHeader("Content-Encoding","br");
    res.setHeader("Content-Type",encoded&&file.includes(".wasm.")?"application/wasm":encoded&&file.includes(".js.")?"application/javascript":mime[ext]||"application/octet-stream");
    fs.createReadStream(file).pipe(res);
});
async function verifyGraphics(page,software){
    const read=()=>page.evaluate(()=>document.getElementById("ride").upwellGraphics);
    const wait=async (key,value)=>{try{await page.waitForFunction(([k,v])=>document.getElementById("ride").upwellGraphics?.[k]===v,[key,value],{timeout:22000});}catch(err){throw new Error("Graphics "+key+" expected "+value+"; "+JSON.stringify(await read()));}};
    const key=async key=>{await page.keyboard.down(key);await page.waitForTimeout(software?1250:200);await page.keyboard.up(key);await page.waitForTimeout(software?500:200);};
    const click=async (row,index,n)=>{const p=await page.evaluate(([row,index,n])=>{
        const c=document.getElementById("ride"),bounds=c.getBoundingClientRect(),u=Math.max(.74,Math.min(1.6,c.height/850)),w=c.width/u,h=c.height/u;
        const pw=Math.min(420,w-24),ph=Math.min(402,h-16),left=(w-pw)/2+18,y=(h-ph)/2,r=(ph-124)/4,inner=pw-36,b=(inner-(n-1)*4)/n;
        const px=row===-2?left+pw-66:row===-1?left+47:left+index*(b+4)+b/2,py=row===-2?y+25:row===-1?y+ph-27:y+51+row*r+24+Math.min(30,r-25)/2;
        return {x:bounds.left+px*u*bounds.width/c.width,y:bounds.top+py*u*bounds.height/c.height};
    },[row,index,n]);
        await page.mouse.click(p.x,p.y,{delay:software?850:110});await page.waitForTimeout(software?850:200);
    };
    const audit=async()=>{await page.evaluate(()=>{const c=document.getElementById("ride");delete c.upwellEdgeAudit;c.dispatchEvent(new Event("verify-visible-edges"));});
        await page.waitForFunction(()=>!!document.getElementById("ride").upwellEdgeAudit,null,{timeout:45000});
        const result=await page.evaluate(()=>document.getElementById("ride").upwellEdgeAudit);
        if(result.samples!==1||result.changed<result.repeat+50)throw new Error("No optical change in same-tick WebGL readback: "+JSON.stringify(result));return result;};
    const aim=async()=>page.evaluate(()=>{const c=document.getElementById("ride");c.dispatchEvent(new Event("read-visible-aim"));return c.upwellAim;});
    await wait("software",software);
    await key("F2");await wait("menu",true);
    const defaults=await read();
    if(defaults.msaa!==0||defaults.cabinSamples!==1||defaults.edges!==(software?0:1)||defaults.contact!==(software?0:1)||defaults.shadows!==(software?1:2))
        throw new Error("Incorrect hardware capabilities/initial state: "+JSON.stringify(defaults));
    await page.screenshot({path:path.join(graphicsFolder,software?"web-software-menu.png":"web-hardware-menu.png")});
    await click(0,software?1:0,2);await wait("edges",software?1:0);
    if(!software)await page.screenshot({path:path.join(graphicsFolder,"web-hardware-menu-aa-off.png")});
    await click(1,0,3);await wait("shadowQuality",0);
    if(software){
        await click(1,2,3);await wait("shadows",0);
        await click(2,2,3);await wait("atmosphere",0);
        await click(3,1,2);await wait("contact",0);
        const capped=await read();await click(-1,0,1);await wait("edges",0);await wait("shadowQuality",1);await key("F2");await wait("menu",false);
        const initial=await page.evaluate(()=>document.getElementById("ride").upwellFrame);
        await page.waitForTimeout(6000);
        const finish=await page.evaluate(()=>document.getElementById("ride").upwellFrame);
        return {defaults,capped,warmFPS:(finish.frame-initial.frame)/(finish.seconds-initial.seconds)};
    }
    await click(2,0,3);await wait("atmosphere",0);await click(3,0,2);await wait("contact",0);
    const selected=await read();await key("F2");await wait("menu",false);
    const cabin=await audit();
    await page.reload({waitUntil:"domcontentloaded"});await page.getByRole("button",{name:"Enter the carriage"}).waitFor({timeout:180000});
    await page.getByRole("button",{name:"Enter the carriage"}).click();await wait("contact",0);
    const persisted=await read();
    if(persisted.edges||persisted.shadows||persisted.atmosphere)throw new Error("Saved graphics choices did not reload: "+JSON.stringify(persisted));
    await key("F2");await wait("menu",true);await click(-1,0,1);await wait("edges",1);await wait("contact",1);await wait("shadowQuality",2);await wait("atmosphere",1);
    await key("F2");await wait("menu",false);await key("5");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.view===5);
    await page.waitForFunction(()=>{const g=document.getElementById("ride").upwellGraphics;return g?.opticSamples===1&&g.sensorScene===g.sensorFiltered;});
    const optic=await audit();if(!optic.optical)throw new Error("Expected actual guide sensor");
    await key("F2");await wait("menu",true);await click(2,0,3);await wait("atmosphere",0);const low=await read();
    await click(2,2,3);await wait("atmosphere",2);await page.waitForFunction(w=>document.getElementById("ride").upwellGraphics?.skyWidth>w,low.skyWidth);const high=await read();
    await click(-1,0,1);await wait("atmosphere",1);await key("F2");await wait("menu",false);await key("0");
    let x=650,y=285;await page.mouse.move(x,y);await key("1");let target=await aim(),gainX=.175,gainY=.15;
    for(let turn=0;target&&!target.atOptic&&turn<8;turn++){
        const dx=Math.max(-220,Math.min(220,target.horizontal/gainX)),dy=Math.max(-160,Math.min(160,target.vertical/gainY));
        x+=dx;y+=dy;await page.mouse.move(x,y,{steps:5});await page.waitForTimeout(300);const next=await aim();
        if(Math.abs(dx)>2&&Math.abs((target.horizontal-next.horizontal)/dx)>.025)gainX=(target.horizontal-next.horizontal)/dx;
        if(Math.abs(dy)>2&&Math.abs((target.vertical-next.vertical)/dy)>.025)gainY=(target.vertical-next.vertical)/dy;
        target=next;
    }
    if(!target?.atOptic)throw new Error("Ordinary pointer could not aim at the modeled binoculars: "+JSON.stringify(target));
    await key("f");if(!(await aim()).inHand)throw new Error("Ordinary F did not bring the binoculars into the cabin light");
    await key("q");const held=await audit();if(!held.held||held.optical)throw new Error("Held optics were not present in the actual cabin framebuffer");
    await key("F2");await wait("menu",true);await key("F2");await wait("menu",false);
    if(!(await aim()).inHand)throw new Error("Graphics panel discarded the held object");
    await key("f");await key("1");
    const initialAim=await aim(),dismissals=[];
    for(const level of [0,1]){
        await key("F2");await wait("menu",true);await click(0,level,2);await wait("edges",level);await click(-2,0,1);
        await wait("menu",false);await page.waitForTimeout(500);
        const after=await aim();
        if(after.zoomed!==initialAim.zoomed||Math.abs(after.lens-initialAim.lens)>.12||Math.max(Math.abs(after.horizontal-initialAim.horizontal),Math.abs(after.vertical-initialAim.vertical))>.12)
            throw new Error("Clicking Graphics Close disturbed the passenger sightline: "+JSON.stringify({initialAim,after}));
        dismissals.push(after);
    }
    await key("0");
    const start=await page.evaluate(()=>document.getElementById("ride").upwellFrame);await page.waitForTimeout(4200);const end=await page.evaluate(()=>document.getElementById("ride").upwellFrame);
    const warmFPS=(end.frame-start.frame)/(end.seconds-start.seconds);
    return {defaults,selected,persisted,cabin,held,optic,low,high,warmFPS,dismissals};
}
async function passage(adapter,width,height,outputName){
    const errors=[],log=[];let browser;
    try {
        browser=await chromium.launch({executablePath:process.env.CHROME_PATH||"C:/Program Files/Google/Chrome/Application/chrome.exe",headless:true,args:["--no-sandbox","--ignore-gpu-blocklist","--use-angle="+adapter,"--enable-unsafe-swiftshader","--autoplay-policy=no-user-gesture-required"]});
        const encodedItems={};
        const touchGravity=process.argv.includes("--gravity-touch");
        const page=await browser.newPage({viewport:{width,height},hasTouch:touchGravity,isMobile:touchGravity});page.on("pageerror",e=>errors.push(e.message));
        page.on("response",r=>{if(r.status()>=400)errors.push(r.status()+" "+r.url());if(r.url().endsWith(".unityweb"))encodedItems[path.basename(r.url())]=r.headers()["content-encoding"]||"fallback";});
        page.on("console",m=>{if(m.type()==="error")errors.push(m.text());log.push(m.text());});
        const origin=hosted||("http://127.0.0.1:"+server.address().port);
        await page.goto(new URL(hosted?"/unity/":"/unity/?verify-graphics",origin).href,{waitUntil:"domcontentloaded"});
        await page.getByRole("button",{name:"Enter the carriage"}).waitFor({timeout:240000});
        if(await page.evaluate(()=>!!document.pointerLockElement))throw new Error("Unity captured the pointer before boarding");
        await page.getByRole("button",{name:"Enter the carriage"}).click();
        await page.waitForFunction(()=>document.getElementById("boarding").hidden);
        await page.waitForTimeout(1800);
        if(touchGravity){
            const pause=ms=>page.waitForTimeout(ms);
            await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.count===13);
            await page.getByRole("button",{name:"Moments",exact:true}).tap();
            await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.menu);
            await page.keyboard.down("End");await pause(190);await page.keyboard.up("End");await pause(350);
            await page.screenshot({path:path.join(output,"gravity/touch-moments.jpg"),type:"jpeg",quality:90});
            await selectMomentRow(page,11,{touch:true});
            const onward=page.locator("#galley-onward");
            try{await onward.waitFor({state:"visible",timeout:6500});}catch{
                await page.screenshot({path:path.join(output,"gravity/touch-galley-debug.jpg"),type:"jpeg",quality:91});
                throw Error("Galley touch action missing "+JSON.stringify(await page.evaluate(()=>({state:document.getElementById("ride").upwellPassage,size:[innerWidth,innerHeight],touch:matchMedia("(pointer:coarse)").matches,lock:!!document.pointerLockElement}))));
            }
            await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.seconds===360);await onward.tap();
            await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.index===12);
            const arrival=await page.evaluate(()=>{const c=document.getElementById("ride");return {view:c.upwellPassage.view,seconds:c.upwellPassage.seconds};});
            if(arrival.view!==0)throw Error("The suggested galley tour seated an originally free passenger before the touch push: "+JSON.stringify(arrival));
            if(hosted)return await require("../../qa/unity-public-zero-g.cjs")(page,output,true);
            const restored=await page.evaluate(()=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-load-target",{detail:"mug"}));return c.upwellLoad;});
            if(!restored?.drifting||restored.eye.y<2.27)throw Error("The galley returned the camera without its physical braking history: "+JSON.stringify(restored));
            await page.getByRole("button",{name:"Push off surface",exact:true}).tap();await pause(720);
            const state=await page.evaluate(()=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-load-target",{detail:"mug"}));return {body:c.upwellLoad,view:c.upwellPassage.view};});
            if(state.view!==0||!state.body.drifting||state.body.g>.00001)throw Error("Touch push did not leave the dock observer "+JSON.stringify(state));
            state.beforePush={...arrival,eye:restored.eye,drifting:restored.drifting};fs.writeFileSync(path.join(output,"gravity-touch.json"),JSON.stringify(state,null,2));return state;
        }
        if(hosted&&process.argv.includes("--gravity-only"))return await require("../../qa/unity-public-zero-g.cjs")(page,output,false);
        if(process.argv.includes("--gravity-baseline")||process.argv.includes("--gravity-only"))return await require("./gravity-inputs.cjs")(page,output,process.argv.includes("--gravity-baseline"));
        if(process.argv.includes("--encoded-host")){
            await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.count===13,undefined,{timeout:150000});
            await page.locator("#ride").focus();
            await page.keyboard.down("F2");await page.waitForTimeout(240);await page.keyboard.up("F2");
            await page.waitForFunction(()=>document.getElementById("ride").upwellGraphics?.menu,undefined,{timeout:60000});
            if(Object.keys(encodedItems).length!==3||Object.values(encodedItems).some(enc=>enc!=="br")||errors.length)throw new Error("Encoded host failed: "+JSON.stringify({encodedItems,errors}));
            const packet=fs.readFileSync(path.join(site,"unity/Build/unity.data.unityweb")),decoded=zlib.brotliDecompressSync(packet);
            if(!decoded.subarray(0,32).includes("UnityWebData"))throw new Error("Bad static data package "+packet.length);
            const report={boarded:true,encodings:encodedItems,compressedBytes:packet.length,compressedSHA256:crypto.createHash("sha256").update(packet).digest("hex"),
                decodedBytes:decoded.length,decodedSHA256:crypto.createHash("sha256").update(decoded).digest("hex"),consoleErrors:errors};
            fs.writeFileSync(path.join(output,"webgl-brotli.json"),JSON.stringify(report,null,2));return report;
        }
        if(process.argv.includes("--fracture-only"))return await fractureInputs(page,output);
        const performance=await page.evaluate(()=>new Promise(resolve=>{
            const canvas=document.getElementById("ride"),gl=canvas.getContext("webgl2"),info=gl.getExtension("WEBGL_debug_renderer_info");
            const renderer=info?gl.getParameter(info.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
            let first=canvas.upwellFrame,t0=null,last=null,frames=[];
            const tick=t=>{if(!first)first=canvas.upwellFrame;if(t0===null)t0=t;else frames.push(t-last);last=t;
                if((t-t0>=4500&&frames.length>=12)||t-t0>12000){
                    const end=canvas.upwellFrame;frames.sort((a,b)=>a-b);
                    resolve({renderer,reducedBudget:document.documentElement.dataset.softwareRaster==="1",frames:frames.length,medianFrameMilliseconds:frames[Math.floor(frames.length*.5)],averageBrowserFrameMilliseconds:(t-t0)/frames.length,
                        unityFPS:first&&end&&end.seconds>first.seconds?(end.frame-first.frame)/(end.seconds-first.seconds):null,width:canvas.width,height:canvas.height});
                }
                else requestAnimationFrame(tick);};requestAnimationFrame(tick);
        }));
        await page.screenshot({path:path.join(output,outputName+".jpg"),type:"jpeg",quality:88});
        const graphics=await verifyGraphics(page,adapter==="swiftshader");
        let curtainGestures,momentSurvey;
        if(adapter==="d3d11"){
            const tap=async key=>{await page.keyboard.down(key);await page.waitForTimeout(250);await page.keyboard.up(key);await page.waitForTimeout(230);};
            const coarse=async key=>{await page.keyboard.down("Shift");await tap(key);await page.keyboard.up("Shift");};
            const fixtures=()=>page.evaluate(()=>document.getElementById("ride").upwellFrame);
            const passage=()=>page.evaluate(()=>document.getElementById("ride").upwellPassage);
            const waitMoment=async index=>{try{await page.waitForFunction(i=>document.getElementById("ride").upwellPassage?.index===i,index,{timeout:8000});}catch{throw new Error("Passage row "+index+" was not selected: "+JSON.stringify(await passage()));}return await passage();};
            const menu=async()=>{await tap("m");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.menu);};
            const survey=JSON.parse(fs.readFileSync(path.join(site,"assets/passage-moments.json"),"utf8")).moments;
            const scale=Math.max(.74,Math.min(1.6,height/850)),menuLeft=(width-500*scale)/2,menuTop=(height-650*scale)/2;
            const menuPoint=(x,y)=>({x:menuLeft+x*scale,y:menuTop+y*scale});
            const pressPanel=async p=>{await page.mouse.click(p.x,p.y,{delay:80});await page.waitForTimeout(550);};
            await menu();const firstState=await passage();
            if(firstState.count!==13)throw new Error("Unity did not load the 13 shared passage moments");
            await page.screenshot({path:path.join(output,"unity-webgl-moments.jpg"),type:"jpeg",quality:89});
            if(firstState.follow)await pressPanel(menuPoint(115,65));
            await page.waitForFunction(()=>!document.getElementById("ride").upwellPassage.follow);
            await selectMomentRow(page,2);let chosen=await waitMoment(2);
            if(chosen.view!==0||chosen.direct||Math.abs(chosen.seconds-survey[2].start)>2)throw new Error("Unfollowed row changed the passenger camera: "+JSON.stringify(chosen));
            await tap("]");await waitMoment(3);await tap("[");await waitMoment(2);
            await menu();await pressPanel(menuPoint(115,65));await page.waitForFunction(()=>document.getElementById("ride").upwellPassage.follow);
            await selectMomentRow(page,0);await waitMoment(0);
            const selected=[];
            for(let i=0;i<survey.length;i++){
                if(i)await tap("]");
                const target=await waitMoment(i);
                if(Math.abs(target.seconds-survey[i].start)>2.2)throw new Error("Incorrect moment lead-in "+survey[i].id+" "+target.seconds);
                if(["forward","earth","stars","colony","counter"].includes(survey[i].view)&&
                    (!target.direct||target.width!==width||target.height!==height||target.sky<width*.4))throw new Error("Sensor was rendered through a preview texture: "+JSON.stringify(target));
                if(survey[i].id==="bubble"&&!target.cell)throw new Error("Suggested bubble view did not open its actual cabin fixture");
                if(i===6||i===9||i===10)await page.screenshot({path:path.join(output,"unity-webgl-moment-"+survey[i].id+".jpg"),type:"jpeg",quality:90});
                selected.push({id:survey[i].id,view:target.view,seconds:target.seconds,screen:target.direct?[target.width,target.height]:null,sky:target.direct?target.sky:null});
            }
            await tap("]");const end=await waitMoment(12);if(end.seconds!==360||end.view!==0)throw new Error("The full bracket tour did not conclude with a free aisle passenger");
            await tap("1");
            await page.waitForTimeout(1300);
            const dockAim=()=>page.evaluate(()=>{const c=document.getElementById("ride");c.dispatchEvent(new Event("read-visible-aim"));return c.upwellAim;});
            const dockLens=await dockAim();const closedDock=[];
            for(let j=0;j<2;j++){
                await tap("F2");await page.waitForFunction(()=>document.getElementById("ride").upwellGraphics.menu);
                await page.mouse.click((width+420*scale)/2-48*scale,(height-402*scale)/2+25*scale,{delay:110});
                await page.waitForFunction(()=>!document.getElementById("ride").upwellGraphics.menu);await page.waitForTimeout(1200);
                const after=await dockAim();closedDock.push(after);
                if(after.zoomed!==dockLens.zoomed||Math.abs(after.lens-dockLens.lens)>.06||Math.abs(after.horizontal-dockLens.horizontal)>.06||Math.abs(after.vertical-dockLens.vertical)>.06)
                    throw new Error("A Graphics Close click operated the dock glazing: "+JSON.stringify({dockLens,after}));
            }
            await tap("[");const reverse=await waitMoment(11);if(!reverse.cell)throw new Error("Reverse from dock lost the bubble lead-in");
            await tap("]");await waitMoment(12);await coarse("[");
            await page.waitForFunction(()=>{const s=document.getElementById("ride").upwellPassage;return s.index===-1&&s.seconds>=339&&s.seconds<342;});
            await coarse("]");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage.seconds===360);
            await menu();await page.mouse.move(menuLeft+190*scale,menuTop+510*scale);
            for(let i=0;i<4;i++){await page.mouse.wheel(0,580);await page.waitForTimeout(100);}
            await tap("End");
            await page.screenshot({path:path.join(output,"unity-webgl-moments-bottom.jpg"),type:"jpeg",quality:88});
            await selectMomentRow(page,12);await waitMoment(12);
            await tap("0");await menu();await page.mouse.move(menuLeft+180*scale,menuTop+254*scale);
            for(let i=0;i<4;i++){await page.mouse.wheel(0,-580);await page.waitForTimeout(90);}
            await tap("Home");
            await selectMomentRow(page,0);await waitMoment(0);await tap("0");
            momentSurvey={count:selected.length,selected,previousFromDock:reverse.seconds,coarseBack:339,keptView:chosen.view,dockLens,closedDock};
            const contact=async kind=>{
                try{await page.waitForFunction(k=>document.getElementById("ride").upwellFrame?.curtainContact===k,kind,{timeout:6000});}
                catch{await page.screenshot({path:path.join(project,"Logs","curtain-aim-debug.jpg")});throw new Error("Physical pointer target "+kind+" was not reached: "+JSON.stringify(await fixtures()));}
            };
            const handleDrag=async(start,finish)=>{
                await page.mouse.move(start,height*.48);await tap("9");await contact(1);
                await page.mouse.down();await page.waitForTimeout(160);
                await page.mouse.move(finish,height*.48,{steps:14});await page.waitForTimeout(230);
                await page.mouse.up();await page.waitForTimeout(620);return await fixtures();
            };
            await tap("F2");await page.waitForFunction(()=>document.getElementById("ride").upwellGraphics.menu);
            await page.mouse.click((width+420*scale)/2-48*scale,(height-402*scale)/2+25*scale,{delay:95});
            await page.waitForFunction(()=>!document.getElementById("ride").upwellGraphics.menu);
            const old=await fixtures(),part=await handleDrag(width*.79,width*.67);
            if(part.railGestures<=old.railGestures||part.curtain<.035||part.curtain>.88)throw new Error("Horizontal grip did not retain a partial position: "+JSON.stringify(part));
            await page.waitForTimeout(450);const parked=await fixtures();
            if(Math.abs(part.curtain-parked.curtain)>.005)throw new Error("Released curtain drifted from its intermediate position");
            await page.screenshot({path:path.join(output,"unity-webgl-curtain-partway.jpg"),type:"jpeg",quality:87});
            const drawn=await handleDrag(width*.97,width*.03);
            if(drawn.curtain<.99)throw new Error("The pointer could not reach the drawn stop: "+JSON.stringify(drawn));
            await page.mouse.move(width*.40,height*.36);await tap("9");await contact(1);
            await page.mouse.move(width*.40+100,height*.36+79,{steps:10});await contact(2);
            const soft=await fixtures();
            await page.mouse.down();await page.waitForTimeout(270);await page.mouse.move(width*.40+137,height*.36+39,{steps:7});await page.waitForTimeout(240);
            await page.mouse.up();await page.waitForTimeout(650);
            const hem=await fixtures();if(hem.hemGestures<=soft.hemGestures||hem.curtain<.99)throw new Error("The real fabric grip moved the carrier or lost the hem: "+JSON.stringify(hem));
            const stowed=await handleDrag(width*.03,width*.97);
            if(stowed.curtain>.011)throw new Error("Reverse pointer drag missed its stowed stop: "+JSON.stringify(stowed));
            await tap("9");await contact(1);await tap("f");await tap("q");await page.waitForTimeout(700);
            const aimed=await fixtures();if(aimed.curtain<.99)throw new Error("Targeted handle inspection failed to draw the curtain");
            await tap("e");await tap("0");
            curtainGestures={partial:part.curtain,parked:parked.curtain,drawn:drawn.curtain,stowed:stowed.curtain,hemTug:hem.hemGestures>soft.hemGestures,targeted:aimed.curtain};
            await tap("7");const prior=await fixtures();await tap("q");
            await page.waitForFunction(before=>document.getElementById("ride").upwellFrame?.tests>before,prior.tests);
            await page.screenshot({path:path.join(output,"unity-webgl-accelerometer.jpg"),type:"jpeg",quality:88});await tap("e");
            await tap("8");await page.screenshot({path:path.join(output,"unity-webgl-cell-anchor.jpg"),type:"jpeg",quality:88});await tap("e");
            await tap("F1");
            await page.screenshot({path:path.join(output,"unity-webgl-controls.jpg"),type:"jpeg",quality:85});
            await tap("F1");await coarse("[");await coarse("[");await coarse("[");await tap("6");
            for(let i=0;i<7;i++)await coarse("]");
            await page.screenshot({path:path.join(output,"unity-webgl-earthward.jpg"),type:"jpeg",quality:88});
            for(let i=0;i<3;i++)await coarse("]");
            await tap("0");await tap("8");const atDock=await fixtures();await tap("q");
            await page.waitForFunction(before=>document.getElementById("ride").upwellFrame?.strokes>before,atDock.strokes);
            await page.screenshot({path:path.join(output,"unity-webgl-cell-primer.jpg"),type:"jpeg",quality:88});
            if(Math.abs(atDock.signedLoad)>.002||Math.abs(atDock.gasFraction-.23)>.001)throw new Error("GEO instrument readout is incorrect: "+JSON.stringify(atDock));
            await tap("e");await tap("c");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.view===10);
            await page.screenshot({path:path.join(output,"unity-webgl-hub-relay.jpg"),type:"jpeg",quality:93});
            await page.setViewportSize({width:442,height:790});await page.waitForTimeout(850);
            await menu();await page.screenshot({path:path.join(output,"unity-webgl-moments-portrait.jpg"),type:"jpeg",quality:90});await tap("Escape");
            for(let i=0;i<6;i++)await tap("[");
            const portrait=await waitMoment(6);
            const share=Math.tan(Math.asin(6371/(6371+portrait.km)))/(Math.tan(portrait.lens*Math.PI/360)*Math.min(1,portrait.width/portrait.height));
            if(!portrait.direct||portrait.width>=portrait.height||Math.abs(share-.78)>.006)throw new Error("Portrait Earth optics clipped the globe: "+JSON.stringify({portrait,share}));
            momentSurvey.portrait={...portrait,discFraction:share};
            await page.screenshot({path:path.join(output,"unity-webgl-earth-portrait.jpg"),type:"jpeg",quality:93});
            await page.setViewportSize({width,height});await page.goto(new URL("/unity/?verify-graphics",page.url()).href,{waitUntil:"domcontentloaded"});
            await page.getByRole("button",{name:"Enter the carriage"}).waitFor({timeout:180000});await page.getByRole("button",{name:"Enter the carriage"}).click();
            await page.waitForTimeout(1100);await fractureInputs(page,output);
        }
        const receipt={loaded:true,boarded:true,consoleErrors:errors,performance,graphics,curtainGestures,momentSurvey,log:log.filter(s=>/WebGL|wasm|Unity|renderer/i.test(s)).slice(-12)};
        if(errors.length)throw new Error(errors.join("\n"));
        if(adapter==="swiftshader"&&(!performance.reducedBudget||performance.width>456))throw new Error("Software GPU did not enter its reduced render budget");
        return receipt;
    } finally {if(browser)await browser.close();}
}
(async()=>{
    if(!hosted)await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
    try {
        if(process.argv.includes("--gravity-baseline")||process.argv.includes("--gravity-only")||process.argv.includes("--gravity-touch")){const result=await passage("d3d11",1100,690,"unity-webgl");console.log("Passenger gravity",JSON.stringify(result));return;}
        if(process.argv.includes("--encoded-host")){console.log("Static Brotli host",await passage("d3d11",1100,690,"unity-webgl"));return;}
        if(process.argv.includes("--fracture-only")){const report=await passage("d3d11",1100,690,"unity-webgl");console.log("Guarded fracture input",report.partial.force,report.coast.moving);return;}
        if(process.argv.includes("--software-only")){
            const result=await passage("swiftshader",704,440,"unity-webgl-software");
            fs.writeFileSync(path.join(graphicsFolder,"web-software.json"),JSON.stringify(result,null,2));
            console.log("Software renderer after warmup",result.graphics.warmFPS);return;
        }
        const hardware=await passage("d3d11",1100,690,"unity-webgl");
        const software=await passage("swiftshader",704,440,"unity-webgl-software");
        fs.writeFileSync(path.join(output,"webgl-checks.json"),JSON.stringify({...hardware,software},null,2));
        console.log("Hardware and software WebGL static-host receipt",hardware.performance,software.performance);
    } finally {if(server.listening)server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
