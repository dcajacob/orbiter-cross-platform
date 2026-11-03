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
void CloseSession() override {SetCameraRotation(false);clbkCloseSession(false);}
void Close() override {clbkDestroyRenderWindow(false);}
SURFHANDLE LoadTextureResource(const char* name,oapi::UInt32 flags) override {return LoadTexture(name,int(flags));}
std::uint64_t GuiTextureId(SURFHANDLE surface) override {return surface ? static_cast<OGLTexture*>(surface)->m_TexId : 0;}
bool ReleaseTextureResource(SURFHANDLE texture) override {return clbkReleaseSurface(texture);}
void StoreMesh(MESHHANDLE mesh,const char* name) override {clbkStoreMeshPersistent(mesh,name);}
void VisualEvent(OBJHANDLE object,VISHANDLE visual,oapi::UInt32 event,std::uintptr_t data) override {clbkVisEvent(object,visual,event,data);}
oapi::Font* CreateFontResource(int height,bool prop,const char* face,FontStyle style,int orientation) override {return CreateFont(height,prop,face,style,orientation,true);}
void ReleaseFontResource(oapi::Font* font) override {clbkReleaseFont(font);}
oapi::Pen* CreatePenResource(int style,int width,oapi::UInt32 color) override {return CreatePen(style,width,color);}
void ReleasePenResource(oapi::Pen* pen) override {clbkReleasePen(pen);}
oapi::Brush* CreateBrushResource(oapi::UInt32 color) override {return CreateBrush(color);}
void ReleaseBrushResource(oapi::Brush* brush) override {clbkReleaseBrush(brush);}
oapi::Sketchpad* AcquireSketchpad(SURFHANDLE surface) override {return GetSketchpad(surface,true);}
void ReleaseSketchpadResource(oapi::Sketchpad* pad) override {clbkReleaseSketchpad(pad);}
SURFHANDLE CreateSurfaceResource(int w,int h) override {return CreateSurface(w,h);}
int MeshGroup(DEVMESHHANDLE mesh,oapi::UInt32 index,GROUPREQUESTSPEC* request) override {return GetMeshGroup(mesh,int(index),request);}
oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel,const double* level,const VECTOR3* pos,const VECTOR3* dir) override {return clbkCreateExhaustStream(spec,vessel,level,pos,dir);}
oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel,const double* level,const VECTOR3& pos,const VECTOR3& dir) override {return clbkCreateExhaustStream(spec,vessel,level,pos,dir);}
oapi::ParticleStream* Reentry(PARTICLESTREAMSPEC* spec,OBJHANDLE vessel) override {return clbkCreateReentryStream(spec,vessel);}

void clbkGetViewportSize(oapi::UInt32* width,oapi::UInt32* height) const override {int w,h;GetViewportSize(&w,&h);*width=w;*height=h;}

SURFHANDLE clbkCreateSurfaceEx(oapi::UInt32 w,oapi::UInt32 h,oapi::UInt32 flags) override {return CreateSurfaceEx(int(w),int(h),int(flags));}
oapi::UInt32 clbkGetDeviceColour(std::uint8_t r,std::uint8_t g,std::uint8_t b) override {return GetDeviceColour(r,g,b);}
bool clbkFillSurface(SURFHANDLE surface,oapi::UInt32 color) const override {return FillSurface(surface,color);}
bool clbkFillSurface(SURFHANDLE surface,oapi::UInt32 x,oapi::UInt32 y,oapi::UInt32 w,oapi::UInt32 h,oapi::UInt32 color) const override {return FillSurface(surface,int(x),int(y),int(w),int(h),color);}
bool clbkBlt(SURFHANDLE t,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE s,oapi::UInt32 flags) const override {return Blt(t,int(x),int(y),s,int(flags));}
bool clbkBlt(SURFHANDLE t,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE s,oapi::UInt32 sx,oapi::UInt32 sy,oapi::UInt32 w,oapi::UInt32 h,oapi::UInt32 flags) const override {return Blt(t,int(x),int(y),s,int(sx),int(sy),int(w),int(h),int(flags));}

int DesktopHeight() const override;
std::vector<orbiter::production::NativeJoystickDevice> Joysticks() const override;
oapi::SdkPoint CursorPosition() const override;
void SetCursorPosition(oapi::SdkPoint) override;
void SetCameraRotation(bool) override;

bool clbkGetRenderParam(oapi::UInt32 parameter,oapi::UInt32* value) const override {int result=0;const bool ok=GetRenderParam(int(parameter),&result);if(ok)*value=oapi::UInt32(result);return ok;}
SURFHANDLE clbkLoadSurface(const char* name,oapi::UInt32 flags,bool) override {return LoadSurface(name,int(flags));}
SURFHANDLE clbkCreateTexture(oapi::UInt32 w,oapi::UInt32 h) override {return CreateTexture(int(w),int(h));}
bool clbkGetSurfaceSize(SURFHANDLE surface,oapi::UInt32* width,oapi::UInt32* height) override {int w=0,h=0;const bool ok=GetSurfaceSize(surface,&w,&h);if(ok){*width=w;*height=h;}return ok;}
bool clbkScaleBlt(SURFHANDLE t,oapi::UInt32 x,oapi::UInt32 y,oapi::UInt32 w,oapi::UInt32 h,SURFHANDLE s,oapi::UInt32 sx,oapi::UInt32 sy,oapi::UInt32 sw,oapi::UInt32 sh,oapi::UInt32 flags) const override {return ScaleBlt(t,int(x),int(y),int(w),int(h),s,int(sx),int(sy),int(sw),int(sh),int(flags));}

void InitGui() override;
void NewGuiFrame() override;
void RenderGui() override;
void ShutdownGui() override;

void ReplayGuiInput(const std::string&,int,int,const std::string&) override;
