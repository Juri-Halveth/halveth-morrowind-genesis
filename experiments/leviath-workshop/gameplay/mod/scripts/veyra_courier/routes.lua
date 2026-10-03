-- SPDX-License-Identifier: MIT
-- Travel is a declared map-cell approximation; NPC walking starts at the final leg.
local R = {}
function R.new(now, origin)
    return {impact=now, lastTime=now, x=origin.x, y=origin.y, phase='DEPOT'}
end
function R.advance(route, now, target, departureDays, cellsPerDay)
    assert(type(now)=='number' and now==now, 'Finite game time required')
    assert(type(target)=='table' and type(target.x)=='number' and type(target.y)=='number', 'Map target required')
    -- Loading an older save naturally loads that save's own route. A backwards clock
    -- within one state does not earn travel distance or change its impact time.
    if now < route.lastTime then return route end
    local departure=route.impact+departureDays*86400
    if now < departure then route.lastTime=now; return route end
    if route.phase=='DEPOT' then route.phase='TRAVEL' end
    if route.phase=='FINAL_LEG' and (route.x~=target.x or route.y~=target.y) then route.phase='TRAVEL' end
    if route.phase~='TRAVEL' then route.lastTime=now; return route end
    local start=math.max(route.lastTime,departure)
    local budget=math.max(0,now-start)*cellsPerDay/86400
    for _,axis in ipairs({'x','y'}) do
        local delta=target[axis]-route[axis]
        local step=math.min(math.abs(delta),budget)
        route[axis]=route[axis]+(delta<0 and -step or step)
        budget=budget-step
    end
    route.lastTime=now
    if math.abs(route.x-target.x)<0.000001 and math.abs(route.y-target.y)<0.000001 then
        route.phase='FINAL_LEG'
    end
    return route
end
return R
