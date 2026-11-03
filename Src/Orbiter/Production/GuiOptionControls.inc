	// Resettable slider from https://github.com/ocornut/imgui/issues/1751
	ORBITER_WIDGET_EXPORT bool SliderFloatReset(const char* label, float* v, float v_min, float v_max, float v_default, const char* display_format)
	{
		bool ret = ImGui::SliderFloat(label, v, v_min, v_max, display_format);
		if (ImGui::BeginPopupContextItem(label))
		{
			char buf[64];
			sprintf(buf, "Reset to %f", v_default);
			if (ImGui::MenuItem(buf))
				*v = v_default;
			ImGui::MenuItem("Close");
			ImGui::EndPopup();
		}
		return ret;
	}

	// Cheap double slider
	// It's provided only to be able to use sliders where a double is used but a float would have been enough
	// e.g. the stars brightness configuration
	ORBITER_WIDGET_EXPORT bool SliderDouble(const char* label, double* v, double v_min, double v_max, const char* display_format)
	{
		float tmp = *v;
		bool ret = ImGui::SliderFloat(label, &tmp, v_min, v_max, display_format);
		if(ret) *v = tmp;
		return ret;
	}

	ORBITER_WIDGET_EXPORT bool InputIntEx(const char* label, int* v, int v_min, int v_max, int step, int step_fast, ImGuiInputTextFlags flags)
	{
		bool ret = ImGui::InputInt(label, v, step, step_fast, flags);
		if(ret) {
			if(*v < v_min) *v = v_min;
			else if (*v > v_max) *v = v_max;
		}
		return ret;
	}
	ORBITER_WIDGET_EXPORT bool InputDoubleEx(const char* label, double* v, double v_min, double v_max, double step, double step_fast, const char *fmt, ImGuiInputTextFlags flags)
	{
		bool ret = ImGui::InputDouble(label, v, step, step_fast, fmt, flags);
		if(ret) {
			if(*v < v_min) *v = v_min;
			else if (*v > v_max) *v = v_max;
		}
		return ret;
	}


	ORBITER_WIDGET_EXPORT bool SliderEnum(const char *label, int *v, const char *values[], int nvalues)
	{
        const char* elem_name = (*v >= 0 && *v < nvalues) ? values[*v] : "Unknown";
        return ImGui::SliderInt(label, v, 0, nvalues - 1, elem_name);
	}
