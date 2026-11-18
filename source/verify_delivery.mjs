import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {MeshoptDecoder} from '../web/assets/vendor/meshopt.js';

const receipts=JSON.parse(await readFile(process.argv[2],'utf8'));
await MeshoptDecoder.ready;
let count=0;
for(const record of receipts){
  const f=await readFile(record.stage),len=f.readUInt32LE(12);
  const doc=JSON.parse(f.subarray(20,20+len)), buffers=[f.subarray(28+len)];
  for(const def of doc.buffers.slice(1)) buffers.push(def.uri ? await readFile(path.resolve(path.dirname(record.path),def.uri)) : null);
  for(const [i,view] of doc.bufferViews.entries()){
    const ext=view.extensions?.EXT_meshopt_compression;
    let output;
    if(ext){
      const data=buffers[ext.buffer].subarray(ext.byteOffset??0,(ext.byteOffset??0)+ext.byteLength);
      output=new Uint8Array(ext.byteStride*ext.count);
      MeshoptDecoder.decodeGltfBuffer(output,ext.count,ext.byteStride,data,ext.mode,ext.filter);
    } else {
      const data=buffers[view.buffer],off=view.byteOffset??0;output=data.subarray(off,off+view.byteLength);
    }
    if(createHash('sha256').update(output).digest('hex')!==record.hashes[i]) throw new Error(`${record.path} view ${i} changed`);
    count++;
  }
}
console.log(`Browser decoder verified ${count} geometry and image buffer views byte for byte.`);
