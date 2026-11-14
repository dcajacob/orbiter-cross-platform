-- Licensed under the MIT License
-- Qualification flight. Drive the stock DG-S through its controls.
local ship = assert(vessel.get_focusinterface())
assert(ship:get_classname() == 'DG-S')
local pi, rad = math.pi, math.pi/180
local function clamp(x, lo, hi) return math.min(hi, math.max(lo, x)) end
local function wrap(x) return (x+pi)%(2*pi)-pi end
local start = ship:get_equpos()
local course = 330.01*rad
local sn, cs = math.sin(course), math.cos(course)
local radius = 5600
local departure, turnFinal = 5700, -8300
local field = ship:get_surfaceelevation()
local report = assert(io.open('vulkan-circuit.csv', 'w'))
report:write('t,phase,x,y,agl,airspeed,vertical_speed,pitch,bank,yaw,main,elevator,aileron,gear,ground\n')
local phase, airborne, gear, lastLog = 'roll', false, 1, -1
local markedTouchdown = false
local pitch0, bank0 = ship:get_pitch(), ship:get_bank()
local elevatorTrim, throttleTrim = 0, .36
local function throttle(level) ship:set_thrustergrouplevel(THGROUP.MAIN, level) end
local function elevator(level) ship:set_adclevel(AIRCTRL.ELEVATOR, level) end
local function aileron(level) ship:set_adclevel(AIRCTRL.AILERON, level) end
local function setGear(down)
    gear=down
    ship:Gear(down)
