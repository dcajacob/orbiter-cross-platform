// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_GUI_DATA_H
#define ORBITER_GUI_DATA_H
#include <string>
#include <cstddef>
typedef struct {
	char *helpfile; 
	char *topic;
	char *toc;
	char *index;
} HELPCONTEXT;

class OAPIFUNC ImGuiDialog {
	struct ImGuiDefaultSize {
		float width;
		float height;
	};
public:
	/**
	 * \brief Create an ImGui dialog object.
	 * \param name Name of the dialog window
	 * \note This class must by derived from in order to define a custom ImGui dialog
	 */
	ImGuiDialog(const char *n, ImGuiDefaultSize ds = {350.0,280.0}):name(n),defaultSize(ds) {}
	virtual ~ImGuiDialog();
	bool IsActive() { return active; }
	void Activate();
	virtual void Display();
	void SetHelp(const char *file, const char *topic = NULL) {
		helpfile = file;
		if(topic)
			helptopic = topic;
		else
			helptopic.clear();
	}
	bool HandleHelpButton();
protected:
	/**
	 * \brief Callback that is executed when the dialog is closed.
	 * \note The default behavior is to do nothing
	 */
	virtual void OnClose() {};
	/**
	 * \brief Callback that is executed when the dialog should be drawn.
	 * \note Orbiter takes care of doing the ImGui::Begin() / ImGui::End() pair
	 * required to create the window and handle its visibility.
	 * \note ImGui documentation is available at https://github.com/ocornut/imgui
	 */
	virtual void OnDraw() = 0;
	bool active = false;
	const std::string name;
	ImGuiDefaultSize defaultSize;
	std::string helpfile;
	std::string helptopic;
};
#endif
