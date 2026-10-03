(() => {
  'use strict';
  const canvas = document.querySelector('#world');
  const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, powerPreference: 'high-performance' });
  const veil = document.querySelector('#veil');
  if (!gl) { veil.innerHTML = '<span>WEBGL 2 WIRD BENÖTIGT</span>'; return; }

  const vertex = `#version 300 es
  in vec2 a_position;
  out vec2 v_uv;
  void main(){ v_uv=a_position*.5+.5; gl_Position=vec4(a_position,0.,1.); }`;
  const fragment = `#version 300 es
  precision highp float;
  in vec2 v_uv; out vec4 frag;
  uniform vec2 u_size; uniform float u_time; uniform float u_phase;
  uniform vec3 u_camera; uniform float u_yaw; uniform float u_pitch;
  uniform float u_flash;
  const float FAR=55.0;
  float smin(float a,float b,float k){float h=max(k-abs(a-b),0.)/k;return min(a,b)-h*h*k*.25;}
  float ellipsoid(vec3 p,vec3 r){float k0=length(p/r);float k1=length(p/(r*r));return k0*(k0-1.)/k1;}
  float capsule(vec3 p,vec3 a,vec3 b,float r){vec3 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h)-r;}
  float sphere(vec3 p,float r){return length(p)-r;}
  vec3 field4(vec3 p,float seed){
    float w=.38*sin(u_time*.23+seed+u_phase*6.2831853)+.15*cos(p.x*.21+p.z*.14-u_time*.17);
    float a=.095*sin(u_time*.15+seed*.7);
    float x=p.x*cos(a)-w*sin(a); float nw=p.x*sin(a)+w*cos(a);
    float b=.07*cos(u_time*.12+seed*1.3);
    float z=p.z*cos(b)-nw*sin(b); float w2=p.z*sin(b)+nw*cos(b);
    float scale=1./(1.+.09*w2);
    return vec3(x,p.y+.045*w2,z)*scale;
  }
  vec2 scene(vec3 p){
    float wave=.16*sin(p.x*.25+u_time*.22)+.11*cos(p.z*.32-u_time*.16)+.06*sin(p.x*.51+p.z*.4);
    float d=(p.y-wave)*.86; float id=1.;
    for(int i=0;i<11;i++){
      float fi=float(i); float side=mod(fi,2.)*2.-1.;
      vec3 center=vec3(side*(2.15+mod(fi*1.73,5.7)),0.,4.0+floor(fi*.5)*4.1+mod(fi*1.7,1.9));
      vec3 q=field4(p-center,fi*1.73);
      float trunk=capsule(q,vec3(0.,-.05,0.),vec3(.08,2.8,0.),.16+mod(fi,3.)*.025);
      float branches=min(capsule(q,vec3(0.,1.4,0.),vec3(-.58,2.25,.03),.075),capsule(q,vec3(.02,1.55,0.),vec3(.65,2.4,-.04),.07));
      float crown=ellipsoid(q-vec3(.08,3.25,0.),vec3(.83,.96,.72));
      crown=smin(crown,ellipsoid(q-vec3(-.37,3.06,.04),vec3(.69,.76,.67)),.42);
      crown=smin(crown,ellipsoid(q-vec3(.47,3.3,-.08),vec3(.68,.8,.71)),.38);
      float tree=min(trunk,min(branches,crown));
      if(tree<d){d=tree;id=tree==crown?3.:2.;}
    }
    for(int j=0;j<8;j++){
      float fj=float(j); vec3 c=vec3(sin(fj*14.1+1.)*4.5,.2+mod(fj,3.)*.08,3.5+fj*3.1);
      vec3 q=p-c; q.x+=.25*sin(u_time*.4+fj);
      float rock=ellipsoid(q,vec3(.45+mod(fj,2.)*.28,.25,.34));
      if(rock<d){d=rock;id=4.;}
    }
    // An original amber squirrel: body, head, curled tail and four feet animate together.
    float sx=1.4*sin(u_time*.11+u_phase*6.28), sz=4.6+1.5*cos(u_time*.11+u_phase*6.28);
    vec3 sq=p-vec3(sx,.0,sz); sq=field4(sq,2.4);
    float breathe=.018*sin(u_time*3.2);
    float body=ellipsoid(sq-vec3(0.,.43+breathe,0.),vec3(.22,.34,.18));
    float head=sphere(sq-vec3(.05,.79+breathe,.03),.16);
    float tail1=capsule(sq,vec3(-.05,.48,-.07),vec3(-.28,.79,-.1),.105);
    float tail2=capsule(sq,vec3(-.28,.79,-.1),vec3(-.22,1.14,-.12),.12);
    float tail3=capsule(sq,vec3(-.22,1.14,-.12),vec3(.02,1.27,-.12),.13);
    float tail=min(tail1,min(tail2,tail3));
    float ears=min(sphere(sq-vec3(-.025,.94,.03),.055),sphere(sq-vec3(.13,.91,.03),.045));
    float feet=min(capsule(sq,vec3(-.13,.15,0.),vec3(-.15,.29,0.),.045),capsule(sq,vec3(.13,.14,.02),vec3(.13,.3,.02),.045));
    float squirrel=min(min(body,head),min(tail,min(ears,feet)));
    if(squirrel<d){d=squirrel;id=(tail<squirrel+.005)?6.:5.;}
    for(int g=0;g<9;g++){
      float fg=float(g); vec3 orb=vec3(sin(fg*31.7+u_time*.31)*5.,1.35+sin(u_time*.5+fg*4.)*.9,2.+fg*4.8+cos(fg*17.)*1.);
      float gd=sphere(p-orb,.055+max(0.,sin(u_time*1.2+fg))*.03);
      if(gd<d){d=gd;id=7.;}
    }
    return vec2(d,id);
  }
  vec3 normalAt(vec3 p){vec2 e=vec2(.0015,0.);return normalize(vec3(scene(p+e.xyy).x-scene(p-e.xyy).x,scene(p+e.yxy).x-scene(p-e.yxy).x,scene(p+e.yyx).x-scene(p-e.yyx).x));}
  float shadow(vec3 ro,vec3 rd,float mint,float maxt){float res=1.,t=mint;for(int i=0;i<30;i++){float h=scene(ro+rd*t).x;res=min(res,12.*h/t);t+=clamp(h,.025,.55);if(h<.002||t>maxt)break;}return clamp(res,.14,1.);}
  float ao(vec3 p,vec3 n){float occ=0.,sca=1.;for(int i=0;i<4;i++){float h=.08+.14*float(i);float d=scene(p+n*h).x;occ+=(h-d)*sca;sca*=.62;}return clamp(1.-occ*1.65,.35,1.);}
  void main(){
    vec2 uv=(gl_FragCoord.xy-.5*u_size)/u_size.y;float t=u_time;
    vec3 ro=u_camera;float cy=cos(u_yaw),sy=sin(u_yaw),cp=cos(u_pitch),sp=sin(u_pitch);
    vec3 rd=normalize(vec3(uv.x,uv.y,1.5));rd=vec3(rd.x*cy+rd.z*sy,rd.y,rd.z*cy-rd.x*sy);rd=vec3(rd.x,rd.y*cp-rd.z*sp,rd.y*sp+rd.z*cp);
    float dist=0.,id=0.;vec3 p=ro;bool hit=false;
    for(int i=0;i<92;i++){p=ro+rd*dist;vec2 h=scene(p);if(h.x<.0025){id=h.y;hit=true;break;}dist+=max(h.x*.78,.009);if(dist>FAR)break;}
    vec3 sky=mix(vec3(.025,.09,.075),vec3(.23,.31,.22),smoothstep(-.2,.58,rd.y));
    float sun=pow(max(dot(rd,normalize(vec3(-.35,.72,.3))),0.),50.);sky+=vec3(.58,.39,.17)*sun*.45;
    vec3 col=sky;
    if(hit){
      vec3 n=normalAt(p),light=normalize(vec3(-.42,.82,-.3));
      float diff=max(dot(n,light),0.)*shadow(p+n*.012,light,.05,22.);
      float fill=max(dot(n,normalize(vec3(.55,.28,.7))),0.)*.23;
      float ambient=ao(p,n);vec3 base;
      if(id<1.5){float grain=sin(p.x*17.+sin(p.z*12.))*sin(p.z*19.);base=mix(vec3(.035,.105,.082),vec3(.13,.22,.14),.5+.25*grain);}
      else if(id<2.5)base=vec3(.18,.105,.052);
      else if(id<3.5){float fleck=sin(p.x*12.+p.z*9.)*sin(p.y*14.);base=mix(vec3(.095,.23,.14),vec3(.28,.39,.21),.5+.3*fleck);}
      else if(id<4.5)base=vec3(.16,.23,.2);
      else if(id<5.5)base=vec3(.64,.31,.11);
      else if(id<6.5)base=vec3(.91,.5,.17);
      else base=vec3(.79,.82,.52);
      float fres=pow(1.-max(dot(n,-rd),0.),3.);
      col=base*(.22+diff*.95+fill)*ambient+vec3(.25,.49,.29)*fres*.34;
      if(id>4.5&&id<6.5)col+=vec3(.37,.13,.025)*fres*.5;
      if(id>6.5)col=base*(1.3+diff*.4);
      float fog=1.-exp(-dist*.032);col=mix(col,sky,fog);
    }
    float pulse=exp(-abs(length(p.xz-u_camera.xz)-mod(t*3.4,28.))*.27)*u_flash;
    col+=vec3(.11,.47,.29)*pulse*.16;
    float vignette=1.-.22*dot(uv,uv);col*=vignette;
    col=col/(col+vec3(.82));col=pow(max(col,0.),vec3(.91));
    frag=vec4(col,1.);
  }`;

  function shader(type, source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
  try{
    const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    const loc=gl.getAttribLocation(program,'a_position');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
    const U={size:gl.getUniformLocation(program,'u_size'),time:gl.getUniformLocation(program,'u_time'),phase:gl.getUniformLocation(program,'u_phase'),camera:gl.getUniformLocation(program,'u_camera'),yaw:gl.getUniformLocation(program,'u_yaw'),pitch:gl.getUniformLocation(program,'u_pitch'),flash:gl.getUniformLocation(program,'u_flash')};
    const stage=document.querySelector('.stage'),intro=document.querySelector('.intro'),enter=document.querySelector('#enter'),pulseBtn=document.querySelector('#pulse');
    const phaseLabel=document.querySelector('#phase'),note=document.querySelector('#note'),noteIndex=document.querySelector('#note-index');
    const controls=document.querySelector('#controls'),mobile=document.querySelector('#mobile-pad'),stateLabel=document.querySelector('#state-label');
    let start=performance.now(),yaw=0,pitch=-.08,phase=.12,flash=0,entered=false,walk=0,step=0,audio=null;
    const pos=[0,1.38,-7.5],keys=new Set();
    const notes=[
      'Der Hain erkennt deinen ersten Schritt und ordnet sein Licht neu.',
      'Ein Wesen mit bernsteinfarbenem Schweif folgt einem eigenen Rhythmus.',
      'Boden, Licht und Bewegung bilden zusammen ein neues Ereignis.',
      'Die vierte Achse verändert den Ort, ohne seine Erinnerung zu löschen.',
      'Ein winziger Impuls reicht: die Welt wächst aus ihren Beziehungen.'
    ];
    function resize(){const dpr=Math.min(devicePixelRatio||1,1.45);const w=Math.max(2,Math.floor(innerWidth*dpr)),h=Math.max(2,Math.floor(innerHeight*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}}
    function enterWorld(){entered=true;stage.classList.add('entered');controls.hidden=false;mobile.hidden=!matchMedia('(pointer:coarse)').matches;stateLabel.textContent='WORLD IS LISTENING';if(document.pointerLockElement!==canvas&&matchMedia('(pointer:fine)').matches)canvas.requestPointerLock?.();}
    enter.addEventListener('click',enterWorld);
    canvas.addEventListener('click',()=>{if(entered&&matchMedia('(pointer:fine)').matches)canvas.requestPointerLock?.();});
    document.addEventListener('pointerlockchange',()=>{if(document.pointerLockElement===canvas)stateLabel.textContent='FIELD LINKED';else if(entered)stateLabel.textContent='WORLD IS LISTENING';});
    document.addEventListener('mousemove',e=>{if(document.pointerLockElement===canvas){yaw+=e.movementX*.0022;pitch=Math.max(-.52,Math.min(.42,pitch-e.movementY*.0018));}});
    document.addEventListener('keydown',e=>{if(['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','Space'].includes(e.code)){keys.add(e.code);e.preventDefault();}});
    document.addEventListener('keyup',e=>keys.delete(e.code));
    pulseBtn.addEventListener('click',()=>{flash=1;phase=(phase+.173)%1;step=(step+1)%notes.length;noteIndex.textContent=String(step+1).padStart(2,'0');note.textContent=notes[step];stateLabel.textContent='NEW RELATION OBSERVED';if(audio)audio.osc.forEach((osc,i)=>{osc.frequency.setTargetAtTime([55,82.41,110][i]*(1+phase*.06),audio.ctx.currentTime,.6);});});
    document.querySelectorAll('[data-move]').forEach(button=>{const code={forward:'KeyW',back:'KeyS',left:'KeyA',right:'KeyD'}[button.dataset.move];button.addEventListener('pointerdown',e=>{e.preventDefault();keys.add(code);});for(const ev of ['pointerup','pointercancel','pointerleave'])button.addEventListener(ev,()=>keys.delete(code));});
    document.querySelector('#sound').addEventListener('click',async e=>{const b=e.currentTarget;const on=b.getAttribute('aria-pressed')!=='true';
      if(on){try{const ctx=new AudioContext();await ctx.resume();const master=ctx.createGain();master.gain.value=.035;master.connect(ctx.destination);const osc=[];for(const [i,f] of [55,82.41,110].entries()){const node=ctx.createOscillator(),gain=ctx.createGain();node.type=i===1?'triangle':'sine';node.frequency.value=f;gain.gain.value=[.46,.25,.16][i];node.connect(gain).connect(master);node.start();osc.push(node);}audio={ctx,osc,master};b.setAttribute('aria-pressed','true');b.querySelector('span').textContent='ON';stateLabel.textContent='LOCAL AMBIENT FIELD';}catch(err){stateLabel.textContent='AUDIO NOT AVAILABLE';console.warn(err);}}
      else if(audio){const old=audio;audio=null;old.master.gain.setTargetAtTime(0,old.ctx.currentTime,.12);setTimeout(()=>old.ctx.close(),700);b.setAttribute('aria-pressed','false');b.querySelector('span').textContent='OFF';stateLabel.textContent=entered?'WORLD IS LISTENING':'WORLD FORMING';}
    });
    function tick(now){resize();const time=(now-start)*.001;const speed=(keys.has('ShiftLeft')?.09:.055);
      const forward=(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0),strafe=(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0);
      if(entered){pos[0]+=(Math.sin(yaw)*forward+Math.cos(yaw)*strafe)*speed;pos[2]+=(Math.cos(yaw)*forward-Math.sin(yaw)*strafe)*speed;pos[0]=Math.max(-6,Math.min(6,pos[0]));pos[2]=Math.max(-8,Math.min(16,pos[2]));if(keys.has('KeyQ'))phase=(phase-.0016+1)%1;if(keys.has('KeyE'))phase=(phase+.0016)%1;if(keys.has('Space'))walk=Math.min(walk+.035,.32);else walk=Math.max(walk-.025,0);}
      flash=Math.max(0,flash-.004);gl.useProgram(program);gl.uniform2f(U.size,canvas.width,canvas.height);gl.uniform1f(U.time,time);gl.uniform1f(U.phase,phase);gl.uniform3f(U.camera,pos[0],pos[1]+Math.sin(walk*Math.PI)*.14,pos[2]);gl.uniform1f(U.yaw,yaw);gl.uniform1f(U.pitch,pitch);gl.uniform1f(U.flash,flash);gl.drawArrays(gl.TRIANGLES,0,6);
      phaseLabel.textContent='PHASE '+(phase*360).toFixed(2).padStart(6,'0')+'°';requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    setTimeout(()=>veil.classList.add('done'),850);
  }catch(error){console.error(error);veil.innerHTML='<span>FIELD ERROR · '+String(error.message).replace(/[<>]/g,'')+'</span>';}
})();
