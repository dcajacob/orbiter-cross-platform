// Licensed under the MIT License
#include "Production/CustomCommands.h"
#include <iostream>
using namespace orbiter::production;
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
struct Context {CustomCommands* commands;int id=-1,calls=0;};
void removeSelf(void* pointer) {
    auto& state=*static_cast<Context*>(pointer);
    ++state.calls;require(state.commands->Remove(state.id),"Callback could not unregister itself");
    for(int i=0;i<100;++i)state.commands->Register("new","new",[](void*){},nullptr);
}
int main() {
    try {
        CustomCommands commands;
        Context state{&commands};
        std::string label="same",description="owned";
        state.id=commands.Register(label.c_str(),description.c_str(),removeSelf,&state);
        int duplicate=commands.Register(label.c_str(),description.c_str(),[](void* p){++*static_cast<int*>(p);},&state.calls);
        label="changed";description="changed";
        auto view=commands.Snapshot();
        require(view.size()==2 && view[0].label=="same" && view[0].description=="owned","Registration borrowed temporary text");
        require(duplicate!=state.id,"Duplicate labels reused an identifier");
        require(commands.Invoke(state.id) && state.calls==1 && !commands.Contains(state.id),"Self-removing callback failed");
        require(view[0].description=="owned" && view.size()==2,"Mutation invalidated the display snapshot");
        require(!commands.Invoke(state.id) && !commands.Remove(state.id),"Removed function remained callable");
        require(commands.Invoke(duplicate) && state.calls==2,"Remaining duplicate label lost its callback or context");
        require(commands.Remove(duplicate) && !commands.Invoke(duplicate),"Removed snapshot entry was dispatched");
        require(!commands.Remove(-1),"Unknown identifier was accepted");
        CustomCommands nextSession;
        require(nextSession.Snapshot().empty(),"Custom functions leaked into another session");
        std::cout<<"Custom function ownership, mutation, context, duplicate labels and session isolation passed\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
