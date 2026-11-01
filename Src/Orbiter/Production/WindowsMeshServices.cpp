// Licensed under the MIT License
#include "WindowsMeshServices.h"
#include "Orbiter.h"
#include "Log.h"
#include <type_traits>
#include <cstddef>
namespace orbiter::production {
static_assert(std::is_same<UInt32,DWORD>::value && std::is_same<UInt16,WORD>::value);
static_assert(std::is_same<UInt64,DWORDLONG>::value);
static_assert(std::is_same<MeshSurface,SURFHANDLE>::value);
static_assert(sizeof(GroupSpec)==sizeof(MESHGROUPEX), "SDK mesh group extent changed");
static_assert(MeshExtraTextures==MAXTEX, "SDK extra-texture count changed");
#define CHECK_MESH_FIELD(field) static_assert(offsetof(GroupSpec,field)==offsetof(MESHGROUPEX,field)); \
    static_assert(std::is_same<decltype(GroupSpec::field),decltype(MESHGROUPEX::field)>::value)
CHECK_MESH_FIELD(Vtx); CHECK_MESH_FIELD(Idx); CHECK_MESH_FIELD(nVtx); CHECK_MESH_FIELD(nIdx);
CHECK_MESH_FIELD(MtrlIdx); CHECK_MESH_FIELD(TexIdx); CHECK_MESH_FIELD(UsrFlag);
CHECK_MESH_FIELD(zBias); CHECK_MESH_FIELD(Flags); CHECK_MESH_FIELD(TexIdxEx); CHECK_MESH_FIELD(TexMixEx);
#undef CHECK_MESH_FIELD
static_assert(MeshEdit::SETUSERFLAG==GRPEDIT_SETUSERFLAG);
static_assert(MeshEdit::ADDUSERFLAG==GRPEDIT_ADDUSERFLAG);
static_assert(MeshEdit::DELUSERFLAG==GRPEDIT_DELUSERFLAG);
static_assert(MeshEdit::VTXCRDX==GRPEDIT_VTXCRDX);
static_assert(MeshEdit::VTXCRDY==GRPEDIT_VTXCRDY);
static_assert(MeshEdit::VTXCRDZ==GRPEDIT_VTXCRDZ);
static_assert(MeshEdit::VTXCRD==GRPEDIT_VTXCRD);
static_assert(MeshEdit::VTXNMLX==GRPEDIT_VTXNMLX);
static_assert(MeshEdit::VTXNMLY==GRPEDIT_VTXNMLY);
static_assert(MeshEdit::VTXNMLZ==GRPEDIT_VTXNMLZ);
static_assert(MeshEdit::VTXNML==GRPEDIT_VTXNML);
static_assert(MeshEdit::VTXTEXU==GRPEDIT_VTXTEXU);
static_assert(MeshEdit::VTXTEXV==GRPEDIT_VTXTEXV);
static_assert(MeshEdit::VTXTEX==GRPEDIT_VTXTEX);
static_assert(MeshEdit::VTX==GRPEDIT_VTX);
static_assert(MeshEdit::VTXCRDADDX==GRPEDIT_VTXCRDADDX);
static_assert(MeshEdit::VTXCRDADDY==GRPEDIT_VTXCRDADDY);
static_assert(MeshEdit::VTXCRDADDZ==GRPEDIT_VTXCRDADDZ);
static_assert(MeshEdit::VTXCRDADD==GRPEDIT_VTXCRDADD);
static_assert(MeshEdit::VTXNMLADDX==GRPEDIT_VTXNMLADDX);
static_assert(MeshEdit::VTXNMLADDY==GRPEDIT_VTXNMLADDY);
static_assert(MeshEdit::VTXNMLADDZ==GRPEDIT_VTXNMLADDZ);
static_assert(MeshEdit::VTXNMLADD==GRPEDIT_VTXNMLADD);
static_assert(MeshEdit::VTXTEXADDU==GRPEDIT_VTXTEXADDU);
static_assert(MeshEdit::VTXTEXADDV==GRPEDIT_VTXTEXADDV);
static_assert(MeshEdit::VTXTEXADD==GRPEDIT_VTXTEXADD);
static_assert(MeshEdit::VTXADD==GRPEDIT_VTXADD);
static_assert(MeshEdit::VTXMOD==GRPEDIT_VTXMOD);
MeshServices WindowsMeshServices(Orbiter& application)
{
    MeshServices services;
    services.context=&application;
    services.path=[](void* context,const char* name)->std::filesystem::path {
        return static_cast<Orbiter*>(context)->MeshPath(name);
    };
    services.loadTexture=[](void* context,const char* name,UInt32 flags)->MeshSurface {
        auto* graphics=static_cast<Orbiter*>(context)->GetGraphicsClient();
        return graphics ? graphics->clbkLoadTexture(name,flags) : nullptr;
    };
    services.releaseTexture=[](void* context,MeshSurface surface) {
        if (auto* graphics=static_cast<Orbiter*>(context)->GetGraphicsClient()) graphics->clbkReleaseTexture(surface);
    };
    services.error=[](void*,const char* message) { LOGOUT_ERR("%s",message); };
    services.allocation=[](void*,const char* file,int line) {
#ifdef TRACE_MEMALLOC
        tracenew(const_cast<char*>(file),line);
#endif
    };
    return services;
}
}
