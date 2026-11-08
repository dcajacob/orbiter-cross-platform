-- Fly the unmodified stock tug to a stock Module2 port with its real RCS.
-- Read-only geometry and actuator levels only; no placement or docking setters.
local tug = assert(vessel.get_interface('TUG-01'))
local target = assert(vessel.get_interface('Module1C'))
assert(tug:get_classname() == 'Dragonfly' and target:get_classname() == 'Module2')
local function add(a,b) return {x=a.x+b.x,y=a.y+b.y,z=a.z+b.z} end
local function scale(a,s) return {x=a.x*s,y=a.y*s,z=a.z*s} end
local function sub(a,b) return add(a,scale(b,-1)) end
local function dot(a,b) return a.x*b.x+a.y*b.y+a.z*b.z end
local function cross(a,b) return {x=a.y*b.z-a.z*b.y,y=a.z*b.x-a.x*b.z,z=a.x*b.y-a.y*b.x} end
local function length(a) return math.sqrt(dot(a,a)) end
local function limit(a,n) local m=length(a);return scale(a,math.min(1,n/math.max(m,1e-12))) end
local zero={x=0,y=0,z=0}
local own = assert(tug:get_dockhandle(0))
local op,od,ou = tug:get_dockparams(own)
local port,best=nil,-1e30
for i=0,target:get_dockcount()-1 do
    local h=assert(target:get_dockhandle(i))
    local p,d,u=target:get_dockparams(h)
    local score=dot(tug:globalrot(od),scale(target:globalrot(d),-1))+dot(tug:globalrot(ou),target:globalrot(u))
    if score>best then port,best=h,score end
end
local tp,td,tu=target:get_dockparams(assert(port))
local groups={THGROUP.ATT_PITCHUP,THGROUP.ATT_PITCHDOWN,THGROUP.ATT_YAWLEFT,THGROUP.ATT_YAWRIGHT,
    THGROUP.ATT_BANKLEFT,THGROUP.ATT_BANKRIGHT,THGROUP.ATT_RIGHT,THGROUP.ATT_LEFT,
    THGROUP.ATT_UP,THGROUP.ATT_DOWN,THGROUP.ATT_FORWARD,THGROUP.ATT_BACK}
local actuators,thrusters={},{}
local mass,pmi=tug:get_mass(),tug:get_pmi()
for _,g in ipairs(groups) do
    local a={group=g,force=zero,torque=zero,jets={}}
    assert(tug:get_groupthrustercount(g)>0,'Original RCS group missing')
    for i=0,tug:get_groupthrustercount(g)-1 do
        local h=assert(tug:get_groupthruster(g,i))
        local f=scale(tug:get_thrusterdir(h),tug:get_thrustermax0(h))
        a.force=add(a.force,f)
        -- Orbiter's original left-handed torque is F cross r.
        a.torque=add(a.torque,cross(f,tug:get_thrusterpos(h)))
        table.insert(a.jets,h);thrusters[h]=0
    end
    a.accel=scale(a.force,1/mass)
    a.alpha={x=a.torque.x/(mass*pmi.x),y=a.torque.y/(mass*pmi.y),z=a.torque.z/(mass*pmi.z)}
    table.insert(actuators,a)
end
local function choose(command,field,first,last)
    local residual=command
    for _,axis in ipairs({'x','y','z'}) do
        local selected,response=nil,0
        for i=first,last do
            local a=actuators[i]
            if a[field][axis]*residual[axis]>0 and math.abs(a[field][axis])>math.abs(response) then
                selected,response=a,a[field][axis]
            end
        end
        if selected then
            local level=math.min(1,residual[axis]/response)
            selected.level=(selected.level or 0)+level
            residual=sub(residual,scale(selected[field],level))
        end
    end
end
local approach=true
local lastlog=-10
while oapi.get_simtime()<390 do
    if tug:get_dockstatus(own) then
        assert(tug:get_dockstatus(own)==target:get_handle(),'Unexpected docking partner')
        assert(target:get_dockstatus(port)==tug:get_handle(),'Docking must be reciprocal')
        for h,_ in pairs(thrusters) do tug:set_thrusterlevel(h,0) end
        oapi.write_log('PHASE6_CONTROL Module2 reciprocal physical docking t='..oapi.get_simtime())
        return
    end
    local R=tug:get_rotationmatrix()
    local out,up=target:globalrot(td),target:globalrot(tu)
    local currentdir,currentup=tug:globalrot(od),tug:globalrot(ou)
    local desired=scale(out,-1)
    local error=scale(mat.tmul(R,add(cross(currentdir,desired),cross(currentup,up))),-0.5)
    local omega=sub(tug:get_angvel(),mat.tmul(R,target:globalrot(target:get_angvel())))
    local alpha=limit(sub(scale(error,0.08),scale(omega,0.6)),0.025)
    local targetoffset=target:globalrot(tp)
    local ownoffset=tug:globalrot(op)
    local delta=sub(add(sub(target:get_globalpos(),tug:get_globalpos()),targetoffset),ownoffset)
    local waypoint=add(delta,scale(out,approach and 10 or 0))
    if approach and length(waypoint)<0.7 and dot(currentdir,desired)>0.999 and dot(currentup,up)>0.999 then
        approach=false
        oapi.write_log('PHASE6_CONTROL Module2 final approach t='..oapi.get_simtime())
    end
    local targetvelocity=sub(target:get_globalvel(),cross(target:globalrot(target:get_angvel()),targetoffset))
    local ownvelocity=sub(tug:get_globalvel(),cross(tug:globalrot(tug:get_angvel()),ownoffset))
    local relative=sub(ownvelocity,targetvelocity)
    local wanted=limit(scale(waypoint,0.12),approach and 0.7 or 0.25)
    local accel=mat.tmul(R,scale(sub(wanted,relative),0.45))
    for _,a in ipairs(actuators) do a.level=0 end
    choose(alpha,'alpha',1,6)
    -- Compensate the real net force from the original rotational jet layout.
    for i=1,6 do accel=sub(accel,scale(actuators[i].accel,actuators[i].level)) end
    choose(accel,'accel',7,12)
    for h,_ in pairs(thrusters) do thrusters[h]=0 end
    for _,a in ipairs(actuators) do
        for _,h in ipairs(a.jets) do thrusters[h]=thrusters[h]+a.level end
    end
    for h,level in pairs(thrusters) do tug:set_thrusterlevel(h,math.min(1,level)) end
    if oapi.get_simtime()-lastlog>=10 then
        lastlog=oapi.get_simtime()
        oapi.write_log(string.format('PHASE6_CONTROL Module2 approach t=%.3f distance=%.6f align=%.9f up=%.9f rate=%.6f',lastlog,length(waypoint),dot(currentdir,desired),dot(currentup,up),length(omega)))
    end
    proc.skip()
end
error('Original RCS docking did not complete within the declared 390 seconds')
