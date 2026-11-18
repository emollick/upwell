// Unity draws its moment list into the game canvas. Locate the highlighted
// top edge of each full-width row in the actual IMGUI pixels. Exclude the
// shorter shortcut buttons above the scroll view, then verify the selection.
module.exports=async function selectMomentRow(page,index,{touch=false}={}){
    const current=()=>page.evaluate(()=>document.getElementById("ride").upwellPassage);
    let state=await current();
    async function key(k){await page.keyboard.down(k);await page.waitForTimeout(165);await page.keyboard.up(k);}
    if(!state.menu){await key("m");await page.waitForFunction(()=>document.getElementById("ride").upwellPassage?.menu);}
    const atBottom=index>=state.count/2;
    await key(atBottom?"End":"Home");
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const image=(await page.screenshot({type:"png",scale:"css"})).toString("base64");
    const result=await page.evaluate(async ({image,index,atBottom})=>{
        const ride=document.getElementById("ride"),box=ride.getBoundingClientRect(),unit=Math.max(.74,Math.min(1.6,ride.height/850));
        const geometricWidth=ride.width/unit,geometricHeight=ride.height/unit;
        const panelW=Math.min(500,geometricWidth-24),panelH=Math.min(650,geometricHeight-26);
        const x=(geometricWidth-panelW)/2,y=(geometricHeight-panelH)/2;
        const screenX=n=>box.left+(x+n)*unit*box.width/ride.width,screenY=n=>box.top+(y+n)*unit*box.height/ride.height;
        const canvas=document.createElement("canvas");
        const bytes=Uint8Array.from(atob(image),ch=>ch.charCodeAt(0));
        const bitmap=await createImageBitmap(new Blob([bytes],{type:"image/png"}));
        canvas.width=bitmap.width;canvas.height=bitmap.height;const ctx=canvas.getContext("2d");ctx.drawImage(bitmap,0,0);bitmap.close();
        const w=canvas.width,data=ctx.getImageData(0,0,w,canvas.height).data,css=unit*box.height/ride.height;
        const lo=Math.round(screenX(25)),hi=Math.round(screenX(panelW-60)),first=Math.ceil(screenY(77)),last=Math.floor(screenY(panelH-12));
        const gap=Math.max(1,Math.round(2*css)),starts=[];let lastMatch=-1e4;
        for(let yy=first;yy<last;yy++){
            let bright=0,n=0;
            // The shortcut pair has a dark, wide center gutter. A real row
            // has the same bright border spanning both halves and its center.
            const center=screenX(panelW/2);
            const mid=Math.round(center);
            const shade=k=>data[4*(yy*w+k)]-data[4*((yy-gap)*w+k)];
            for(let xx=lo;xx<=hi;xx+=5){if(shade(xx)>39)bright++;n++;}
            const centerLuma=data[4*(yy*w+mid)];
            if(bright/n>.78&&shade(mid)>39&&centerLuma>100){
                if(yy-lastMatch>Math.max(5,7*css))starts.push(yy);
                lastMatch=yy;
            }
        }
        // Full rows have a following boundary or enough space below their
        // top for a real title. This removes a partially clipped bottom row.
        const titleOffset=Math.round(17*css),usable=starts.filter(top=>top+titleOffset<last-2);
        const position=atBottom?usable.length-(ride.upwellPassage.count-index):index;
        return {rows:usable,last,point:position>=0&&position<usable.length?{x:screenX(150),y:usable[position]+titleOffset}:null};
    },{image,index,atBottom});
    if(!result.point)throw Error("No complete drawn moment row "+index+" / "+JSON.stringify(result));
    if(touch)await page.touchscreen.tap(result.point.x,result.point.y);
    else await page.mouse.click(result.point.x,result.point.y,{delay:115});
    try{
        await page.waitForFunction(i=>{const m=document.getElementById("ride").upwellPassage;return !m.menu&&m.index===i;},index,{timeout:10000});
    }catch{
        throw Error("Actual moment row "+index+" was not selected: "+JSON.stringify({result,state:await current()}));
    }
    state=await current();return {state,point:result.point,rows:result.rows};
};