end
while oapi.get_simtime() < 525 do
    local t = oapi.get_simtime()
    local dt = math.max(.001, oapi.get_simstep())
    local p = ship:get_equpos()
    local east = (p.lng - start.lng) * start.rad * math.cos(start.lat)
    local north = (p.lat - start.lat) * start.rad
    local x, y = east*cs - north*sn, east*sn + north*cs
    local v = ship:get_groundspeedvector(REFFRAME.HORIZON)
    local airspeed = ship:get_airspeed()
    local agl = ship:get_altitude(1)
    local pitch, bank, yaw = ship:get_pitch(), ship:get_bank(), ship:get_yaw()
    local pitchRate, bankRate = wrap(pitch-pitch0)/dt, wrap(bank-bank0)/dt
    pitch0, bank0 = pitch, bank
    local ground = ship:get_groundcontact()
    if not airborne and not ground and agl > 12 then airborne = true; phase = 'departure' end
    if airborne and ground and phase == 'final' then
        if gear ~= 1 or y <= 50 or y >= 2500 or math.abs(x) >= 35 then
            throttle(0)
            ship:set_wheelbrakelevel(1)
            report:close()
            oapi.set_pause(true)
            error(string.format('Touchdown outside runway zone: %.1f m lateral, %.1f m along',x,y))
        end
        oapi.write_log(string.format('Vulkan circuit touchdown: %.1f m lateral, %.1f m along, %.1f m/s at %.1f s',x,y,airspeed,t))
        markedTouchdown = true
        phase = 'rollout'
    end
    if airborne and gear == 1 and agl > 55 and phase == 'departure' then setGear(0) end
    if phase == 'departure' and y > departure then phase = 'crosswind' end
    if phase == 'crosswind' and x < -1.75*radius and y < departure+400 then phase = 'downwind' end
    if phase == 'downwind' and y < turnFinal then phase = 'base' end
    if phase == 'base' and x > -.22*radius and y > turnFinal-280 then
        phase = 'final'; setGear(1)
    end

    if phase == 'roll' then
        throttle(1)
        elevator(airspeed >= 135 and 1 or 0)
    elseif phase == 'rollout' then
        throttle(0)
        elevator(0)
        aileron(0)
        local rudder=clamp(-4*wrap(yaw-course) - .006*x, -.6, .6)
        ship:set_adclevel(AIRCTRL.RUDDER,rudder)
        ship:set_wheelbrakelevel(1)
    else
        local speed = math.max(1,math.sqrt(v.x*v.x+v.z*v.z))
        local lookahead = clamp(8*speed, 800, 1450)
        local tx, ty
        if phase == 'departure' then tx, ty = 0, y+lookahead
        elseif phase == 'downwind' then tx, ty = -2*radius, y-lookahead
        elseif phase == 'crosswind' or phase == 'base' then
            local cy = phase == 'crosswind' and departure or turnFinal
            local angle = math.atan2(y-cy,x+radius)
            if phase == 'crosswind' then angle = clamp(angle, 0, pi)
            else angle = clamp(angle%(2*pi), pi, 2*pi) end
            local limit = phase == 'crosswind' and pi or 2*pi
            local target = angle+lookahead/radius
            local endpoint = math.min(target,limit)
            tx, ty = -radius + radius*math.cos(endpoint), cy + radius*math.sin(endpoint)
            local direction = phase == 'crosswind' and -1 or 1
            ty = ty + direction * radius * math.max(0,target-limit)
        else
            lookahead=clamp(2.5*speed+agl, 240, 900)
            tx, ty = 0, y+lookahead
        end
        local track=math.atan2(v.x,v.z)
        local desiredTrack=course+math.atan2(tx-x,ty-y)
        local gainDistance = math.sqrt((tx-x)^2+(ty-y)^2)
        local targetBank=clamp(-math.atan(2*speed^2*math.sin(wrap(desiredTrack-track))/(9.81*gainDistance)), -34*rad,34*rad)
        if phase == 'final' and agl < 75 then targetBank=clamp(targetBank, -9*rad,9*rad) end
        local roll=clamp(-4.2*(targetBank-bank) + 1.8*bankRate, -1,1)
        aileron(roll)
        local targetSpeed = phase == 'final' and 141 or 174
        local onFinal = phase == 'final'
        local pathHeight = (680-y)*.045 + 3
        local targetAlt = field + (onFinal and pathHeight or 420)
        local vertical = clamp((onFinal and -.045*speed or 0) + .20*(targetAlt-ship:get_altitude()), -12,15)
        if onFinal and y > -450 and agl < 28 then
            vertical = math.max(vertical, -1.1 - 4.8*clamp((agl-5)/23,0,1))
        end
        local q=math.max(7000, .5*1.18*airspeed*airspeed)
        local cl=ship:get_mass()*9.81 / (q*90*math.max(.72,math.cos(bank)))
        local targetAlpha=(17/0.7*cl-2)*rad
        local targetPitch=clamp(targetAlpha + math.atan2(vertical + .85*(vertical-v.y), speed), -13*rad, 14*rad)
        local error=targetPitch-pitch
        elevatorTrim=clamp(elevatorTrim+.50*error*dt,-.70,.70)
        elevator(clamp(4.5*error-2.0*pitchRate+elevatorTrim,-1,1))
        local speedError=targetSpeed-airspeed
        throttleTrim=clamp(throttleTrim + .004*speedError*dt, .04,.82)
        throttle(clamp(throttleTrim+.024*speedError,0,1))
    end
    if t>=lastLog+.5 then
        lastLog=t
        report:write(string.format('%.3f,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%d,%d\n',
            t,phase,x,y,agl,airspeed,v.y,pitch/rad,bank/rad,yaw/rad,ship:get_thrustergrouplevel(THGROUP.MAIN),
            ship:get_adclevel(AIRCTRL.ELEVATOR),ship:get_adclevel(AIRCTRL.AILERON),gear,ground and 1 or 0))
        report:flush()
    end
    if phase=='rollout' and ground and ship:get_groundspeed()<3 then
        report:close()
        oapi.set_pause(true)
        assert(markedTouchdown and math.abs(x) < 35 and y < 4600, 'Rollout left the runway')
        oapi.write_log(string.format('Vulkan circuit completed: %.1f m lateral, %.1f m along runway at %.1f s',x,y,t))
        return
    end
    proc.skip()
end
report:close()
throttle(0)
oapi.set_pause(true)
error('DG-S did not complete the Runway 33 circuit')
