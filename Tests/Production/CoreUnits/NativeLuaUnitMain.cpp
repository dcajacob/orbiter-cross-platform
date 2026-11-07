// Supply the resource context for the unchanged upstream Lua unit.
#include "Production/NativeGraphics.h"
#include "Production/ResourceResolver.h"
#include <catch2/catch_session.hpp>
#include <iostream>
int main(int argc,char** argv)
{
    if(argc<2)return 2;
    orbiter::production::ResourceResolver files(argv[1]);
    orbiter::production::NativeRenderContext context;
    context.programFiles=&files;
    auto* previous=orbiter::production::BindNativeRenderContext(&context);
    int code=3;
    try {code=Catch::Session().run(argc-1,argv+1);}
    catch(const std::exception& error) {std::cerr<<error.what()<<'\n';}
    orbiter::production::BindNativeRenderContext(previous);
    return code;
}
