#ifndef RATANA_ISLAND_WINDOW_H
#define RATANA_ISLAND_WINDOW_H

#include <gtk/gtk.h>
#include "settings.h"
#include "state_manager.h"
#include "media.h"
#include "notifications.h"
#include "system_status.h"

G_BEGIN_DECLS

#define RATANA_TYPE_ISLAND_WINDOW (ratana_island_window_get_type())
G_DECLARE_FINAL_TYPE(RatanaIslandWindow, ratana_island_window, RATANA, ISLAND_WINDOW, GtkApplicationWindow)

RatanaIslandWindow *ratana_island_window_new(GtkApplication *app,
                                             RatanaSettings *settings,
                                             StateManager *state_mgr,
                                             MediaManager *media_mgr);

void ratana_island_window_update_media(RatanaIslandWindow *win, const TrackInfo *track);
void ratana_island_window_update_workspace(RatanaIslandWindow *win, const char *change, const char *ws_name);
void ratana_island_window_update_notification(RatanaIslandWindow *win, const NotificationInfo *notif);
void ratana_island_window_update_status(RatanaIslandWindow *win, const SystemStatusInfo *status, gboolean is_vol);
void ratana_island_window_apply_state(RatanaIslandWindow *win, IslandState state, gboolean animated);
void ratana_island_window_toggle_expanded(RatanaIslandWindow *win);
void ratana_island_window_reload_settings(RatanaIslandWindow *win);
void ratana_island_window_open_settings(RatanaIslandWindow *win);

G_END_DECLS

#endif /* RATANA_ISLAND_WINDOW_H */
