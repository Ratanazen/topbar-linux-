#ifndef RATANA_SETTINGS_H
#define RATANA_SETTINGS_H

#include <glib.h>

G_BEGIN_DECLS

typedef struct _RatanaSettings {
    int collapsed_width;
    int collapsed_height;
    int expanded_width;
    int expanded_height;
    int top_margin;
    int corner_radius_collapsed;
    int corner_radius_expanded;
    int animation_duration_ms;
    gboolean reduced_motion;
    gboolean low_power_mode;
    gboolean privacy_mode;
    char *theme;
    char *monitor;
    int workspace_timeout_ms;
    int volume_timeout_ms;
    int notification_timeout_ms;
    int battery_low_threshold;
    gboolean enable_media;
    gboolean enable_sway;
    gboolean enable_notifications;
    gboolean enable_system_status;
} RatanaSettings;

RatanaSettings *ratana_settings_new_default(void);
void ratana_settings_free(RatanaSettings *settings);
RatanaSettings *ratana_settings_load(const char *path);
gboolean ratana_settings_save(const RatanaSettings *settings, const char *path);
char *ratana_settings_get_default_path(void);

G_END_DECLS

#endif /* RATANA_SETTINGS_H */
