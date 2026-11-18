let catalogue;
function loadCatalogue(){
  return catalogue??=fetch('./assets/passage-moments.json').then(response=>{
    if(!response.ok)throw Error('Could not load the passage moments');
    return response.json();
  }).catch(error=>{catalogue=null;throw error;});
}
export async function loadMoments(){return (await loadCatalogue()).moments;}
export async function linkedObservation(id){
  const {moments,observations=[]}=await loadCatalogue();
  return moments.find(m=>m.id===id)??observations.find(m=>m.id===id);
}

// Inside a moment’s lead-in, Back goes to the preceding moment. Farther
// along the route it replays the most recent event. Forward always advances.
export function adjacentMoment(moments,seconds,direction){
  const firstAhead=moments.findIndex(m=>m.start>seconds+.08);
  if(direction>0)return firstAhead;
  const current=(firstAhead<0?moments.length:firstAhead)-1;
  if(current<0)return -1;
  return seconds<=moments[current].event+1.25?current-1:current;
}

export function passageTime(seconds){
  return Math.floor(seconds/60)+':'+String(Math.floor(seconds)%60).padStart(2,'0');
}
