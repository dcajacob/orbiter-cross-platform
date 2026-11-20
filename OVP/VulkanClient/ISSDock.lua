-- Both vessels start in independent free flight. The simulator captures the ports.
local glider = vessel.get_focusinterface()
local station = vessel.get_interface('ISS')
local own = glider:get_dockhandle(0)
local target = station:get_dockhandle(0)
local p = glider:get_dockparams(own)
local q = station:get_dockparams(target)
local function separation()
    return vec.length(vec.sub(glider:local2global(p), station:local2global(q)))
end
local function exterior()
    oapi.set_cameramode({mode='track',trackmode='relative',reldist=5,phi=1.15,tht=-0.35})
end
local start = oapi.get_simtime()
exterior()
oapi.write_log(string.format('Vulkan docking start: ports %.3f m apart',separation()))
proc.wait_simdt(2)
oapi.set_cameramode({mode='cockpit',cockpitmode='panel2d',pos=0})
while not glider:get_dockstatus(own) and oapi.get_simtime()-start < 30 do proc.skip() end
local captured = glider:get_dockstatus(own) == station:get_handle()
    and station:get_dockstatus(target) == glider:get_handle()
oapi.write_log(string.format('Vulkan docking contact: t=%.2f reciprocal=%s port range=%.3f m',
    oapi.get_simtime()-start,tostring(captured),separation()))
proc.wait_simdt(4)
exterior()
