// Licensed under the MIT License
#pragma once
#include <algorithm>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace orbiter::production {
struct CustomCommand {
    int id;
    std::string label,description;
    void (*callback)(void*);
    void* context;
};

// Owned by one application session. Drawing takes a snapshot because a module
// callback may unregister itself, remove another command, or register more.
class CustomCommands {
    std::vector<CustomCommand> commands_;
    int nextId_=0;
public:
    int Register(const char* label,const char* description,void (*callback)(void*),void* context) {
        if(!label || !callback)throw std::invalid_argument("Custom function requires a label and callback");
        if(nextId_==(std::numeric_limits<int>::max)())throw std::overflow_error("Custom function identifiers exhausted");
        int id=nextId_++;
        commands_.push_back({id,label,description ? description : "",callback,context});
        return id;
    }
    bool Remove(int id) {
        auto it=std::find_if(commands_.begin(),commands_.end(),[&](const auto& command){return command.id==id;});
        if(it==commands_.end())return false;
        commands_.erase(it);return true;
    }
    bool Contains(int id) const {
        return std::any_of(commands_.begin(),commands_.end(),[&](const auto& command){return command.id==id;});
    }
    std::vector<CustomCommand> Snapshot() const {return commands_;}
    bool Invoke(int id) {
        auto it=std::find_if(commands_.begin(),commands_.end(),[&](const auto& command){return command.id==id;});
        if(it==commands_.end())return false;
        const auto callback=it->callback;void* context=it->context;
        callback(context);return true;
    }
};
}
