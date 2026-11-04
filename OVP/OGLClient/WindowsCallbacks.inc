// Private Windows adapter declarations. The public SDK is included unchanged.
SURFHANDLE clbkLoadTexture(const char *name,DWORD flags) override { return LoadTexture(name,int(flags)); }
SURFHANDLE clbkLoadSurface(const char *name,DWORD flags,bool path) override;
bool clbkSetMeshTexture(DEVMESHHANDLE mesh,DWORD index,SURFHANDLE texture) override { return SetMeshTexture(mesh,int(index),texture); }
int clbkSetMeshMaterial(DEVMESHHANDLE mesh,DWORD index,const MATERIAL *mat) override { return SetMeshMaterial(mesh,int(index),mat); }
int clbkMeshMaterial(DEVMESHHANDLE mesh,DWORD index,MATERIAL *mat) override { return MeshMaterial(mesh,int(index),mat); }
bool clbkSetMeshProperty(DEVMESHHANDLE mesh,DWORD property,DWORD value) override { return SetMeshProperty(mesh,int(property),int(value)); }
int clbkGetMeshGroup(DEVMESHHANDLE mesh,DWORD index,GROUPREQUESTSPEC *request) override { return GetMeshGroup(mesh,int(index),request); }
int clbkEditMeshGroup(DEVMESHHANDLE mesh,DWORD index,GROUPEDITSPEC *edit) override { return EditMeshGroup(mesh,int(index),edit); }
void clbkGetViewportSize(DWORD *w,DWORD *h) const override { int a,b;GetViewportSize(&a,&b);*w=a;*h=b; }
bool clbkGetRenderParam(DWORD param,DWORD *value) const override { int v;bool ok=GetRenderParam(int(param),&v);if(ok)*value=v;return ok; }
SURFHANDLE clbkCreateSurfaceEx(DWORD w,DWORD h,DWORD flags) override { return CreateSurfaceEx(int(w),int(h),int(flags)); }
SURFHANDLE clbkCreateSurface(DWORD w,DWORD h,SURFHANDLE pattern) override { return CreateSurface(int(w),int(h),pattern); }
SURFHANDLE clbkCreateSurface(HBITMAP bitmap) override;
HDC clbkGetSurfaceDC(SURFHANDLE surface) override;
void clbkReleaseSurfaceDC(SURFHANDLE surface,HDC dc) override;
SURFHANDLE clbkCreateTexture(DWORD w,DWORD h) override { return CreateTexture(int(w),int(h)); }
bool clbkGetSurfaceSize(SURFHANDLE s,DWORD *w,DWORD *h) override { int a,b;bool ok=GetSurfaceSize(s,&a,&b);if(ok){*w=a;*h=b;}return ok; }
bool clbkSetSurfaceColourKey(SURFHANDLE s,DWORD key) override { return SetSurfaceColourKey(s,key); }
DWORD clbkGetDeviceColour(BYTE r,BYTE g,BYTE b) override { return GetDeviceColour(r,g,b); }
bool clbkBlt(SURFHANDLE t,DWORD x,DWORD y,SURFHANDLE s,DWORD flags) const override { return Blt(t,int(x),int(y),s,int(flags)); }
bool clbkBlt(SURFHANDLE t,DWORD x,DWORD y,SURFHANDLE s,DWORD sx,DWORD sy,DWORD w,DWORD h,DWORD flags) const override { return Blt(t,int(x),int(y),s,int(sx),int(sy),int(w),int(h),int(flags)); }
bool clbkScaleBlt(SURFHANDLE t,DWORD x,DWORD y,DWORD w,DWORD h,SURFHANDLE s,DWORD sx,DWORD sy,DWORD sw,DWORD sh,DWORD flags) const override { return ScaleBlt(t,int(x),int(y),int(w),int(h),s,int(sx),int(sy),int(sw),int(sh),int(flags)); }
bool clbkFillSurface(SURFHANDLE s,DWORD color) const override { return FillSurface(s,color); }
bool clbkFillSurface(SURFHANDLE s,DWORD x,DWORD y,DWORD w,DWORD h,DWORD color) const override { return FillSurface(s,int(x),int(y),int(w),int(h),color); }
Sketchpad *clbkGetSketchpad(SURFHANDLE s) override { return GetSketchpad(s,true); }
Font *clbkCreateFont(int height,bool prop,const char *face,FontStyle style,int orientation) const override { return CreateFont(height,prop,face,style,orientation,true); }
Pen *clbkCreatePen(int style,int width,DWORD color) const override { return CreatePen(style,width,color); }
Brush *clbkCreateBrush(DWORD color) const override { return CreateBrush(color); }
void clbkImGuiInit() override;
void clbkImGuiShutdown() override;
uint64_t clbkImGuiSurfaceTexture(SURFHANDLE surface) override;
LRESULT RenderWndProc(HWND window,UINT message,WPARAM wparam,LPARAM lparam) override;
