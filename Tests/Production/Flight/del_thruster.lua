-- Scenario regression. Run on the focus vessel in a disposable flight.
local ship = assert(vessel.get_focusinterface())
local initial_count = ship:get_thrustercount()
local initial_exhaust = ship:get_exhaustcount()
local tank = ship:create_propellantresource(1)
local spec = {pos = {x=1,y=0,z=0}, dir = {x=0,y=1,z=0}, maxth0 = 10, hprop = tank}
local removed = ship:create_thruster(spec)
local survivor = ship:create_thruster(spec)
local standard = THGROUP.ATT_PITCHUP
local original = {}
for i = 0, ship:get_groupthrustercount(standard) - 1 do
    original[i+1] = ship:get_groupthruster(standard, i)
end
local members = {removed}
for _, thruster in ipairs(original) do table.insert(members, thruster) end
table.insert(members, removed)
ship:create_thrustergroup(members, standard)

-- Leave an empty user slot preceding a live group. Preserve existing groups.
local slot = 0
while ship:get_thrustergrouphandlebyindex(slot) or ship:get_thrustergrouphandlebyindex(slot+1) do
    slot = slot+1
end
local user_type = 0x40 + slot  -- THGROUP_USER + slot
local hole = ship:create_thrustergroup({survivor}, user_type)
local user = ship:create_thrustergroup({removed, survivor, removed}, user_type+1)
ship:del_thrustergroup(hole)
ship:add_exhaust(removed, 1, 0.1)
ship:add_exhaust(survivor, 1, 0.1)
assert(ship:get_exhaustcount() == initial_exhaust+2)

assert(ship:del_thruster(removed))
assert(not ship:del_thruster(removed))
assert(ship:get_thrustercount() == initial_count+1)
assert(ship:get_exhaustcount() == initial_exhaust+1)
assert(ship:get_groupthrustercount(standard) == #original)
for i, thruster in ipairs(original) do
    assert(ship:get_groupthruster(standard, i-1) == thruster)
end
assert(ship:get_groupthrustercount(user) == 1)
assert(ship:get_groupthruster(user, 0) == survivor)
ship:set_thrustergrouplevel(user, 0.5)
assert(ship:get_thrusterlevel(survivor) == 0.5)
assert(ship:del_thruster(survivor))
assert(ship:get_groupthrustercount(user) == 0)
ship:del_thrustergroup(user)
ship:del_propellantresource(tank)
assert(ship:get_thrustercount() == initial_count)
assert(ship:get_exhaustcount() == initial_exhaust)
local report = assert(io.open('del-thruster-pass.txt', 'w'))
report:write(ship:get_classname(), '\n', initial_count, ' thrusters, ', initial_exhaust, ' exhausts restored\n')
report:close()
