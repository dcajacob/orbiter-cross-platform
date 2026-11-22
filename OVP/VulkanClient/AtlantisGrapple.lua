-- Stock Atlantis controls: 8 grapples/releases, 9 stows the moving arm.
-- Carina coasts toward the independently calculated deployed tip at 0.7 m/s.
local shuttle = vessel.get_interface('Atlantis')
local payload = vessel.get_interface('Carina')
local arm = shuttle:get_attachmenthandle(false, 1)
local socket = payload:get_attachmenthandle(true, 1)
local report = assert(io.open('vulkan-grapple.csv', 'w'))
report:write('time,phase,arm_holds_carina,carina_on_arm,tip_x,tip_y,tip_z,socket_x,socket_y,socket_z,gap_m\n')

local function sample(phase)
    local tip = shuttle:get_attachmentparams(arm)
    local fixture = payload:get_attachmentparams(socket)
    local pos = shuttle:global2local(payload:local2global(fixture))
    local gap = vec.length(vec.sub(pos, tip))
    local parent = shuttle:get_attachmentstatus(arm) == payload:get_handle()
    local child = payload:get_attachmentstatus(socket) == shuttle:get_handle()
    report:write(string.format('%.3f,%s,%d,%d,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f\n',
        oapi.get_simtime(), phase, parent and 1 or 0, child and 1 or 0,
        tip.x, tip.y, tip.z, pos.x, pos.y, pos.z, gap))
    report:flush()
    return parent, child, gap, pos
end

local function check(phase, attached, maxGap)
    local parent, child, gap, pos = sample(phase)
    assert(parent == attached and child == attached, phase .. ': unexpected attachment state')
    if maxGap then assert(gap < maxGap, phase .. ': grapple fixture missed the tip') end
    return gap, pos
end

proc.wait_simtime(0.2)
assert(check('incoming', false) > 1, 'payload did not approach from free flight')
proc.wait_simtime(2)
check('approach', false, 0.1)
shuttle:send_bufferedkey(0x09) -- 8
proc.wait_simtime(4)
local _, capture = check('grappled', true, 0.02)
shuttle:send_bufferedkey(0x0A) -- 9
proc.wait_simtime(14)
local _, release = check('carried', true, 0.1)
assert(vec.length(vec.sub(release, capture)) > 2, 'arm did not carry the payload')
shuttle:send_bufferedkey(0x09)
proc.wait_simtime(14.2)
check('released', false, 0.25)
proc.wait_simtime(28)
local gap, free = check('clear', false)
assert(gap > 2, 'arm and free payload did not separate')
assert(vec.length(vec.sub(free, release)) < 0.25, 'payload jumped on release')
report:close()
