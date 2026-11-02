// Native adapter to the same OpenGL implementation. Window ownership is GLFW.
void Open() override;
RenderInput Poll() override;
void Resize(int,int) override;
void Status(const std::string&) override;
void PostCreation() override {clbkPostCreation();}
void NewVessel(OBJHANDLE vessel) override {clbkNewVessel(vessel);}
void DeleteVessel(OBJHANDLE vessel) override {clbkDeleteVessel(vessel);}
void Render() override {clbkClearFrame();clbkRenderScene();}
bool Present() override {return clbkDisplayFrame();}
void CloseSession() override {clbkCloseSession(false);}
void Close() override {clbkDestroyRenderWindow(false);}
SURFHANDLE LoadTextureResource(const char* name,oapi::UInt32 flags) override {return LoadTexture(name,int(flags));}
bool ReleaseTextureResource(SURFHANDLE texture) override {return clbkReleaseSurface(texture);}
void StoreMesh(MESHHANDLE mesh,const char* name) override {clbkStoreMeshPersistent(mesh,name);}
void VisualEvent(OBJHANDLE object,VISHANDLE visual,oapi::UInt32 event,std::uintptr_t data) override {clbkVisEvent(object,visual,event,data);}
oapi::Font* CreateFontResource(int height,bool prop,const char* face,FontStyle style,int orientation) override {return CreateFont(height,prop,face,style,orientation,true);}
void ReleaseFontResource(oapi::Font* font) override {clbkReleaseFont(font);}
oapi::Pen* CreatePenResource(int style,int width,oapi::UInt32 color) override {return CreatePen(style,width,color);}
void ReleasePenResource(oapi::Pen* pen) override {clbkReleasePen(pen);}
oapi::Sketchpad* AcquireSketchpad(SURFHANDLE surface) override {return GetSketchpad(surface,true);}
void ReleaseSketchpadResource(oapi::Sketchpad* pad) override {clbkReleaseSketchpad(pad);}
SURFHANDLE CreateSurfaceResource(int w,int h) override {return CreateSurface(w,h);}
int MeshGroup(DEVMESHHANDLE mesh,oapi::UInt32 index,GROUPREQUESTSPEC* request) override {return GetMeshGroup(mesh,int(index),request);}
oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel,const double* level,const VECTOR3* pos,const VECTOR3* dir) override {return clbkCreateExhaustStream(spec,vessel,level,pos,dir);}
oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel,const double* level,const VECTOR3& pos,const VECTOR3& dir) override {return clbkCreateExhaustStream(spec,vessel,level,pos,dir);}
oapi::ParticleStream* Reentry(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel) override {return clbkCreateReentryStream(spec,vessel);}

void clbkGetViewportSize(oapi::UInt32* width,oapi::UInt32* height) const override {int w,h;GetViewportSize(&w,&h);*width=w;*height=h;}
