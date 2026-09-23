// Production format conversion only: retain every source pixel and its dimensions.
// Requires Node.js and FFmpeg/FFprobe on PATH. The generated PNG is never changed.
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(root, 'mod/Textures/halveth/scarlet-love-banner.png');
const target = resolve(root, 'assets/ScarletLoveBanner/Textures');
const output = resolve(target, 'Tx_de_tapestry_02.dds');
if (existsSync(output)) throw new Error('DDS already exists; preserve it or choose a new artifact before conversion.');
const png = readFileSync(source);
if (png.toString('hex',0,8) !== '89504e470d0a1a0a') throw new Error('Expected PNG source');
const width=png.readUInt32BE(16), height=png.readUInt32BE(20);
if (height !== width*2 || width>4096) throw new Error('Expected bounded portrait 1:2');
const conversion=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-i',source,'-frames:v','1','-f','rawvideo','-pix_fmt','bgra','pipe:1'],{maxBuffer:width*height*4+1024*1024});
if(conversion.status!==0) throw new Error(String(conversion.stderr));
if(conversion.stdout.length!==width*height*4) throw new Error('Unexpected pixel byte count');
// Standard legacy DDS header, uncompressed A8R8G8B8, little-endian BGRA pixels.
const header=Buffer.alloc(128);
header.write('DDS ',0,'ascii');
for(const [offset,value] of [[4,124],[8,0x100f],[12,height],[16,width],[20,width*4],
  [76,32],[80,0x41],[88,32],[92,0x00ff0000],[96,0x0000ff00],[100,0x000000ff],[104,0xff000000],[108,0x1000]]) header.writeUInt32LE(value,offset);
mkdirSync(target,{recursive:true});
writeFileSync(output,Buffer.concat([header,conversion.stdout]));
console.log(JSON.stringify({source,output,width,height,format:'DDS uncompressed BGRA32',pixelBytes:conversion.stdout.length}));
