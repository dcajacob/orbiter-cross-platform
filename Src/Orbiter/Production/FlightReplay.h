// Licensed under the MIT License
#pragma once
#include <filesystem>
#include <cmath>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace orbiter::production {
struct FlightCommand {std::string action,value;};
class FlightReplay {
    std::map<std::pair<unsigned,std::string>,std::vector<FlightCommand>> commands;
public:
    void Load(const std::filesystem::path& path) {
        std::ifstream file(path);if(!file)throw std::runtime_error("Cannot open flight replay: "+path.string());
        std::string line;std::getline(file,line);if(!line.empty() && line.back()=='\r')line.pop_back();if(line!="tick,phase,action,value")throw std::runtime_error("Invalid flight replay header");
        while(std::getline(file,line)) {
            if(!line.empty() && line.back()=='\r')line.pop_back();
            std::istringstream row(line);std::string tick,phase,action,value,extra;
            if(!std::getline(row,tick,',') || !std::getline(row,phase,',') || !std::getline(row,action,',') || !std::getline(row,value) || value.find(',')!=std::string::npos)
                throw std::runtime_error("Invalid flight replay row");
            std::size_t end=0;auto index=std::stoul(tick,&end);
            if(end!=tick.size() || index>10000000 || (phase!="before" && phase!="pre" && phase!="after"))throw std::runtime_error("Invalid flight replay tick/phase");
            commands[{unsigned(index),phase}].push_back({action,value});
        }
        if(!file.eof())throw std::runtime_error("Flight replay read failed");
    }
    std::vector<FlightCommand> Take(unsigned tick,const std::string& phase) {
        auto it=commands.find({tick,phase});if(it==commands.end())return {};
        auto result=std::move(it->second);commands.erase(it);return result;
    }
    bool Empty() const {return commands.empty();}
};
inline double FlightNumber(const std::string& text) {
    std::size_t end=0;double number=std::stod(text,&end);
    if(end!=text.size() || !std::isfinite(number))throw std::runtime_error("Invalid finite flight number: "+text);
    return number;
}
}
