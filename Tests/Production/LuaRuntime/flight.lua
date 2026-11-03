-- Run the stock AAP in a scenario interpreter on a live DG or DG-S.
run('dg/aap')
local ship = vessel.get_focusinterface()
setvessel(ship)
local report = assert(io.open('lua-flight.csv', 'w'))
report:write('tick,seconds,class,altitude,airspeed,elevator,aileron,main\n')
aap.alt(altitude()+500)
aap.spd(airspeed()-25)
aap.bank(5)
ship:Gear(1)
ship:Nosecone(1)
for tick=1,40 do
    if tick==12 then aap.spd(airspeed()+50) end
    if tick==24 then aap.spd(airspeed()-25) end
    if tick==32 then aap.alt(); aap.spd(); aap.bank() end
    proc.skip()
    report:write(string.format('%d,%.17g,%s,%.17g,%.17g,%.17g,%.17g,%.17g\n',
        tick,oapi.get_simtime(),ship:get_classname(),ship:get_altitude(),ship:get_airspeed(),
        ship:get_adclevel(AIRCTRL.ELEVATOR),ship:get_adclevel(AIRCTRL.AILERON),
        ship:get_thrustergrouplevel(THGROUP.MAIN)))
    report:flush()
end
report:close()
