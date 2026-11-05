// Licensed under the MIT License
#include "Production/FlightInput.h"
#include "Production/FlightKeys.h"
#include <iostream>
#include <stdexcept>
using namespace orbiter::production;
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
bool pressed(const std::array<char,256>& keys,unsigned code) {return (keys[code]&0x80)!=0;}
int main() {
 try {
    // A full Ctrl+S chord reached the real docked application in one batch.
    // The held-key snapshot is already clear, but the S press must retain Ctrl.
    for(unsigned modifier:{OAPI_KEY_LCONTROL,OAPI_KEY_RCONTROL,OAPI_KEY_LSHIFT,OAPI_KEY_RSHIFT,OAPI_KEY_LALT,OAPI_KEY_RALT}) {
        for(unsigned key:{OAPI_KEY_S,OAPI_KEY_SPACE,OAPI_KEY_I}) {
            FlightInput input;input.events={{modifier,true},{key,true},{key,false},{modifier,false}};
            const auto original=input.keys;BufferedKeyState buffered(input);
            for(unsigned i=0;i<input.events.size();++i) {
                const auto& state=buffered.Advance(input.events[i]);
                require(pressed(state,modifier)==(i<3),"Queued chord lost its modifier");
                require(pressed(state,key)==(i==1),"Queued key edge state is incorrect");
            }
            require(input.keys==original,"Buffered dispatch changed immediate held keys");
        }
    }
    // A modifier held before this poll stays held through a complete key tap.
    FlightInput held;held.keys[OAPI_KEY_RCONTROL]=char(0x80);held.events={{OAPI_KEY_S,true},{OAPI_KEY_S,false}};
    BufferedKeyState heldState(held);
    for(const auto& event:held.events)require(pressed(heldState.Advance(event),OAPI_KEY_RCONTROL),"Pre-existing held modifier lost");
    // A later Ctrl press must not retroactively modify the preceding S press.
    FlightInput later;later.keys[OAPI_KEY_LCONTROL]=char(0x80);later.events={{OAPI_KEY_S,true},{OAPI_KEY_LCONTROL,true},{OAPI_KEY_S,false}};
    BufferedKeyState laterState(later);require(!pressed(laterState.Advance(later.events[0]),OAPI_KEY_LCONTROL),"Later modifier affected earlier event");
    require(pressed(laterState.Advance(later.events[1]),OAPI_KEY_LCONTROL),"Later modifier press absent");
    // The same chord must deliver identical event states however polls divide it.
    const std::vector<FlightKeyEvent> chord={{OAPI_KEY_LCONTROL,true},{OAPI_KEY_LSHIFT,true},{OAPI_KEY_I,true},{OAPI_KEY_I,false},{OAPI_KEY_LCONTROL,false},{OAPI_KEY_LSHIFT,false}};
    const bool ctrl[]={true,true,true,true,false,false},shift[]={false,true,true,true,true,false};
    for(unsigned cuts=0;cuts<(1u<<(chord.size()-1));++cuts) {
        std::array<char,256> heldKeys{};unsigned begin=0;
        for(unsigned end=0;end<chord.size();++end) {
            heldKeys[chord[end].code]=chord[end].down?char(0x80):0;
            if(end+1<chord.size() && !(cuts&(1u<<end)))continue;
            FlightInput batch;batch.keys=heldKeys;batch.events.assign(chord.begin()+begin,chord.begin()+end+1);BufferedKeyState state(batch);
            for(unsigned i=begin;i<=end;++i) {
                const auto& keys=state.Advance(chord[i]);
                require(pressed(keys,OAPI_KEY_LCONTROL)==ctrl[i] && pressed(keys,OAPI_KEY_LSHIFT)==shift[i],"Input behavior depends on poll grouping");
            }
            require(batch.keys==heldKeys,"Immediate state changed between polls");begin=end+1;
        }
    }
    std::cout<<"Buffered chords preserve event modifiers across all poll partitions; immediate state unchanged\n";
 } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
