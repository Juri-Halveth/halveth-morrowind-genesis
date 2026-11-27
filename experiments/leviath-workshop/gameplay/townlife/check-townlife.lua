-- MIT. Declared engine doubles: these checks do not start or emulate OpenMW.
local root=assert(arg[1],'Candidate root required')
local C=assert(loadfile(root..'/mod/scripts/veyra_townlife/config.lua'))()
local count=0
local function check(name,fn)
    fn();count=count+1;print('TOWNMODEL|PASS|'..name)
end
local function clone(value)
    if type(value)~='table'then return value end
    local result={};for key,child in pairs(value)do result[key]=clone(child)end;return result
end
local vectorMeta={}
local function vector(x,y,z)
    return setmetatable({x=x,y=y,z=z or 0},vectorMeta)
end
function vectorMeta.__sub(a,b)return vector(a.x-b.x,a.y-b.y,a.z-b.z)end
function vectorMeta.__add(a,b)return vector(a.x+b.x,a.y+b.y,a.z+b.z)end
function vectorMeta.__index(_,name)
    if name=='length'then return function(v)return math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z)end end
end
local util={vector3=vector,vector2=vector,color={rgb=function(...)return{...}end}}
local function actor()
    local context={now=0,paused=false,nav=true,starts={},removals=0,reports={},package=nil,flee=false}
    local self={id='own-dynamic-id',recordId='own-dynamic-record',contentFile=nil,dead=false,
        position=vector(C.locations.home_garden.x,C.locations.home_garden.y,C.locations.home_garden.z)}
    self.object=self;function self:isValid()return true end;function self:isActive()return context.active end
    local core={isWorldPaused=function()return context.paused end,getSimulationTime=function()return context.now end,
        sendGlobalEvent=function(name,data)context.reports[#context.reports+1]={name=name,data=data}end}
    local AI={startPackage=function(data)context.starts[#context.starts+1]=data;context.package=data end,
        removePackages=function(name)assert(name=='Travel');context.removals=context.removals+1
            if context.package and context.package.type=='Travel'then context.package=nil end end,
        getActivePackage=function()return context.package end,isFleeing=function()return context.flee end}
    local types={NPC={objectIsInstance=function(o)return o==self end},Actor={
        isDead=function(o)return o.dead end,getPathfindingAgentBounds=function(o)assert(o==self);return'OWN_BOUNDS'end}}
    local nearby={NAVIGATOR_FLAGS={Walk=1,OpenDoor=2},FIND_PATH_STATUS={Success='SUCCESS'},
        findNearestNavMeshPosition=function(point,options)
            assert(options.agentBounds=='OWN_BOUNDS');if context.nav then return point end end,
        findPath=function(_,point,options)
            assert(options.agentBounds=='OWN_BOUNDS')
            return context.nav and'SUCCESS'or'UNAVAILABLE',{point}
        end}
    local modules={['openmw.core']=core,['openmw.self']=self,['openmw.types']=types,
        ['openmw.nearby']=nearby,['openmw.util']=util,['openmw.interfaces']={AI=AI},
        ['scripts.veyra_townlife.config']=C}
    local old=require;require=function(name)return assert(modules[name],name)end
    local result=assert(loadfile(root..'/mod/scripts/veyra_townlife/actor.lua'))();require=old
    context.script=result;context.self=self
    context.meta={schema=C.saveSchema,boundEntrySha256=C.boundEntrySha256,
        role='garden',actorId=self.id,recordId=self.recordId}
    result.engineHandlers.onInit(context.meta)
    function context:activate()
        self.active=true;self.script.engineHandlers.onActive()
    end
    function context:authorize(place,seq)
        self.script.eventHandlers.VEYRA_TownEnabled({enabled=true})
        self.script.eventHandlers.VEYRA_TownGoal({seq=seq or 1,place=place or'field',position=C.locations[place or'field']})
    end
    function context:tick(seconds)
        self.now=self.now+(seconds or 0.5);self.script.engineHandlers.onUpdate()
    end
    function context:state()return self.script.interface.getState()end
    return context
end
check('CUSTOM_IDENTITY_AND_DELAYED_ACTIVE_HANDSHAKE',function()
    local a=actor();a:authorize();a:tick();assert(#a.starts==0)
    a:activate();assert(a.reports[#a.reports].data.kind=='READY')
    assert(a.reports[#a.reports].data.seq==nil);a:authorize();a:tick();assert(#a.starts==1)
end)
check('TRAVEL_REQUIRES_POSITION_BOUND_GOAL',function()
    local a=actor();a:activate();a.script.eventHandlers.VEYRA_TownEnabled({enabled=true})
    a.script.eventHandlers.VEYRA_TownGoal({seq=1,place='field',position={x=0,y=0,z=0}})
    a:tick();assert(#a.starts==0)
end)
check('NATIVE_TRAVEL_DESTINATION_CONTRACT',function()
    local a=actor();a:activate();a:authorize();a:tick()
    local request=a.starts[1];assert(request.type=='Travel'and request.destPosition)
    assert(request.cancelOther and not request.isRepeat and request.target==nil)
    assert(a:state().phase=='TRAVEL_STARTED'and a:state().totalMeasuredDistance==0)
end)
check('STATIONARY_REQUEST_IS_NOT_ARRIVAL',function()
    local a=actor();a:activate();a:authorize();a:tick();a:tick(5)
    assert(a:state().phase~='ARRIVED_OBSERVED'and a:state().totalMeasuredDistance==0)
end)
check('SAMPLED_HORIZONTAL_MOVE_AND_ARRIVAL',function()
    local a=actor();a:activate();a:authorize('water');a:tick()
    a.self.position=vector(C.locations.water.x,C.locations.water.y,C.locations.water.z);a:tick()
    assert(a:state().phase=='ARRIVED_OBSERVED'and a:state().windowDistance>=64)
end)
check('INITIAL_PROXIMITY_IS_POSITION_ONLY',function()
    local a=actor();a:activate();a:authorize('home_garden');a:tick()
    assert(a:state().phase=='AT_DESTINATION_POSITION_ONLY'and#a.starts==0)
end)
check('VERTICAL_DROP_CANNOT_EARN_WALK_DISTANCE',function()
    local a=actor();a:activate();a:authorize();a:tick()
    a.self.position=a.self.position+vector(0,0,100);a:tick()
    assert(a:state().totalMeasuredDistance==0 and a:state().phase~='ARRIVED_OBSERVED')
end)
check('LARGE_JUMP_HOLD_SURVIVES_RELOAD',function()
    local a=actor();a:activate();a:authorize();a:tick()
    a.self.position=a.self.position+vector(1000,0,0);a:tick()
    assert(a:state().phase=='POSITION_JUMP_HOLD')
    local saved=a.script.engineHandlers.onSave();a.script.engineHandlers.onLoad(saved)
    a:activate();a:authorize();a:tick();assert(a:state().phase=='POSITION_JUMP_HOLD'and#a.starts==1)
end)
check('TWO_REPLANS_THEN_STALLED_RETAINED',function()
    local a=actor();a:activate();a:authorize();a:tick()
    for _=1,5 do a:tick(13);a:tick(1)end
    assert(#a.starts==3 and a:state().replans==2 and a:state().phase=='STALLED')
    local saved=a.script.engineHandlers.onSave();a.script.engineHandlers.onLoad(saved)
    a:activate();a:authorize();a:tick();assert(#a.starts==3 and a:state().phase=='STALLED')
end)
check('ASYNC_NAV_UNAVAILABLE_WAITS_WITHOUT_AI_WRITE',function()
    local a=actor();a:activate();a:authorize();a.nav=false;a:tick();a:tick(10)
    assert(#a.starts==0 and a:state().phase=='WAIT_NAV');a.nav=true;a:tick(1);assert(#a.starts==1)
end)
check('PAUSE_PREVENTS_NEW_TRAVEL_AND_SAMPLING',function()
    local a=actor();a:activate();a:authorize();a.paused=true;a:tick(30)
    assert(#a.starts==0 and a:state().totalMeasuredDistance==0)
    a.paused=false;a:tick();assert(#a.starts==1)
end)
check('COMBAT_DEFER_PRESERVES_COMBAT_PACKAGE',function()
    local a=actor();a:activate();a:authorize();a.package={type='Combat'}
    local removals=a.removals;a:tick(30)
    assert(#a.starts==0 and a.removals==removals and a.package.type=='Combat')
    assert(a:state().phase=='COMBAT_DEFERRED');a.package=nil;a:tick();assert(#a.starts==1)
end)
check('DISABLED_REENTRY_NEEDS_FRESH_AUTHORITY',function()
    local a=actor();a:activate();a:authorize();a:tick()
    a.active=false;a.script.engineHandlers.onInactive();a:activate();a:tick(2)
    assert(#a.starts==1 and a:state().awaitAuthority)
    a.script.eventHandlers.VEYRA_TownEnabled({enabled=false});a:tick()
    assert(a:state().phase=='WAIT_OWNER'and#a.starts==1)
end)
check('SAVE_RESUMES_IDENTITY_AND_EXPLICIT_SAMPLE_GAP',function()
    local a=actor();a:activate();a:authorize();a:tick()
    a.self.position=a.self.position+vector(100,100,0);a:tick()
    local measured=a:state().totalMeasuredDistance;local saved=a.script.engineHandlers.onSave()
    a.script.engineHandlers.onLoad(saved);a:activate();a:authorize();a:tick()
    assert(a:state().actorId=='own-dynamic-id'and a:state().seq==1)
    assert(a:state().totalMeasuredDistance==measured and a:state().windowDistance==0)
    assert(a:state().observationContinuity=='SAVE_RELOAD_GAP')
end)
check('UNKNOWN_SAVE_HOLD_PERSISTS_THROUGH_ANOTHER_SAVE',function()
    local a=actor();a.script.engineHandlers.onLoad({schema=999})
    assert(a:state().phase=='LOAD_HOLD')
    a.script.engineHandlers.onLoad(a.script.engineHandlers.onSave());a:activate();a:authorize();a:tick()
    assert(a:state().phase=='LOAD_HOLD'and#a.starts==0)
end)
check('SOURCE_ORIGINAL_ACTOR_IDENTITY_REFUSED',function()
    local a=actor();a.self.contentFile='Morrowind.esm';a:activate();a:authorize();a:tick()
    assert(a:state().phase=='IDENTITY_HOLD'and#a.starts==0 and a.removals==0)
end)
local function global()
    local context={now=0,time=8*3600,activeActors={},actors={},records={},paused=false}
    local player={id='player',position=vector(C.entry.x,C.entry.y,328),
        cell={name=C.entry.name,isExterior=true},events={}}
    function player:isValid()return true end
    function player:sendEvent(name,data)self.events[#self.events+1]={name=name,data=data}end
    local world={activeActors=context.activeActors,players={player},
        getGameTime=function()return context.time end,getSimulationTime=function()return context.now end,
        isWorldPaused=function()return context.paused end}
    local types={NPC={records={}},Actor={isDead=function(o)return o.dead end}}
    for _,role in ipairs(C.roles)do types.NPC.records[role.template]={isMale=true,name='Original Template'}end
    function types.NPC.objectIsInstance(o)return o.isNpc==true end
    function types.NPC.createRecordDraft(data)return data end
    function world.createRecord(draft)
        local record={id='dynamic-record-'..(#context.records+1),draft=draft}
        context.records[#context.records+1]=record;return record
    end
    function world.createObject(recordId)
        local o={id='dynamic-actor-'..(#context.actors+1),recordId=recordId,isNpc=true,enabled=true,events={}}
        function o:isValid()return true end
        function o:addScript(path,data)assert(path=='scripts/veyra_townlife/actor.lua');self.init=data end
        function o:teleport(cell,position,options)self.cell=cell;self.position=position;assert(options.onGround)end
        function o:sendEvent(name,data)self.events[#self.events+1]={name=name,data=data}end
        context.actors[#context.actors+1]=o;return o
    end
    local modules={['openmw.world']=world,['openmw.types']=types,['openmw.util']=util,
        ['scripts.veyra_townlife.config']=C}
    local old=require;require=function(name)return assert(modules[name],name)end
    local result=assert(loadfile(root..'/mod/scripts/veyra_townlife/global.lua'))();require=old
    context.script=result;context.world=world
    function context:create()
        local positions={};for _,role in ipairs(C.roles)do positions[role.id]=clone(C.locations[role.home])end
        self.script.eventHandlers.VEYRA_TownCreate({player=player,positions=positions})
    end
    function context:activateAndReport()
        for _,o in ipairs(self.actors)do self.activeActors[#self.activeActors+1]=o
            self.script.eventHandlers.VEYRA_TownReport({kind='READY',actor=o,role=o.init.role})end
    end
    function context:tick()self.now=self.now+1;self.script.engineHandlers.onUpdate()end
    return context
end
check('GLOBAL_DISABLE_REACHES_REACTIVATED_OWN_ACTORS',function()
    local g=global();g:create();g.script.interface.setEnabled(false);g:activateAndReport();g:tick()
    for _,o in ipairs(g.actors)do
        local found=false;for _,event in ipairs(o.events)do
            if event.name=='VEYRA_TownEnabled'then found=true;assert(event.data.enabled==false)end
            assert(event.name~='VEYRA_TownGoal')
        end;assert(found)
    end
end)
check('THREE_DAILY_ROLES_HAVE_BOUND_REAL_GOALS_ONLY',function()
    local g=global();g:create();g:activateAndReport();g:tick()
    local expected={garden='field',trade='market',watch='lookout'}
    local snapshot=g.script.interface.getState()
    for id,row in pairs(snapshot.roles)do assert(row.goal==expected[id]and row.daySlot=='08:00-12:00')end
    assert(#g.actors==3 and#g.records==3)
    for _,record in ipairs(g.records)do assert(record.draft.mwscript==''and record.draft.servicesOffered.Barter==false)end
end)
check('GLOBAL_UNKNOWN_SAVE_HOLD_RETAINED',function()
    local g=global();g.script.engineHandlers.onLoad({schema=999})
    local saved=g.script.engineHandlers.onSave();g.script.engineHandlers.onLoad(saved);g:tick()
    assert(g.script.interface.getState().phase=='LOAD_HOLD'and#g.actors==0)
end)
local function panel()
    local context={now=0,mode=nil,hud=true,updates=0}
    local self={object={},cell={name=C.entry.name,isExterior=true}}
    local UI={getMode=function()return context.mode end,isHudVisible=function()return context.hud end}
    local ui={TYPE={Text='Text',Image='Image',Widget='Widget'},
        screenSize=function()return vector(1024,768)end,content=function(value)return value end,
        texture=function(data)assert(data.path=='Textures/veyra_townlife/white.png');return data end,
        layers={indexOf=function()return false end,insertAfter=function(name,_,options)assert(name=='HUD'and not options.interactive)end}}
    function ui.create(layout)
        context.layout=layout
        return{update=function()context.updates=context.updates+1 end,destroy=function()end}
    end
    local modules={['openmw.core']={getSimulationTime=function()return context.now end,getGameTime=function()return 8*3600 end,
        sendGlobalEvent=function()end},['openmw.self']=self,['openmw.nearby']={},['openmw.types']={},
        ['openmw.ui']=ui,['openmw.interfaces']={UI=UI},['openmw.util']=util,
        ['scripts.veyra_townlife.config']=C}
    local old=require;require=function(name)return assert(modules[name],name)end
    local result=assert(loadfile(root..'/mod/scripts/veyra_townlife/player.lua'))();require=old
    context.script=result
    local state={created=true,gameDayIndex=2,gameHour=8,gameMinute=0,roles={}}
    for _,role in ipairs(C.roles)do
        state.roles[role.id]={phase='TRAVEL_PROGRESS',goal='water',daySlot='08:00-12:00',measuredDistance=128}
    end
    result.eventHandlers.VEYRA_TownStatus(state);return context
end
check('PANEL_HAS_ROLE_SLOT_DESTINATION_AND_OBSERVED_PHASE',function()
    local p=panel();p.script.engineHandlers.onFrame(1)
    assert(p.layout.props.visible and#p.layout.content==11)
    local texts={};for _,element in ipairs(p.layout.content)do texts[element.name]=element.props.text end
    assert(texts.garden_role=='KERA / GARTENBESUCHER')
    assert(texts.garden_goal=='08:00-12:00  >  Wasserecke')
    assert(texts.garden_state=='Unterwegs / gemessen / 128 Weg')
    assert(texts.title=='LEVIATH / TAG 2 / 08:00')
    local shown=p.script.interface.getState();assert(shown.screenX==1024 and shown.screenY==768)
    assert(shown.lastRefreshAtGameTime==8*3600 and shown.roles.garden.displayedRole==texts.garden_role)
end)
check('PANEL_HIDES_IN_PAUSED_MENU_WITH_ZERO_DT',function()
    local p=panel();p.script.engineHandlers.onFrame(1);p.mode='Inventory';p.script.engineHandlers.onFrame(0)
    assert(not p.layout.props.visible);p.mode=nil;p.script.engineHandlers.onFrame(0);assert(p.layout.props.visible)
    local detached=p.script.interface.getState();detached.roles.garden.phase='MUTATED'
    assert(p.script.interface.getState().roles.garden.phase=='TRAVEL_PROGRESS')
end)
check('PANEL_FIXED_ADJACENT_POSITION_SOURCE_CONTRACT',function()
    local p=panel();p.script.engineHandlers.onFrame(1)
    local props=p.layout.props
    assert(props.position.x==460 and props.position.y==28)
    assert(props.relativePosition==nil and props.anchor==nil)
    assert(props.size.x==398 and props.size.y==244)
    local status=p.script.interface.getState()
    assert(status.panelAnchor=='FIXED_ADJACENT'and status.presentationVersion=='0.1.2')
end)
print('TOWNMODEL|TOTAL|'..count..'|NATIVE=NOT_RUN')
