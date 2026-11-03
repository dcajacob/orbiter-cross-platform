// Copyright (c) Martin Schweiger
// Licensed under the MIT License
ORBITER_MENU_EXPORT bool MenuButton(const char *label, const char *tooltip, float xoffset)
	{
		ImGuiContext& g = *GImGui;
		const ImGuiWindow* window = ImGui::GetCurrentWindow();
		const ImRect titleBarRect = window->TitleBarRect();
		const ImGuiStyle& style = g.Style;
        ImGuiLastItemData last_item_backup = g.LastItemData;
		ImGui::PushClipRect( titleBarRect.Min, titleBarRect.Max, false );
		float width = (strlen(label)+1) * g.FontSize;
		float offset = titleBarRect.Max.x - width - titleBarRect.Min.x - g.Style.FramePadding.x;
		offset -= xoffset;
		ImGui::SetCursorPos( ImVec2( offset, 0.0f ) );
		ImGui::PushStyleVar(ImGuiStyleVar_FrameBorderSize, 0.0f);   // no border
		ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0,0,0,0));
		ImGui::PushStyleColor(ImGuiCol_Border, ImVec4(0,0,0,0));    // invisible border color		bool ret = ImGui::Button( label );
		bool ret = ImGui::Button( label );
		ImGui::PopStyleColor(2);
		ImGui::PopStyleVar();
		if(tooltip && ImGui::IsItemHovered())
			ImGui::SetTooltip(tooltip);
		ImGui::PopClipRect();
        g.LastItemData = last_item_backup;
		return ret;
	}
