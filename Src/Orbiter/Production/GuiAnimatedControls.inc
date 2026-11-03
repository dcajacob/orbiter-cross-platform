// Copyright (c) Martin Schweiger
// Licensed under the MIT License
	ORBITER_WIDGET_EXPORT bool BeginAnimatedCombo(const char* label, const char* preview_value, ImGuiComboFlags flags, float duration)
	{
		ImGuiContext& g = *GImGui;
		ImGuiID id = g.CurrentWindow->GetID(label);
		FadingState& S = g_popupStates[id];

		float alpha = 1.0f;
		if (S.state == FadingState::Opening) {
			S.animstate += ImGui::GetIO().DeltaTime;
			if (S.animstate >= duration) {
				S.state = FadingState::Open;
			} else {
				float x = ImClamp(S.animstate / duration, 0.0f, 1.0f);
				alpha = x * x * (3.0f - 2.0f * x);
			}
		}

		ImVec4 bc = ImGui::GetStyleColorVec4(ImGuiCol_Border);
		ImVec4 bs = ImGui::GetStyleColorVec4(ImGuiCol_BorderShadow);
		bc.w *= alpha;
		bs.w *= alpha;
		ImGui::PushStyleColor(ImGuiCol_Border, bc);
		ImGui::PushStyleColor(ImGuiCol_BorderShadow, bs);
		ImGui::SetNextWindowBgAlpha(alpha);

		if (ImGui::BeginCombo(label, preview_value, flags)) {
			ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);

			if(S.state == FadingState::Closed) {
				S.state = FadingState::Opening;
				S.animstate = 0.0f;
			}
		} else {
			S.state = FadingState::Closed;
			ImGui::PopStyleColor(2);
			return false;
		}

		return true;
	}

    ORBITER_WIDGET_EXPORT void EndAnimatedCombo()
	{
		ImGui::PopStyleColor(2);
		ImGui::PopStyleVar();
		ImGui::EndCombo();
	}

	struct AnimatedHeaderState
	{
		enum State { Closed, Opening, Closing, Open } state = Closed;
		float speed;
		float height = 0.0f;
		ImVec2 startPos;
		std::string childname;
	};
	static std::unordered_map<ImGuiID, AnimatedHeaderState> g_headerStates;
	static std::vector<ImGuiID> g_stackHeaders;
	ORBITER_WIDGET_EXPORT bool BeginAnimatedCollapsingHeader(const char* label, ImGuiTreeNodeFlags flags, float speed)
	{
		ImGuiWindow* window = GetCurrentWindow();
		if (window->SkipItems)
			return false;

		ImGuiID id = ImGui::GetID(label);
		auto found = g_headerStates.find(id);
		auto& state = g_headerStates[id];
		state.speed = speed;

		// First time with see this widget,
		if(found == g_headerStates.end()) {
			state.childname = std::string(label) + "_child";
			// Check to see if it should be open
			if(flags & ImGuiTreeNodeFlags_DefaultOpen)
				state.state = AnimatedHeaderState::Open;
		}

		bool visible = ImGui::CollapsingHeader(label, flags);

		if(visible) {
			switch(state.state) {
				case AnimatedHeaderState::Closed:
					state.state = AnimatedHeaderState::Opening;
					break;
				case AnimatedHeaderState::Closing:
					state.state = AnimatedHeaderState::Opening;
					break;
				case AnimatedHeaderState::Opening:
				case AnimatedHeaderState::Open:
					break;
			}
		} else {
			switch(state.state) {
				case AnimatedHeaderState::Open:
					state.state = AnimatedHeaderState::Closing;
					break;
				case AnimatedHeaderState::Opening:
					state.state = AnimatedHeaderState::Closing;
					break;
				case AnimatedHeaderState::Closing:
				case AnimatedHeaderState::Closed:
					break;
			}
		}

		// If it's closed, EndAnimatedCollapsingHeader won't be called
		// so we need to exit before pushing the id to the stack
		if(state.state == AnimatedHeaderState::Closed) return false;
		g_stackHeaders.push_back(id);

		// If the block is fully deployed, we use a BeginGroup/EndGroup section
		// To compute the height of the whole block in EndAnimatedCollapsingHeader
		if(state.state == AnimatedHeaderState::Open) {
			state.startPos = ImGui::GetCursorScreenPos();
			ImGui::BeginGroup();
			return true;
		}

		// Use a child during the animation, we clamp its height to create
		// a sliding effect
		ImGui::BeginChild(state.childname.c_str(),
							ImVec2(-FLT_MIN, state.height), ImGuiChildFlags_AutoResizeY, ImGuiWindowFlags_NoDecoration);

		return true;
	}

	ORBITER_WIDGET_EXPORT void EndAnimatedCollapsingHeader()
	{
		auto id = g_stackHeaders.back();
		g_stackHeaders.pop_back();

		auto& state = g_headerStates[id];
		// Compute the height of the block
		if(state.state == AnimatedHeaderState::Open) {
			ImGui::EndGroup();

			ImVec2 endPos = ImGui::GetItemRectMax();
			state.height = endPos.y - state.startPos.y;
			return;
		}

		ImVec2 available = ImGui::GetContentRegionAvail();

		switch(state.state) {
			case AnimatedHeaderState::Opening:
				// A negative available.y indicates that the content is
				// too tall to fit in the given height -> we increase it
				// Otherwise we can stop the animation
				if(available.y < 0) {
					state.height += ImGui::GetIO().DeltaTime * state.speed;
				} else {
					state.state = AnimatedHeaderState::Open;
					// Prevent too much overshooting
					float ypos = ImGui::GetCursorPosY();
					ypos -= available.y;
					ImGui::SetCursorPosY(ypos);
					ImGui::Dummy(ImVec2(0,0));
				}
				break;
			case AnimatedHeaderState::Closing:
				state.height -= ImGui::GetIO().DeltaTime * state.speed;
				if(state.height <= 0.0) {
					state.height = 0;
					state.state = AnimatedHeaderState::Closed;
				}
				break;
			case AnimatedHeaderState::Open:
			case AnimatedHeaderState::Closed:
				break; // should not be here
		}
		ImGui::EndChild();
	}
