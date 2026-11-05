// Original Orbiter::KbdInputBuffered_OnRunning Shift-key MFD selection.
int id = (KEYDOWN(kstate, OAPI_KEY_LSHIFT) ? 0 : 1);
g_pane->MFDConsumeKeyBuffered(id, key);
