mergeInto(LibraryManager.library, {
  UpwellPhotoStatus: function(message,count,open) {
    var text=UTF8ToString(message),canvas=document.getElementById("ride");
    if(canvas)canvas.upwellPhotoJournal={count:count,open:!!open,message:text};
    document.body.classList.toggle("photo-review",!!open);
    var status=document.getElementById("nativePhotoNotice");
    if(status){status.textContent=text;clearTimeout(status.hidePhotoNotice);status.hidePhotoNotice=setTimeout(function(){status.textContent="";},3200);}
  },
  UpwellLoadAudit: function(data){document.getElementById("ride").upwellLoad=JSON.parse(UTF8ToString(data));},
  UpwellFrameSample: function(frame, seconds, signedLoad, gasFraction, tests, strokes, curtain, contact, railGestures, hemGestures) {
    var canvas=document.getElementById("ride");if(canvas)canvas.upwellFrame={frame:frame,seconds:seconds,signedLoad:signedLoad,gasFraction:gasFraction,tests:tests,strokes:strokes,curtain:curtain,curtainContact:contact,railGestures:railGestures,hemGestures:hemGestures};
  },
  UpwellMomentSample: function(clock,count,selected,menu,follows,watch,cell,direct,w,h,sky,lens,km,aboard,rate,realTime) {
    var canvas=document.getElementById("ride");
    if(canvas)canvas.upwellPassage={seconds:clock,count:count,index:selected,menu:!!menu,follow:!!follows,view:watch,cell:!!cell,direct:!!direct,width:w,height:h,sky:sky,lens:lens,km:km,aboard:aboard,shipRate:clock>=360?0:rate,realTime:!!realTime};
    var onward=document.getElementById("galley-onward");if(onward)onward.hidden=cell!==2||selected!==count-2||!!menu;
  },
  UpwellGraphicsSample: function(visible,choices,software,cast,aa,cabinSamples,opticSamples,cabinScene,cabinFiltered,sensorScene,sensorFiltered,sky,steps) {
    var canvas=document.getElementById("ride");
    if(canvas)canvas.upwellGraphics={menu:!!visible,edges:choices&15,shadows:(choices>>4)&15,atmosphere:(choices>>8)&15,contact:(choices>>12)&15,software:!!software,shadowQuality:cast,msaa:aa,cabinSamples:cabinSamples,opticSamples:opticSamples,cabinScene:cabinScene,cabinFiltered:cabinFiltered,sensorScene:sensorScene,sensorFiltered:sensorFiltered,skyWidth:sky,skySteps:steps};
  },
  UpwellSoftwareGraphics: function() {return document.documentElement.dataset.softwareRaster==="1"?1:0;},
  UpwellCartridgeRestAudit: function(detail) {var c=document.getElementById("ride");if(c.upwellCartridge)c.upwellCartridge.shardStates=UTF8ToString(detail);},
  UpwellCartridgeAudit: function(focus,yaw,pitch,distance,card,unlocked,drawer,inspecting,force,peak,stroke,broken,breaks,exchanges,blinds,contacts,height,g,escape,seconds,moving) {
    document.getElementById("ride").upwellCartridge={focus:UTF8ToString(focus),yaw:yaw,pitch:pitch,distance:distance,card:!!card,unlocked:!!unlocked,drawer:drawer,
      inspecting:!!inspecting,force:force,peak:peak,stroke:stroke,broken:!!broken,breaks:breaks,exchanges:exchanges,blinds:blinds,contacts:contacts,height:height,g:g,escape:escape,seconds:seconds,moving:moving};
  },
  UpwellEdgeAudit: function(width,height,repeat,changed,samples,held,optical) {
    var canvas=document.getElementById("ride");
    if(canvas)canvas.upwellEdgeAudit={width:width,height:height,repeat:repeat,changed:changed,samples:samples,held:!!held,optical:!!optical};
  },
  UpwellAimAudit: function(horizontal,vertical,atOptic,inHand,lens,zoomed) {
    document.getElementById("ride").upwellAim={horizontal:horizontal,vertical:vertical,atOptic:!!atOptic,inHand:!!inHand,lens:lens,zoomed:!!zoomed};
  },
  UpwellReturnToSeat: function () {
    if (document.pointerLockElement) document.exitPointerLock();
    window.location.assign(new URL("../", window.location.href).href);
  }
});
