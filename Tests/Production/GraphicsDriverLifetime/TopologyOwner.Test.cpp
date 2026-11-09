// The module owns exactly one real Mesa affinity-mask allocation per load.
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
int main(int argc,char** argv) {
    if(argc!=3)return 2;
    const int genuine=std::atoi(argv[2]);
    for(int cycle=0;cycle<20;++cycle) {
        void* owner=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
        if(!owner){std::fprintf(stderr,"%s\n",dlerror());return 3;}
        auto prepare=reinterpret_cast<int(*)(int)>(dlsym(owner,"prepare_topology_fixture"));
        if(!prepare || prepare(genuine)!=0)return 4;
        if(dlclose(owner)!=0)return 5;
    }
    std::printf("completed_ownership_cycles=20 genuine_leak=%d\n",genuine);
    return 0;
}
