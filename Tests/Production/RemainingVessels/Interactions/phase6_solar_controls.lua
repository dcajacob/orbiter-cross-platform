-- Original vessel actuator API only. No vessel placement operations.
local v = assert(vessel.get_interface('FlyingDutchman'))
assert(v:get_classname() == 'SolarSail')
local function command(label, values)
    for index=1,4 do v:set_paddle(index, values[index]) end
    oapi.write_log('PHASE6_CONTROL solar '..label..' t='..oapi.get_simtime())
end
proc.wait_simtime(2)
command('deflect', {1,-1,0.5,-0.5})
proc.wait_simtime(4)
command('neutral', {0,0,0,0})
proc.wait_simtime(6)
command('reverse', {-1,1,-0.5,0.5})
