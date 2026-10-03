-- SPDX-License-Identifier: MIT
local core=require('openmw.core')
local self=require('openmw.self')
local input=require('openmw.input')
local ui=require('openmw.ui')
local nearby=require('openmw.nearby')
local util=require('openmw.util')
local cached,lastStatus={phase='CONNECTING'},-100
local function findLanding()
    if not self.cell or not self.cell.isExterior then return end
    local offsets={{-450,0},{0,-450},{450,0},{0,450},{-350,-350},{350,-350},{-350,350},{350,350}}
    local flags=nearby.NAVIGATOR_FLAGS.Walk+nearby.NAVIGATOR_FLAGS.OpenDoor
    for _,offset in ipairs(offsets) do
        local point=nearby.findNearestNavMeshPosition(self.position+util.vector3(offset[1],offset[2],0),
            {includeFlags=flags,searchAreaHalfExtents=util.vector3(160,160,220)})
        if point and (point-self.position):length()>280 and (point-self.position):length()<800 then
            local ray=nearby.castRay(point+util.vector3(0,0,60),self.position+util.vector3(0,0,60),
                {collisionType=nearby.COLLISION_TYPE.World+nearby.COLLISION_TYPE.Door})
            local status,path=nearby.findPath(point,self.position,{includeFlags=flags,destinationTolerance=60})
            if status==nearby.FIND_PATH_STATUS.Success and not ray.hit then
                local points=0;for _ in ipairs(path)do points=points+1 end
                core.sendGlobalEvent('VEYRA_CourierLanding',{player=self.object,cellId=self.cell.id,
                    position=point,pathPoints=points})
                return
            end
        end
    end
    print('VEYRA|kind=LANDING_WAIT|navmesh or clear path not available yet')
end
local function claim()
    core.sendGlobalEvent('VEYRA_CourierClaim',{player=self.object})
end
return {interfaceName='VeyraCourierPlayer',interface={version=1,claim=claim,getState=function()
        local copy={};for k,v in pairs(cached)do copy[k]=v end;return copy
    end},
    engineHandlers={onFrame=function()
        if not self.cell then return end
        local now=core.getSimulationTime()
        if now-lastStatus>1 then lastStatus=now;core.sendGlobalEvent('VEYRA_CourierStatusRequest',{}) end
    end,onLoad=function()cached,lastStatus={phase='CONNECTING'},-100 end,onKeyPress=function(key)
        if key.code==input.KEY.F10 then claim() end
    end},eventHandlers={VEYRA_CourierNotice=function(data)
        ui.showMessage(data.message)
        print('VEYRA|kind=PLAYER_NOTICE|notice='..tostring(data.kind))
    end,VEYRA_CourierFindLanding=findLanding,VEYRA_CourierStatus=function(data)
        if cached.phase~=data.phase then print('VEYRA|kind=PLAYER_STATUS|phase='..tostring(data.phase)) end
        cached=data
    end}}
