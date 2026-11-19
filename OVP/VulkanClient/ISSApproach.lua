-- Exterior camera for the two stock vessels. Orbiter propagates their orbits.
local glider = oapi.get_objhandle('DG-01')
local station = oapi.get_objhandle('ISS')
local function track(target, offset)
    local distance = vec.length(offset)
    oapi.set_cameramode({mode='track', trackmode='global',
        reldist=distance/oapi.get_size(target), phi=math.atan2(offset.x,-offset.z),
        tht=-math.asin(offset.y/distance)})
end

oapi.set_cameraaperture(math.rad(30))
local gliderEye = {x=53, y=16, z=-40}
track(glider, gliderEye)
local start = oapi.get_simtime()
local function sample(label)
    local separation = vec.length(oapi.get_relativepos(glider, station))
    oapi.write_log(string.format('Vulkan ISS approach %s: t=%.2f range=%.2f m focus=%s',
        label, oapi.get_simtime()-start, separation, vessel.get_focusinterface():get_name()))
end
sample('start')
proc.wait_simdt(10)
-- Frame the incoming glider beside the solar arrays from the station view.
local stationEye = {x=160, y=58, z=-132}
oapi.set_focusobject(station)
track(station, stationEye)
sample('station')
proc.wait_simdt(10)
oapi.set_focusobject(glider)
track(glider, gliderEye)
sample('glider')
proc.wait_simdt(8)
sample('end')
