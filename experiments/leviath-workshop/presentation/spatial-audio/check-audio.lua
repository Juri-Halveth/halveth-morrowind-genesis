-- SPDX-License-Identifier: MIT
-- Ordinary Lua5.1 model checks; engine doubles are not native observations.
local path = assert(arg[1], 'audio source path required')
local tests = 0
local function check(name, fn)
    fn();tests=tests+1;print('PASS '..name)
end
local env, api
local function fresh()
    env={phase='DEPOT',id='courier:1',valid=true,active=true,enabled=true,
        soundEnabled=true,paused=false,time=500,calls={},playing=false}
    env.actor={id=env.id,enabled=true,isValid=function() return env.valid end}
    env.world={activeActors={env.actor}}
    env.courier={status=function()
        if env.statusError then error('optional source unavailable') end
        return {phase=env.phase,courierId=env.id,courierValid=env.valid}
    end}
    env.interfaces={VeyraCourier=env.courier}
    env.core={getGameTime=function()return env.time end,
        isWorldPaused=function()return env.paused end,
        sound={isEnabled=function()return env.soundEnabled end,
            isSoundFilePlaying=function(file, actor)
                assert(file=='Sound/veyra/courier_bell_mono.wav' and actor==env.actor)
                return env.playing
            end,
            playSoundFile3d=function(file, actor, options)
                if env.playError then error('decoder unavailable') end
                env.calls[#env.calls+1]={file=file,actor=actor,options=options}
            end}}
    for name, mod in pairs({['openmw.core']=env.core,['openmw.world']=env.world,
        ['openmw.interfaces']=env.interfaces}) do
        package.loaded[name]=mod
    end
    api=assert(loadfile(path))()
end
local function tick() api.engineHandlers.onUpdate(0.25) end
fresh()
check('non-arrival phases do not request sound',function()
    for _,phase in ipairs({'DEPOT','TRAVEL','APPROACH','CLAIMED'}) do env.phase=phase;tick() end
    assert(#env.calls==0)
end)
check('arrival sound attaches to actual active actor as non-looping 3D file',function()
    env.phase='ARRIVED';tick();assert(#env.calls==1)
    local call=env.calls[1]
    assert(call.actor==env.actor and call.options.loop==false and call.options.volume==0.30
        and call.options.pitch==1.0 and api.interface.getState().status=='PLAY_REQUESTED')
end)
check('only one request per courier and native playback query remains separate',function()
    env.playing=true;tick();assert(api.interface.getState().status=='PLAYING')
    env.playing=false;tick();assert(api.interface.getState().status=='ALREADY_REQUESTED' and #env.calls==1)
end)
check('save and load preserve deduplication',function()
    local saved=api.engineHandlers.onSave();api.engineHandlers.onLoad(saved);tick()
    assert(#env.calls==1 and api.interface.getState().requestCount==0)
end)
check('next courier remains a separate delivery',function()
    env.id='courier:2';env.actor.id=env.id;tick();assert(#env.calls==2)
end)
check('disabled audio and inactive actors defer rather than consume delivery',function()
    fresh();env.phase='ARRIVED';env.soundEnabled=false;tick()
    assert(#env.calls==0 and api.interface.getState().status=='SOUND_DISABLED')
    env.soundEnabled=true;env.world.activeActors={};tick()
    assert(#env.calls==0 and api.interface.getState().status=='WAITING_FOR_ACTIVE_ACTOR')
    env.world.activeActors={env.actor};env.actor.enabled=false;tick();assert(#env.calls==0)
    env.actor.enabled=true;tick();assert(#env.calls==1)
end)
check('pause defers playback until resumed',function()
    fresh();env.phase='ARRIVED';env.paused=true;tick();assert(#env.calls==0)
    env.paused=false;tick();assert(#env.calls==1)
end)
check('absent or failed optional courier leaves isolated module recoverable',function()
    fresh();env.interfaces.VeyraCourier=nil;tick()
    assert(#env.calls==0 and api.interface.getState().status=='NO_COURIER_INTERFACE')
    env.interfaces.VeyraCourier=env.courier;env.statusError=true;tick()
    assert(api.interface.getState().status=='ERROR' and #env.calls==0)
    env.statusError=false;env.phase='ARRIVED';tick();assert(#env.calls==1)
end)
check('decoder failure does not consume delivery',function()
    fresh();env.phase='ARRIVED';env.playError=true;tick()
    assert(#env.calls==0 and api.interface.getState().requestCount==0)
    env.playError=false;tick();assert(#env.calls==1)
end)
check('detached state snapshot cannot alter delivery bookkeeping',function()
    local snapshot=api.interface.getState();snapshot.lastPlayedCourierId='tampered'
    snapshot.requestCount=999;tick();assert(#env.calls==1 and api.interface.getState().requestCount==1)
end)
check('invalid saved state holds instead of silently replaying',function()
    fresh();env.phase='ARRIVED';api.engineHandlers.onLoad({version=1,lastPlayedCourierId=22});tick()
    assert(#env.calls==0 and api.interface.getState().status=='LOAD_HOLD'
        and api.interface.getState().error=='INVALID_SAVED_STATE')
    api.engineHandlers.onLoad(api.engineHandlers.onSave());tick()
    assert(#env.calls==0 and api.interface.getState().status=='LOAD_HOLD')
end)
print('AUDIO_MODEL_PASS tests='..tests..' engine=DECLARED_DOUBLES native=NOT_TESTED')
