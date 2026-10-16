// Record of the one-time export of reviewed imagegen pigment into the ancestor.
// The generated candidate was deleted after export; this is not a runtime tool.
'use strict';
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const {decode, thumbnail} = require('../gathering/thumbnail.js');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const ancestorHash = '135cad1805e7b55690b61ed57d01c05079452308879950c73fc231d1709e6c6d';
const candidateHash = 'bba60088df61a43feb2b59af65b77642141f3097c1834a191fba5d8ce23ab77b';
const oldBytes = fs.readFileSync('artifacts/line-4/wall-v16.png');
const candidateBytes = fs.readFileSync('artifacts/line-4/candidate37.png');
if (hash(oldBytes) !== ancestorHash || hash(candidateBytes) !== candidateHash)
  throw new Error('wall or generated pigment differs from the reviewed input');
const old = decode(oldBytes), candidate = decode(candidateBytes);
if (old.width !== 1254 || old.height !== 1254 || old.channels !== 3 ||
    candidate.width !== 1254 || candidate.height !== 1254 || candidate.channels !== 3)
  throw new Error('unexpected image size or mode');

// The image editor also retouched the surrounding rock. Keep only its two
// charcoal trails, ochre pebble, and chalk dabs in this empty-rock patch.
const bounds = [345, 183, 480, 260];
const pixels = Buffer.from(old.pixels);
let changed = 0, box = [1254, 1254, -1, -1];
for (let y = bounds[1]; y <= bounds[3]; y++) for (let x = bounds[0]; x <= bounds[2]; x++) {
  const top = x >= 347 && x <= 464 && y >= 185 && y <= 211;
  const pebble = x >= 394 && x <= 429 && y >= 205 && y <= 232;
  const bottom = x >= 360 && x <= 478 && y >= 230 && y <= 258;
  if (!top && !pebble && !bottom) continue;
  const p = (y * old.width + x) * 3;
  const [ar, ag, ab] = old.pixels.subarray(p, p + 3);
  const [br, bg, bb] = candidate.pixels.subarray(p, p + 3);
  const dark = (top || bottom) && ag - bg > 17 && ar - br > 18 && br < 110 && bg < 79 && bb < 66;
  const red = pebble && ag - bg > 17 && ar - br > 11 && br >= 65 && br > bg * 1.45 && bg < 77;
  const chalk = bottom && x >= 404 && x <= 455 && bg - ag > 24 && bb - ab > 24 && br >= bg;
  if (!dark && !red && !chalk) continue;
  const strength = chalk ? Math.min(0.9, (bg - ag) / 40) : Math.min(0.94, (ag - bg) / 35);
  for (let channel = 0; channel < 3; channel++)
    pixels[p + channel] = Math.round(old.pixels[p + channel] * (1 - strength) +
                                     candidate.pixels[p + channel] * strength);
  if (pixels[p] !== ar || pixels[p + 1] !== ag || pixels[p + 2] !== ab) {
    changed++;
    box = [Math.min(box[0], x), Math.min(box[1], y), Math.max(box[2], x), Math.max(box[3], y)];
  }
}
if (changed < 500 || changed > 8000) throw new Error('unexpected pigment area');

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const value of bytes) {
    crc ^= value;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(name, data) {
  const kind = Buffer.from(name), size = Buffer.alloc(4), crc = Buffer.alloc(4);
  size.writeUInt32BE(data.length); crc.writeUInt32BE(crc32(Buffer.concat([kind, data])));
  return Buffer.concat([size, kind, data, crc]);
}
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(old.width); ihdr.writeUInt32BE(old.height, 4); ihdr[8] = 8; ihdr[9] = 2;
const stride = old.width * 3, scan = Buffer.alloc(old.height * (stride + 1));
for (let y = 0; y < old.height; y++) pixels.copy(scan, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
const png = Buffer.concat([Buffer.from('89504e470d0a1a0a', 'hex'), chunk('IHDR', ihdr),
  chunk('IDAT', zlib.deflateSync(scan, {level: 9})), chunk('IEND', Buffer.alloc(0))]);
const jpeg = thumbnail(png, 512, 75);
if (jpeg.length >= 100000) throw new Error('JPEG exceeds 100 KB');
fs.writeFileSync('artifacts/line-4/wall-v17.png', png);
fs.writeFileSync('artifacts/line-4/wall.png', png);
fs.writeFileSync('dist/line-4/37.jpg', jpeg);
const checks = {
  ancestor_sha256: ancestorHash, generated_sha256: candidateHash,
  png: {paths: ['artifacts/line-4/wall-v17.png', 'artifacts/line-4/wall.png'],
    format: 'PNG', mode: 'RGB', dimensions: [1254, 1254], bytes: png.length, sha256: hash(png)},
  jpeg: {path: 'dist/line-4/37.jpg', format: 'JPEG', dimensions: [512, 512],
    bytes: jpeg.length, sha256: hash(jpeg)},
  preservation: {rectangle: bounds, changed_pixels: changed, changed_bounds: box,
    outside_rectangle_changed_pixels: 0},
  visual_review_required: true, visual_review_completed: false,
  unmet_visual_requirements: []
};
fs.writeFileSync('line-4/image-checks37.json', JSON.stringify(checks, null, 2) + '\n');
console.log(JSON.stringify(checks, null, 2));
