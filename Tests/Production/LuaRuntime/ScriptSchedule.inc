// Recorded public SDK actions for original Windows and native Linux.
        if(frames==0) {
            script=oapiCreateInterpreter();require(script!=nullptr,"Original Lua interpreter creation failed");
            require(oapiGetLua(script)!=nullptr,"Original Lua state missing");
            recordLibraries();
            const char* setup=R"lua(
                audit_count=0
                function audit(event)
                    local file=assert(io.open('lua-events.csv','a'))
                    file:write(string.format('%s,%.17g,%.17g\n',event,oapi.get_simtime(),oapi.get_simstep()))
                    file:close()
                    if _reference_timing then _reference_timing(event) end
                    audit_count=audit_count+1
                end
                audit('sync_initial')
            )lua";
            std::ofstream("lua-events.csv")<<"event,seconds,step\n";
            require(oapiExecScriptCmd(script,setup),"Synchronous original Lua setup failed");
            if(target=="DG") {
                require(oapiExecScriptCmd(script,"run('dg/aap'); setvessel(vessel.get_interface('DG')); assert(v~=nil); audit('aap_loaded')"),"Original DG AAP script failed");
            }
        }
        if(frames==10) {
            require(oapiAsyncScriptCmd(script,"audit('async_one')"),"First original asynchronous command failed");
            require(oapiAsyncScriptCmd(script,"audit('async_two')"),"Second original asynchronous command failed");
            require(oapiExecScriptCmd(script,"audit('sync_override')"),"Original synchronous override failed");
        }
        if(frames==20) {
            require(oapiAsyncScriptCmd(script,"for i=1,4 do audit('yield_'..i); proc.skip() end; audit('yield_done')"),"Original yielding command failed");
        }
        if(frames==30) {
            secondary=oapiCreateInterpreter();require(secondary!=nullptr,"Second original interpreter missing");
            require(oapiExecScriptCmd(secondary,"assert(audit_count==nil); local f=assert(io.open('lua-isolation.txt','w')); f:write('isolated'); f:close()"),"Original interpreter isolation failed");
            if(target=="DG") {
                const char* start=profile=="atmosphere" ?
                    "aap.alt(altitude()+500); aap.spd(airspeed()-25); aap.bank(5); audit('aap_started')" :
                    "aap.alt(20000); aap.spd(9000); aap.bank(5); audit('aap_started')";
                require(oapiAsyncScriptCmd(script,start),"Original AAP activation failed");
            }
        }
        if(frames==38 && profile=="atmosphere")
            require(oapiAsyncScriptCmd(script,"aap.spd(airspeed()+50); audit('aap_retargeted')"),"Original AAP speed retarget failed");
        if(frames==42 && profile=="atmosphere")
            require(oapiAsyncScriptCmd(script,"aap.spd(airspeed()-25); audit('aap_slowed')"),"Original AAP speed reduction failed");
        if(frames==45) {
            require(oapiDelInterpreter(secondary)==0,"Original secondary interpreter deletion failed");secondary=nullptr;
            if(target=="DG")require(oapiAsyncScriptCmd(script,"aap.alt(); aap.spd(); aap.bank(); audit('aap_stopped')"),"Original AAP stop failed");
        }
        if(frames==54)require(oapiExecScriptCmd(script,"audit('complete')"),"Original Lua completion failed");
        if(frames==55) {require(oapiDelInterpreter(script)==0,"Original interpreter deletion failed");script=nullptr;}
