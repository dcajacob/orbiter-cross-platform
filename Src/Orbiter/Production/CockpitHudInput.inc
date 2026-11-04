	// HUD control (internal view only)
	if (g_camera->IsInternal()) {
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUD))          g_pane->ToggleHUD();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDMode))      g_pane->SwitchHUDMode();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDReference))
			if (g_pane->GetHUD())                                      g_pane->GetHUD()->SelectReference();
		if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_HUDTarget))
			if (g_pane->GetHUD() && g_pane->GetHUD()->Mode() == HUD_DOCKING)    ((HUD_Docking*)g_pane->GetHUD())->SelectReferenceOld();
	}

