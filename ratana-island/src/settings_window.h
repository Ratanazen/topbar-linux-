#ifndef RATANA_SETTINGS_WINDOW_H
#define RATANA_SETTINGS_WINDOW_H

#include <gtk/gtk.h>
#include "settings.h"
#include "island_window.h"

G_BEGIN_DECLS

void ratana_settings_window_present(GtkApplication *app,
                                    RatanaSettings *settings,
                                    RatanaIslandWindow *island_win);

G_END_DECLS

#endif /* RATANA_SETTINGS_WINDOW_H */
