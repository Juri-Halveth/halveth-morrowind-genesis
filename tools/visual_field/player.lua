local self=require('openmw.self')
local core=require('openmw.core')
local camera=require('openmw.camera')
local util=require('openmw.util')
local ui=require('openmw.ui')
local input=require('openmw.input')
local async=require('openmw.async')
local I=require('openmw.interfaces')
local state={gap=2200,page=0,pages=1,stage=0,names={},actors={}}
local selected,yaw,overview=1,0,true
local window,label,controlsLabel,started,last=nil,nil,nil,nil,nil
local frames,total=0,0
local function updateLabel()
 if not label then return end
 label.props.text='HALVETH · GRAFIKFELD  '..(state.page+1)..'/'..state.pages
  ..'  |  '..(state.names[selected] or 'Laden')..'  |  T+'..state.stage
  ..'  |  Freiraum '..state.gap..'  |  '..(overview and 'Gesamt' or 'Nah')
 window:update()
end
local function request(kind,delta)
 core.sendGlobalEvent('HALVETH_FieldRequest',{player=self.object,kind=kind,delta=delta})
end
local function control(text,x,width,fn)
 return {type=ui.TYPE.Text,template=I.MWUI.templates.textNormal,
  props={position=util.vector2(x,70),size=util.vector2(width,36),text=text,textSize=22},
  events={mouseClick=async:callback(function()
   fn();updateLabel()
   print('HALVETH_FIELD_CLICK action='..text..' overview='..tostring(overview)..' selected='..selected..' yaw='..yaw)
  end)}}
end
local function key(k)
 if not self.cell or self.cell.name~='HALVETH Visual Field' then return end
 local c=k.code
 if c==input.KEY.N then overview=not overview
 elseif c==input.KEY.LeftArrow then selected=(selected-2)%16+1
 elseif c==input.KEY.RightArrow then selected=selected%16+1
 elseif c==input.KEY.UpArrow then selected=(selected-5)%16+1
 elseif c==input.KEY.DownArrow then selected=(selected+3)%16+1
 elseif c==input.KEY.Q then yaw=yaw-math.pi/8
 elseif c==input.KEY.E then yaw=yaw+math.pi/8
 elseif c==input.KEY.Equals or c==input.KEY.NP_Plus then request('gap',1)
 elseif c==input.KEY.Minus or c==input.KEY.NP_Minus then request('gap',-1)
 elseif c==input.KEY.PageUp then request('page',-1)
 elseif c==input.KEY.PageDown then request('page',1)
 elseif c==input.KEY.G then request('stage')
 else return end
 print('HALVETH_FIELD_CONTROL key='..c..' overview='..tostring(overview)..' selected='..selected..' yaw='..yaw)
 updateLabel()
end
return {eventHandlers={HALVETH_FieldState=function(s)state=s;updateLabel()end},
engineHandlers={onKeyPress=key,onFrame=function()
 if not self.cell or self.cell.name~='HALVETH Visual Field' then return end
 local now=core.getRealTime()
 if not started then started=now end
 local t=now-started
 if not window then
  I.Controls.overrideMovementControls(true)
  I.Controls.overrideCombatControls(true)
  I.Controls.overrideUiControls(true)
  label={type=ui.TYPE.Text,props={text='',textSize=24,textColor=util.color.rgb(.92,.96,1)}}
  controlsLabel={type=ui.TYPE.Text,props={position=util.vector2(0,34),textSize=20,
   text='N: Gesamt/Nah · Pfeile: Objekt · Q/E: Drehen · +/-: Freiraum · Bild hoch/runter: Seite · G: Wachstum',
   textColor=util.color.rgb(.92,.96,1)}}
  window=ui.create({type=ui.TYPE.Container,layer='Windows',
   props={position=util.vector2(25,25),size=util.vector2(1440,110)},content=ui.content({label,controlsLabel,
    control('[Gesamt / Nah]',0,200,function()overview=not overview end),
    control('[Objekt <]',215,150,function()selected=(selected-2)%16+1 end),
    control('[Objekt >]',375,150,function()selected=selected%16+1 end),
    control('[Drehen]',535,150,function()yaw=yaw+math.pi/8 end),
    control('[Weiter]',695,150,function()request('gap',1)end),
    control('[Naeher]',855,150,function()request('gap',-1)end),
    control('[Seite >]',1015,150,function()request('page',1)end),
    control('[Wachstum]',1175,180,function()request('stage')end)
   })})
  updateLabel()
 end
 if t>8 then
  local gate=I.HALVETHMicrophone
  if gate and gate.isOpen and gate.isOpen() then gate.decline() end
 end
 local target=util.vector3(0,0,0)
 local radius,height=state.gap*2.45,state.gap*2.5
 if not overview then
  target=util.vector3(((selected-1)%4-1.5)*state.gap,(math.floor((selected-1)/4)-1.5)*state.gap,125)
  for _,actor in ipairs(state.actors or {}) do
   if actor.slot==selected then target=actor.position+util.vector3(0,0,125) end
  end
  radius,height=570,90
 end
 local pos=target+util.vector3(math.sin(yaw)*radius,-math.cos(yaw)*radius,height)
 camera.setMode(camera.MODE.Static,true);camera.setStaticPosition(pos)
 camera.setYaw(yaw);camera.setPitch(math.atan(height/radius));camera.showCrosshair(false)
 if last and t>10 and t<35 then frames=frames+1;total=total+now-last end
 if t>=35 and frames>0 then print('HALVETH_FIELD_SAMPLE frames='..frames..' meanFps='..(frames/total));frames=0 end
 last=now
 -- A preview runner can replace this literal with a finite QA duration.
 local duration=0 -- FIELD_DURATION
 if duration>0 and t>=duration then print('HALVETH_FIELD_DONE');core.quit() end
end}}
