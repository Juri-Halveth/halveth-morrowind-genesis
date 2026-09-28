-- Development scene only. No script is registered in the normal game profile.
local world=require('openmw.world')
local types=require('openmw.types')
local util=require('openmw.util')
local core=require('openmw.core')
local CELL='HALVETH Visual Field'
local entries={
 {kind='NPC',id='fargoth',name='Fargoth',scale=1.5},
 {kind='NPC',id='eldafire',name='Eldafire',scale=1.5},
 {kind='NPC',id='arrille',name='Arrille',scale=1.5},
 {kind='Static',id='flora_bc_tree_01',name='Baum',scale=.22},
 {kind='Static',id='terrain_rock_bc_01',name='Fels',scale=.6},
 {kind='Static',id='ex_common_house_tall_01',name='Haus',scale=.35},
 {kind='Container',id='flora_muckspunge_01',name='Sumpfpflanze',scale=2},
 {kind='Container',id='chest_small_01',name='Truhe',scale=3},
 {kind='Armor',id='chitin cuirass',name='Ruestung',scale=4},
 {kind='Clothing',id='common_shirt_04',name='Kleidung',scale=4},
 {kind='Weapon',id='steel broadsword',name='Waffe',scale=4},
 {kind='Book',id='bookskill_enchant1',name='Buch',scale=5},
 {kind='Apparatus',id='apparatus_a_retort_01',name='Alchemie',scale=4},
 {kind='Light',id='light_com_lamp_01',name='Lampe',scale=3},
 {kind='Door',id='ex_common_door_01',name='Tuer',scale=1.6},
 {kind='Static',id='flora_bc_tree_02',name='Baumvariante',scale=.22},
}
local objects,trees,cache,actors={},{},{},{}
local ground
local gap,page,stage,ready=2200,0,0,false
local started,lastStage,lastReport,lastState,queued=-1,-1,-1,-1,false
local destinations={4,8,12}
local function record(model)
 if not cache[model] then cache[model]=world.createRecord(types.Static.createRecordDraft({model=model})).id end
 return cache[model]
end
local function position(i)
 return util.vector3(((i-1)%4-1.5)*gap,(math.floor((i-1)/4)-1.5)*gap,0)
end
local function clear(list)
 for _,o in ipairs(list) do if o:isValid() then o:remove() end end
end
local function names()
 local result={}
 for i=1,16 do local e=entries[page*16+i];result[i]=e and e.name or 'Leer' end
 return result
end
local function report()
 for _,p in ipairs(world.players) do
  if p.cell and p.cell.name==CELL then p:sendEvent('HALVETH_FieldState',{
   gap=gap,page=page,pages=math.ceil(#entries/16),stage=stage,names=names(),
   actors=(function() local a={} for _,item in ipairs(actors) do
    if item.object:isValid() then a[#a+1]={slot=item.slot,position=item.object.position} end
   end return a end)()}) end
 end
end
local function grow(cell)
 clear(trees);trees={}
 for i=1,16 do
  local model='meshes/halveth/visual_field/branch-'..(i-1)..'-'..stage..'.dae'
  local tree=world.createObject(record(model))
  tree:teleport(cell,position(i)+util.vector3(540,0,0))
  trees[#trees+1]=tree
 end
end
local function populate(cell)
 clear(objects);objects={};actors={};queued=true
 if not ground then
  ground=world.createObject(record('meshes/halveth/visual_field/ground.dae'))
  ground:teleport(cell,util.vector3(0,0,0))
 end
 ground:setScale(gap/2200)
 for i=1,16 do
  local pos=position(i)
  local e=entries[page*16+i]
  if e then
   local template=assert(types[e.kind].records[e.id],'Missing field record: '..e.id)
   local rid
   if e.kind=='NPC' then
    local key='npc:'..e.id
    if not cache[key] then
     cache[key]=world.createRecord(types.NPC.createRecordDraft({template=template,
       name='Studie: '..e.name,mwscript='',isEssential=true,isRespawning=false,
       servicesOffered={},travelDestinations={}})).id
    end
    rid=cache[key]
   elseif e.kind=='Light' then rid=e.id
   else rid=record(assert(template.model,'Missing model: '..e.id)) end
   local object=world.createObject(rid)
   object:setScale(e.scale)
   object:teleport(cell,pos+util.vector3(0,0,4))
   objects[#objects+1]=object
   if e.kind=='NPC' then
    object:addScript('scripts/halveth_visual_field/actor.lua')
    actors[#actors+1]={object=object,slot=i,start=pos}
   end
  end
 end
 grow(cell);report()
 print('HALVETH_FIELD_PAGE page='..page..' objects='..#objects..' entries='..#entries)
end
local function populateOrStop(cell)
 local ok,err=pcall(populate,cell)
 if not ok then
  clear(objects);clear(trees);objects={};actors={};trees={};queued=false
  print('ERROR: HALVETH_FIELD_BUILD '..tostring(err))
  core.quit()
 end
 return ok
end
local function request(data)
 if type(data)~='table' or not ready then return end
 local p=data.player
 if not p or not types.Player.objectIsInstance(p) or not p.cell or p.cell.name~=CELL then return end
 if data.kind=='page' and (data.delta==1 or data.delta==-1) then
  page=(page+data.delta)%math.ceil(#entries/16);populateOrStop(p.cell)
 elseif data.kind=='gap' and (data.delta==1 or data.delta==-1) then
  gap=math.max(1600,math.min(10000,gap+data.delta*400));populateOrStop(p.cell)
 elseif data.kind=='stage' then stage=(stage+1)%5;grow(p.cell);report()
 end
end
return {engineHandlers={onUpdate=function()
 if #world.players==0 then return end
 local p=world.players[1]
 if not p.cell or p.cell.name~=CELL then return end
 if ready then
  local now=core.getRealTime()
  if queued then
   queued=false
   for i,item in ipairs(actors) do
    item.object:sendEvent('HALVETH_FieldWalk',{destination=position(destinations[i]),
     returnPosition=item.start,enabled=true})
   end
  end
  if stage<4 and now-lastStage>=8 then
   stage=stage+1;lastStage=now;grow(p.cell);report()
   print('HALVETH_FIELD_GROWTH stage='..stage)
  end
  if now-lastReport>=10 then
   lastReport=now
   for _,item in ipairs(actors) do if item.object:isValid() then
    print('HALVETH_FIELD_MOTION slot='..item.slot..' distance='..(item.object.position-item.start):length())
   end end
  end
  if now-lastState>=.2 then lastState=now;report() end
  return
 end
 ready=true
 local seen={}
 for _,e in ipairs(entries) do seen[e.id:lower()]=true end
 local more={}
 for _,r in ipairs(types.Static.records) do
  if r.model and not seen[r.id:lower()] and not r.id:lower():match('^generated:') then
   more[#more+1]={kind='Static',id=r.id,name=r.id,scale=.3}
  end
 end
 table.sort(more,function(a,b)return a.id<b.id end)
 for _,e in ipairs(more) do entries[#entries+1]=e end
 world.setGameTimeScale(10)
 started=core.getRealTime();lastStage=started;lastReport=started
 p:teleport(p.cell,util.vector3(0,-gap*.4,10))
 populateOrStop(p.cell)
end},eventHandlers={HALVETH_FieldRequest=request}}
