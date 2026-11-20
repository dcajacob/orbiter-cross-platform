-- Stock Orbiter propagates the vehicles and updates the Docking MFD.
local ship = vessel.get_focusinterface()
local station = vessel.get_interface('ISS')
local gliderPort = ship:get_dockparams(ship:get_dockhandle(0))
local stationPort = station:get_dockparams(station:get_dockhandle(0))
local function distance()
    return vec.length(vec.sub(station:local2global(stationPort), ship:local2global(gliderPort)))
end
local start = oapi.get_simtime()
local function sample(label)
    local d = distance()
    local v = oapi.get_relativevel(ship:get_handle(), station:get_handle())
    local r = vec.sub(ship:local2global(gliderPort), station:local2global(stationPort))
    oapi.write_log(string.format('Vulkan pilot %s: t=%.2f port range=%.2f m closing=%.2f m/s',
        label, oapi.get_simtime()-start, d, -vec.dotp(v,r)/d))
end
local function exterior()
    oapi.set_cameramode({mode='track', trackmode='global', reldist=6.83,
        phi=math.rad(52.96), tht=math.rad(-13.52)})
end
exterior()
sample('exterior')
proc.wait_simdt(3)
oapi.set_cameramode({mode='cockpit',cockpitmode='panel2d',pos=0})
sample('cockpit')
proc.wait_simdt(6)
sample('brake start')
local stop = oapi.get_simtime()+5
while oapi.get_simtime() < stop do
    ship:inc_thrustergrouplevel_singlestep(THGROUP.ATT_BACK, 1)
    proc.skip()
end
sample('brake end')
proc.wait_simdt(8)
sample('cockpit end')
exterior()
proc.wait_simdt(4)
sample('exterior end')
