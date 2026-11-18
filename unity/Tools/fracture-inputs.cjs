const fs=require("node:fs");
const path=require("node:path");

// All movement, hardware use, and menu actions go through the ordinary passenger controller.
// The local observer reports the real sightline/fixture state so tests can aim a physical mouse.
module.exports=async function fractureInputs(page,output){
    const dir=path.join(output,"fracture");fs.mkdirSync(dir,{recursive:true});
    const sleep=ms=>page.waitForTimeout(ms);
    await page.waitForFunction(()=>{const c=document.getElementById("ride");return c.upwellPassage?.count===13&&c.upwellFrame?.frame>4;},null,{timeout:35000});
    const key=async(k,ms=140)=>{await page.keyboard.down(k);await sleep(ms);await page.keyboard.up(k);await sleep(125);};
    const read=(id="fracture_cell")=>page.evaluate(id=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-cartridge-target",{detail:id}));return c.upwellCartridge;},id);
    const assert=(condition,message,world)=>{if(!condition)throw Error(message+" "+JSON.stringify(world));};
    let px=550,py=340,gx=.175,gy=.15;await page.mouse.move(px,py);await sleep(180);
    const turn=async(id,offsetX=0,offsetY=0)=>{
        let state=await read(id);assert(state,"No Unity observer",state);
        for(let tries=0;tries<15;tries++){
            const ex=state.yaw+offsetX,ey=state.pitch+offsetY;
            if(Math.max(Math.abs(ex),Math.abs(ey))<.48)return state;
            const dx=Math.max(-235,Math.min(235,ex/gx)),dy=Math.max(-145,Math.min(145,ey/gy));
            if(px+dx<30||px+dx>1070||py+dy<26||py+dy>664){
                // A physical mouse can be lifted while its virtual cursor is locked. Chromium
                // automation requires a real UI unlock to recenter its bounded desktop coordinates.
                await key("F2");px=dx<0?900:200;py=dy<0?535:150;await page.mouse.move(px,py);await key("F2");await sleep(230);
            }
            px+=dx;py+=dy;await page.mouse.move(px,py,{steps:5});await sleep(110);
            const next=await read(id);
            const ax=(state.yaw-next.yaw)/dx,ay=(state.pitch-next.pitch)/dy;
            if(Math.abs(dx)>3&&ax>.045&&ax<.5)gx=ax;
            if(Math.abs(dy)>3&&ay>.045&&ay<.5)gy=ay;
            state=next;
        }
        assert(Math.max(Math.abs(state.yaw+offsetX),Math.abs(state.pitch+offsetY))<4,"Could not turn to "+id,state);return state;
    };
    const walk=async id=>{
        let last=Infinity;
        for(let j=0;j<10;j++){
            const s=await turn(id);if(s.distance<.17)return;
            await key("w",Math.min(650,Math.max(70,(s.distance-.10)*1000/1.62)));
            const after=await read(id);
            assert(after.distance<last-.018||after.distance<.17,"Aisle was obstructed approaching "+id,after);last=after.distance;
        }
        throw Error("Could not reach "+id);
    };
    const aim=async id=>{
        for(const [x,y] of [[0,0],[-1.7,0],[1.7,0],[0,1.7],[0,-2.5],[-3,1],[3,1]]){
            const s=await turn(id,x,y);if(s.focus===id)return s;
        }
        throw Error("Actual triangle ray did not reach "+id+": "+JSON.stringify(await read(id)));
    };
    const until=async(test,ms=3500)=>{let state;for(let t=0;t<ms;t+=100){state=await read();if(test(state))return state;await sleep(100);}throw Error("Cartridge state timed out: "+JSON.stringify(state));};
    const shot=label=>page.screenshot({path:path.join(dir,label+".jpg"),type:"jpeg",quality:92});

    await page.waitForFunction(()=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-cartridge-target",{detail:"fracture_cell"}));return !!c.upwellCartridge;},null,{timeout:12000});
    await key("b");let state=await read();assert(!state.unlocked&&!state.inspecting,"Locked hatch allowed a bench visit",state);
    await walk("crossway");await walk("berth-aisle");await aim("locker_drawer");await key("e");await until(s=>s.drawer>.96);
    await aim("access_card");await key("e");await until(s=>s.card);await key("e");
    await walk("reader-aisle");await aim("card_reader");await key("e");await until(s=>s.unlocked);await sleep(850);
    await walk("service-aisle");await aim("fracture_press");
    await page.keyboard.down("e");await sleep(420);
    const partial=await read();await page.keyboard.up("e");await sleep(480);
    assert(partial.force>28&&partial.force<310&&!partial.broken,"Short physical press did not show a recoverable load",partial);
    await key("e",1050);await until(s=>s.broken);await sleep(850);
    const settled=await read();assert(settled.peak===320&&settled.contacts>0&&settled.height<-.022&&settled.escape<.0015,"Earth-weight fragments failed to settle inside the clear guard",settled);
    await sleep(1200);let resting,quiet,atRest=false;
    for(let attempt=0;attempt<7&&!atRest;attempt++){
        resting=await read();await sleep(470);quiet=await read();
        atRest=resting.moving===0&&quiet.moving===0&&quiet.contacts===resting.contacts&&Math.abs(quiet.height-resting.height)<.000025;
    }
    assert(atRest,"Grounded ceramic continued to move or tick after settling",{resting,quiet});
    await key("b");await until(s=>s.inspecting);await shot("web-02-ground-settlement");
    await key("r",75);await until(s=>s.blinds>.92,1000);await shot("web-03-exchange");await until(s=>s.exchanges===1&&!s.broken&&s.blinds<.02);
    for(let i=0;i<14 && (await read()).seconds<360;i++)await key("]",110);
    const dock=await read();assert(dock.seconds===360&&dock.inspecting&&dock.g<.002,"Could not carry the same physical bench view to dock",dock);
    await page.keyboard.down("q");await sleep(520);const orbitalLoad=await read();await shot("web-04-dock-loading");
    assert(orbitalLoad.force>40&&!orbitalLoad.broken,"Native focused Q did not load the cam",orbitalLoad);
    await until(s=>s.broken);await page.keyboard.up("q");await sleep(210);const coast=await read();await shot("web-05-dock-fracture");
    assert(coast.moving>=3&&coast.peak===320&&coast.escape<.0015,"Dock fragments lost their independent motion or containment",coast);
    await sleep(420);await key("r");await until(s=>s.exchanges===2&&!s.broken&&s.blinds<.01);await key("e");await until(s=>!s.inspecting);
    const delivered=await page.evaluate(()=>performance.getEntriesByType("resource").map(r=>new URL(r.name).pathname).find(n=>n.endsWith(".data.unityweb")||n.endsWith(".data"))||(typeof config!=="undefined"?config.dataUrl:""));
    const result={delivered,unlockedWithCrewKey:true,trianglePress:true,partial,settled,resting,quiet,orbitalLoad,coast};
    fs.writeFileSync(path.join(dir,"web-fracture.json"),JSON.stringify(result,null,2));return result;
};
