// Copyright (c) Martin Schweiger
// Licensed under the MIT License
if (sa) {
	if (!strcmp (s+4, "COL")) {
		double r, g, b;
		if (sscanf (s+8, "%lf%lf%lf", &r, &g, &b)==3) {
			VECTOR3 col = {r,g,b};
			sa->SetColour (col);
		}
	} else if (!strcmp (s+4, "SIZE")) {
		double scale;
		if (sscanf (s+9, "%lf", &scale)==1) sa->SetSize (scale);
	} else if (!strcmp (s+4, "POS")) {
		double x1, y1, x2, y2;
		if (sscanf (s+8, "%lf%lf%lf%lf", &x1, &y1, &x2, &y2)==4) sa->SetPosition (x1, y1, x2, y2);
	} else if (!strcmp (s+4, "OFF")) {
		sa->ClearText();
	} else {
		sa->SetText (s+5);
	}
}
