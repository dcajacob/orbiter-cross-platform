// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "NativeAnnotations.h"
#include "NativeInterpreterSdk.h"
#include "RigidBodyServices.h"
#include <algorithm>
#include <cstring>
using namespace orbiter::production;
using AnnotationClient=NativeGraphics;
using std::min;
namespace oapi {
class ScreenAnnotation {
public:
	/**
	 * \brief Constructs a new annotation object
	 * \param _gc pointer to graphics client
	 */
	ScreenAnnotation (AnnotationClient *_gc);

	/**
	 * \brief Destroys the annotation object
	 */
	virtual ~ScreenAnnotation();

	/**
	 * \brief Resets annotation parameters to their default values
	 */
	virtual void Reset ();

	/**
	 * \brief Set the text to be displayed by the annotation object
	 * \param str character string
	 */
	virtual void SetText (char *str);

	/**
	 * \brief Clear the text display
	 */
	virtual void ClearText ();

	/**
	 * \brief Set the bounding box of the annotation block
	 * \param x1 left edge
	 * \param y1 top edge
	 * \param x2 right edge
	 * \param y2 bottom edge
	 * \note The positions are relative to the boundaries of the render window,
	 *   in the range 0 to 1, where (0,0) is the top left edge, and (1,1) is the
	 *   bottom right edge of the render window.
	 */
	virtual void SetPosition (double x1, double y1, double x2, double y2);

	/**
	 * \brief Set the font size
	 * \param scale font size parameter (>0)
	 * \note scale=1 defines the default font size, scale<1 is a smaller font,
	 *   and scale>1 a larger font.
	 * \note The default font size is automatically scaled with the size of the
	 *   render window.
	 */
	virtual void SetSize (double scale);

	/**
	 * \brief Set the font colour
	 * \param col RGB values of the font colour (0..1 in each component)
	 */
	virtual void SetColour (const VECTOR3 &col);

	/**
	 * \brief Render the annotation text into the simulation window.
	 */
	virtual void Render ();

private:
	AnnotationClient *gc;
	oapi::UInt32 viewW, viewH;
	int nw, nh, nx1, ny1, nx2, ny2, hf;
	int txtlen, buflen;
	char *txt;
	double txtscale;
	oapi::Font *font;
	oapi::UInt32 txtcol, txtcol2;
};
#define TRACENEW GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
#include "ScreenAnnotationMethods.inc"
#undef TRACENEW
}

NativeAnnotations::NativeAnnotations() = default;
NativeAnnotations::~NativeAnnotations() = default;
NOTEHANDLE NativeAnnotations::Create(double size,const VECTOR3 &col)
{
    auto *client=GetNativeRenderContext().graphics;
    if (!client) return nullptr;
    auto note=std::make_unique<oapi::ScreenAnnotation>(client);
    note->SetSize(size);
    auto channel=[](double c) {return (static_cast<unsigned>(c*255.99)&255u)/256.0;};
    note->SetColour(_V(channel(col.x),channel(col.y),channel(col.z)));
    auto *handle=note.get();
    notes.push_back(std::move(note));
    return handle;
}
bool NativeAnnotations::Remove(NOTEHANDLE handle)
{
    auto it=std::find_if(notes.begin(),notes.end(),[&](const auto& note){return note.get()==handle;});
    if (it==notes.end()) return false;
    notes.erase(it);
    return true;
}
void NativeAnnotations::Render() {for (auto &note:notes) note->Render();}
void NativeAnnotations::Clear() {notes.clear();}
NOTEHANDLE oapiCreateAnnotation(bool,double size,const VECTOR3 &col)
{
    auto *notes=GetNativeRenderContext().annotations;
    return notes ? notes->Create(size,col) : nullptr;
}
bool oapiDelAnnotation(NOTEHANDLE handle)
{
    auto *notes=GetNativeRenderContext().annotations;
    return notes && notes->Remove(handle);
}
void oapiAnnotationSetPos (NOTEHANDLE hNote, double x1, double y1, double x2, double y2)
{
	if (hNote) {
		oapi::ScreenAnnotation *sn = (oapi::ScreenAnnotation*)hNote;
		sn->SetPosition (x1, y1, x2, y2);
	}
}

void oapiAnnotationSetSize (NOTEHANDLE hNote, double size)
{
	if (hNote) {
		oapi::ScreenAnnotation *sn = (oapi::ScreenAnnotation*)hNote;
		sn->SetSize (size);
	}
}

void oapiAnnotationSetColour (NOTEHANDLE hNote, const VECTOR3 &col)
{
	if (hNote) {
		oapi::ScreenAnnotation *sn = (oapi::ScreenAnnotation*)hNote;
		sn->SetColour (col);
	}
}

void oapiAnnotationSetText (NOTEHANDLE hNote, char *note)
{
	if (hNote) {
		oapi::ScreenAnnotation *sn = (oapi::ScreenAnnotation*)hNote;
		if (note) sn->SetText (note);
		else sn->ClearText();
	}
}
