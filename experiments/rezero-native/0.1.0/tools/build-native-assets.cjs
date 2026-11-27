// New REZERO assets. Native 0.51 menu filename/handle contracts, independently drawn.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const sharp=require('sharp');
const base=path.resolve(__dirname,'..');
const mod=path.join(base,'mod');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
for(const d of ['Textures/rezero','Splash','MyGUI'])fs.mkdirSync(path.join(mod,d),{recursive:true});
fs.mkdirSync(path.join(base,'art-source'),{recursive:true});
async function dds(source,destination){
 const {data,info}=await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const b=Buffer.alloc(128+data.length);b.write('DDS ',0,'ascii');
 const set=(offset,n)=>b.writeUInt32LE(n>>>0,offset);
 set(4,124);set(8,0x100f);set(12,info.height);set(16,info.width);set(20,info.width*4);
 set(76,32);set(80,0x41);set(88,32);set(92,0xff0000);set(96,0xff00);set(100,0xff);set(104,0xff000000);set(108,0x1000);
 for(let i=0;i<data.length;i+=4){b[128+i]=data[i+2];b[129+i]=data[i+1];b[130+i]=data[i];b[131+i]=data[i+3]}
 fs.writeFileSync(destination,b);return {width:info.width,height:info.height,sha256:sha(b)};
}
const background=`<svg xmlns="http://www.w3.org/2000/svg" width="2048" height="1152" viewBox="0 0 2048 1152">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0b1119"/><stop offset=".5" stop-color="#173239"/><stop offset="1" stop-color="#071015"/></linearGradient>
<radialGradient id="horizon"><stop stop-color="#be9d71" stop-opacity=".38"/><stop offset="1" stop-color="#303e43" stop-opacity="0"/></radialGradient>
<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#14292f"/><stop offset="1" stop-color="#050b10"/></linearGradient></defs>
<rect width="2048" height="1152" fill="url(#sky)"/><ellipse cx="1320" cy="530" rx="970" ry="620" fill="url(#horizon)"/>
<circle cx="1440" cy="180" r="51" fill="#d0c2a7" opacity=".20"/><circle cx="1458" cy="165" r="48" fill="#183137"/>
<path d="M0 622L124 551 232 582 377 487 522 529 669 382 823 472 967 322 1050 438 1160 378 1300 505 1482 360 1682 505 1820 416 2048 564V870H0Z" fill="#17272d"/>
<path d="M0 680L171 597 323 638 532 570 715 673 885 615 1017 687 1263 597 1452 658 1617 589 1796 652 2048 576V881H0Z" fill="#0f1d24"/>
<path d="M0 768Q454 716 913 766T2048 747V1152H0Z" fill="url(#water)"/>
<g stroke="#718b85" stroke-width="1" opacity=".13"><path d="M230 791H941M718 805H1648M514 840H1498M811 879H1560M209 921H918M1240 924H1980"/></g>
<path d="M0 841L106 769 175 864 259 817 327 948 425 893 513 1011 619 1050 803 1152H0Z" fill="#050b0f"/>
<path d="M2048 761L1941 736 1833 812 1781 790 1694 957 1666 1152H2048Z" fill="#050b0f"/>
<g fill="none" stroke="#caa876"><path d="M868 214L1024 91 1180 214 1024 337Z" stroke-width="2" opacity=".38"/><path d="M928 214L1024 139 1120 214 1024 288Z" stroke-width="1" opacity=".7"/></g>
<text x="1024" y="421" text-anchor="middle" fill="#e4dac5" font-family="Georgia,serif" font-size="104" letter-spacing="17">MORROWIND</text>
<text x="1024" y="471" text-anchor="middle" fill="#a9b7b2" font-family="Segoe UI,sans-serif" font-size="22" letter-spacing="7">ASCHE · WASSER · STERNENLICHT</text>
<path d="M744 506H1304" stroke="#b99363" opacity=".6"/>
</svg>`;
async function main(){
 const manifest=[];
 const white=await sharp({create:{width:4,height:4,channels:4,background:'#ffffff'}}).png().toBuffer();
 fs.writeFileSync(path.join(mod,'Textures/rezero/white.png'),white);
 const bg=Buffer.from(background,'utf8');fs.writeFileSync(path.join(base,'art-source/mainmenu.svg'),bg);
 const bgPNG=await sharp(bg).png().toBuffer();fs.writeFileSync(path.join(base,'art-source/mainmenu.png'),bgPNG);
 manifest.push({path:'Textures/menu_morrowind.dds',...(await dds(bgPNG,path.join(mod,'Textures/menu_morrowind.dds')))});
 fs.writeFileSync(path.join(mod,'Splash/rezero_ashwater.png'),bgPNG);
 const panel=Buffer.from('<svg width="800" height="120" xmlns="http://www.w3.org/2000/svg"><rect width="800" height="120" rx="5" fill="#0d1820" fill-opacity=".95"/><path d="M1 0V120" stroke="#c49b65" stroke-width="3"/><path d="M799 0V120" stroke="#324850" stroke-width="2"/></svg>');
 fs.writeFileSync(path.join(mod,'Textures/rezero/loading_panel.png'),await sharp(panel).png().toBuffer());
 const labels={return:'WEITER',newgame:'NEUES SPIEL',savegame:'SPEICHERN',loadgame:'SPIEL LADEN',options:'OPTIONEN',credits:'MITWIRKENDE',exitgame:'BEENDEN'};
 for(const [id,label] of Object.entries(labels)) for(const state of ['', '_over','_pressed']){
  const fill=state==='_pressed'?'#203435':state==='_over'?'#213038':'#101c23',ink=state?'#f1d4a0':'#d7ded6';
  const source=Buffer.from(`<svg width="480" height="64" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="1" width="478" height="47" rx="3" fill="${fill}" fill-opacity=".95"/><path d="M8 47H472" stroke="${state?'#d2af78':'#485d62'}"/><text x="240" y="31" text-anchor="middle" fill="${ink}" font-family="Segoe UI,sans-serif" font-size="20" letter-spacing="3">${label}</text></svg>`);
  fs.writeFileSync(path.join(base,`art-source/menu_${id}${state}.svg`),source);
  const png=await sharp(source).png().toBuffer();
  manifest.push({path:`Textures/menu_${id}${state}.dds`,...(await dds(png,path.join(mod,`Textures/menu_${id}${state}.dds`)))});
 }
 fs.writeFileSync(path.join(base,'NATIVE_ART_MANIFEST.json'),JSON.stringify({version:'0.1.0',sourceKind:'NEW_VECTOR_AND_RGBA_DDS_ART',nativeContractTag:'openmw-0.51.0',assets:manifest,originalGameImagesImported:false,claimCeiling:'ART_GENERATED_PENDING_NATIVE_VISUAL_QA'},null,2));
 console.log(JSON.stringify({assets:manifest.length,background:'art-source/mainmenu.png',mod}));
}
main().catch(e=>{console.error(e);process.exit(1)});
