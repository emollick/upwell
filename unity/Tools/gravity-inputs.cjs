const fs=require("node:fs");
const path=require("node:path");
const selectMomentRow=require("./moment-row.cjs");
module.exports=async function gravityInputs(page,output,baseline){
    if(!baseline)fs.mkdirSync(path.join(output,"gravity"),{recursive:true});
    const pause=ms=>page.waitForTimeout(ms);
    const key=async(k,ms=150)=>{await page.keyboard.down(k);await pause(ms);await page.keyboard.up(k);await pause(250);};
    const read=()=>page.evaluate(()=>{
        const c=document.getElementById("ride");
        function witness(id){c.dispatchEvent(new CustomEvent("read-cartridge-target",{detail:id}));return {...c.upwellCartridge};}
        const flat=witness("crossway"),cell=witness("fracture_cell");
        const height=Math.sin((cell.pitch-flat.pitch)*Math.PI/180)*cell.distance;
        return {seconds:cell.seconds,g:cell.g,view:c.upwellPassage.view,relativeEyeHeight:height};
    });
    await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.count===13);
    const start=await read();await key("n");const afterN=await read();await key("p");const afterP=await read();
    const load=(id="field_glasses")=>page.evaluate(id=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-load-target",{detail:id}));return c.upwellLoad;},id);
    const target=id=>page.evaluate(id=>{const c=document.getElementById("ride");c.dispatchEvent(new CustomEvent("read-cartridge-target",{detail:id}));return c.upwellCartridge;},id);
    const requireState=(ok,description,data)=>{if(!ok)throw Error(description+" "+JSON.stringify(data));};
    let x=635,y=287,gainX=.175,gainY=.15;
    const aim=async id=>{
        let observed=await target(id);
        for(let n=0;n<15;n++){
            if(Math.max(Math.abs(observed.yaw),Math.abs(observed.pitch))<.47)return observed;
            const dx=Math.max(-240,Math.min(240,observed.yaw/gainX)),dy=Math.max(-152,Math.min(152,observed.pitch/gainY));
            if(x+dx<32||x+dx>1060||y+dy<30||y+dy>665){
                await key("F2");x=dx<0?930:190;y=dy<0?530:166;await page.mouse.move(x,y);await key("F2");await pause(230);
            }
            x+=dx;y+=dy;await page.mouse.move(x,y,{steps:6});await pause(150);const next=await target(id);
            const gx=(observed.yaw-next.yaw)/dx,gy=(observed.pitch-next.pitch)/dy;
            if(Math.abs(dx)>3&&gx>.04&&gx<.5)gainX=gx;if(Math.abs(dy)>3&&gy>.04&&gy<.5)gainY=gy;
            observed=next;
        }
        return observed;
    };
    let secured,ground,tour;
    if(!baseline){
        requireState(afterN.seconds>=32&&afterN.seconds<35&&afterP.seconds<3,"N/P did not move actual route stages",{afterN,afterP});
        const passage=()=>page.evaluate(()=>document.getElementById("ride").upwellPassage);
        for(let i=1;i<=11;i++){await key("]");await page.waitForFunction(index=>document.getElementById("ride").upwellPassage.index===index,i);}
        await page.waitForFunction(()=>document.getElementById("ride").upwellPassage.seconds===360);
        await key("]");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage.index===12);
        const freeDock=await passage(),freeBody=await load();
        requireState(freeDock.view===0&&freeBody.drifting&&freeBody.eye.y>2.27,"Full bracket tour failed to restore the free body before pushing",{freeDock,freeBody});
        await key("1");const chosen=await load();await key("[");await key("]");await pause(350);
        const anchored=await passage(),anchorBody=await load();
        requireState(anchored.view===1&&!anchorBody.drifting&&Math.abs(chosen.eye.y-anchorBody.eye.y)<.002,"Suggested tour moved a deliberately chosen window station",{anchored,anchorBody});
        tour={freeBeforePush:freeDock.view,freeHeight:freeBody.eye.y,explicitWindowAfterDock:anchored.view};
        await key("0");await selectMomentRow(page,0);await key("0");await pause(850);
        const boarding=await load();
        requireState((await passage()).view===0&&boarding.eye.y<1.67&&boarding.g>.98&&!boarding.drifting,
            "Default direct-dock trial did not start on foot at the anchor",boarding);
        await selectMomentRow(page,12);await pause(750);
        let dockEye=await load();requireState(dockEye.eye.y>2.28&&dockEye.drifting,"Boarding-origin free passenger missed braking",dockEye);
        await page.screenshot({path:path.join(output,"gravity/00-default-dock.jpg"),type:"jpeg",quality:92});
        await selectMomentRow(page,0);
        await pause(900);await key("0");await pause(800);
        await page.mouse.move(x,y);await key("1");let hand=await aim("field_glasses");
        requireState(hand.focus==="field_glasses","Could not reach the optical kit",hand);
        await key("f");await key("e");await key("0");
        for(let i=0;i<8;i++){let waypoint=await aim("crossway");if(waypoint.distance<.19)break;await key("w",Math.min(580,Math.max(85,(waypoint.distance-.10)*660)));}
        await aim("berth-aisle");await key("i");
        requireState((await load()).held==="field_glasses","I did not produce the stowed optical kit",await load());
        await key("g");await pause(1450);ground=await load();secured=await load("mug");
        requireState(ground.free&&ground.item.y<.29,"A release did not fall onto the ordinary deck",ground);
    }
    await selectMomentRow(page,12);await pause(850);
    const selectedDock=await read();await key("0");const beforePush=await read();
    const destination=baseline?null:await load();
    if(!baseline){
        requireState(selectedDock.view===0&&selectedDock.g<.00001,"Walking passenger lost the aisle at the terminal",selectedDock);
        requireState(destination.free&&destination.item.y>ground.item.y+.55,"Previously settled instrument missed the braking passage",{ground,destination});
        const mounted=await load("mug");requireState(Math.abs(mounted.item.y-secured.item.y)<.009,"Mounted vessel was shifted by route navigation",{secured,mounted});
        await page.screenshot({path:path.join(output,"gravity/web-braced.jpg"),type:"jpeg",quality:92});
    }
    await key("Space",baseline?650:150);const afterPush=await read();
    await pause(340);const coast=await read();
    if(!baseline){
        requireState(afterPush.relativeEyeHeight<beforePush.relativeEyeHeight-.10&&coast.relativeEyeHeight<afterPush.relativeEyeHeight-.10,"Passenger failed to push off the overhead surface or coast",{beforePush,afterPush,coast});
        await page.screenshot({path:path.join(output,"gravity/web-floating.jpg"),type:"jpeg",quality:92});
    }
    await key("[");const reverse=await read();
    await key("]");const returned=await read();
    await page.keyboard.down("Shift");await key("]");await page.keyboard.up("Shift");await pause(550);const extraStage=await read();
    const report={start,afterN,afterP,tour,ground,selectedDock,destination,beforePush,afterPush,coast,reverse,returned,extraStage};
    if(!baseline){
        requireState(extraStage.seconds===360&&reverse.g>.01,"End stage wrapped or reverse braking was absent",{reverse,extraStage});
        for(let i=0;i<10;i++)await key("p");
        await key("0");await pause(1400);report.restored=await load();
        requireState(report.restored.g>.98&&report.restored.item.y<.29&&report.restored.eye.y<1.67,"Backtracking failed to restore terrestrial load to the aisle and same item",report.restored);
    }
    fs.writeFileSync(path.join(output,baseline?"gravity-baseline.json":"gravity-webgl.json"),JSON.stringify(report,null,2));
    return report;
};
