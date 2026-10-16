// Re-encode only large inherited gallery miniatures, entirely in memory.
// Input/output: JSON object of record paths to JPEG data URLs on stdin/stdout.
'use strict';
const fs = require('node:fs');
const decode = require('./vendor/jpeg-js/decoder.js');
const encode = require('./vendor/jpeg-js/encoder.js');
const input = fs.readFileSync(0);
if (input.length > 1000000) throw new Error('preview input too large');
const previews = JSON.parse(input.toString('utf8'));
for (const [key, source] of Object.entries(previews)) {
  if (!/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(source)) throw new Error('invalid preview');
  // Keep already compact previews byte-identical. Recompression is one-time.
  if (source.length < 700) continue;
  const old = decode(Buffer.from(source.split(',')[1], 'base64'), {
    maxResolutionInMP: 1, maxMemoryUsageInMB: 16, tolerantDecoding: false
  });
  if (old.width !== old.height) throw new Error('preview must be square');
  const size = Math.min(16, old.width), data = Buffer.alloc(size * size * 4, 255);
  for (let y=0;y<size;y++) for(let x=0;x<size;x++) {
    const x0=Math.floor(x*old.width/size), x1=Math.floor((x+1)*old.width/size);
    const y0=Math.floor(y*old.height/size), y1=Math.floor((y+1)*old.height/size);
    const sum=[0,0,0], count=(x1-x0)*(y1-y0);
    for(let sy=y0;sy<y1;sy++)for(let sx=x0;sx<x1;sx++)for(let c=0;c<3;c++)sum[c]+=old.data[(sy*old.width+sx)*4+c];
    for(let c=0;c<3;c++)data[(y*size+x)*4+c]=Math.round(sum[c]/count);
  }
  previews[key]='data:image/jpeg;base64,'+encode({width:size,height:size,data},4).data.toString('base64');
}
process.stdout.write(JSON.stringify(previews));
