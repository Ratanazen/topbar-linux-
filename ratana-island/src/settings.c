#include "settings.h"
#include <glib/gstdio.h>

#define GROUP_GENERAL     "General"
#define GROUP_DIMENSIONS  "Dimensions"
#define GROUP_INTEGRATION "Integrations"
#define GROUP_ANIMATION   "Animation"

RatanaSettings *ratana_settings_new_default(void) {
    RatanaSettings *s = g_new0(RatanaSettings, 1);
    s->collapsed_width = 190;
    s->collapsed_height = 32;
    s->expanded_width = 380;
    s->expanded_height = 165;
    s->top_margin = 4;
    s->corner_radius_collapsed = 16;
    s->corner_radius_expanded = 36;
    s->animation_duration_ms = 240;
    s->reduced_motion = FALSE;
    s->low_power_mode = FALSE;
    s->privacy_mode = FALSE;
    s->theme = g_strdup("mac_obsidian");
    s->monitor = g_strdup("");
    s->workspace_timeout_ms = 1500;
    s->volume_timeout_ms = 1500;
    s->notification_timeout_ms = 4000;
    s->battery_low_threshold = 20;
    s->enable_media = TRUE;
    s->enable_sway = TRUE;
    s->enable_notifications = TRUE;
    s->enable_system_status = TRUE;
    return s;
}

void ratana_settings_free(RatanaSettings *settings) {
    if (!settings) return;
    g_free(settings->theme);
    g_free(settings->monitor);
    g_free(settings);
}

char *ratana_settings_get_default_path(void) {
    const char *config_home = g_get_user_config_dir();
    return g_build_filename(config_home, "ratana-island", "config.ini", NULL);
}

RatanaSettings *ratana_settings_load(const char *path) {
    char *allocated_path = NULL;
    if (!path) {
        allocated_path = ratana_settings_get_default_path();
        path = allocated_path;
    }

    RatanaSettings *s = ratana_settings_new_default();
    GKeyFile *kf = g_key_file_new();
    GError *error = NULL;

    if (!g_file_test(path, G_FILE_TEST_EXISTS)) {
        ratana_settings_save(s, path);
        g_key_file_free(kf);
        g_free(allocated_path);
        return s;
    }

    if (!g_key_file_load_from_file(kf, path, G_KEY_FILE_NONE, &error)) {
        g_warning("Could not parse config file %s: %s (using defaults)", path, error ? error->message : "unknown");
        if (error) g_error_free(error);
        g_key_file_free(kf);
        g_free(allocated_path);
        return s;
    }

    #define GET_INT(grp, key, field) do { \
        if (g_key_file_has_key(kf, grp, key, NULL)) { \
            int val = g_key_file_get_integer(kf, grp, key, NULL); \
            if (val > 0) s->field = val; \
        } \
    } while (0)

    #define GET_BOOL(grp, key, field) do { \
        if (g_key_file_has_key(kf, grp, key, NULL)) { \
            s->field = g_key_file_get_boolean(kf, grp, key, NULL); \
        } \
    } while (0)

    GET_INT(GROUP_DIMENSIONS, "collapsed_width", collapsed_width);
    GET_INT(GROUP_DIMENSIONS, "collapsed_height", collapsed_height);
    GET_INT(GROUP_DIMENSIONS, "expanded_width", expanded_width);
    GET_INT(GROUP_DIMENSIONS, "expanded_height", expanded_height);
    if (g_key_file_has_key(kf, GROUP_DIMENSIONS, "top_margin", NULL)) {
        s->top_margin = g_key_file_get_integer(kf, GROUP_DIMENSIONS, "top_margin", NULL);
    }
    GET_INT(GROUP_DIMENSIONS, "corner_radius_collapsed", corner_radius_collapsed);
    GET_INT(GROUP_DIMENSIONS, "corner_radius_expanded", corner_radius_expanded);

    GET_INT(GROUP_ANIMATION, "duration_ms", animation_duration_ms);
    GET_BOOL(GROUP_ANIMATION, "reduced_motion", reduced_motion);

    GET_BOOL(GROUP_GENERAL, "low_power_mode", low_power_mode);
    GET_BOOL(GROUP_GENERAL, "privacy_mode", privacy_mode);

    if (g_key_file_has_key(kf, GROUP_GENERAL, "theme", NULL)) {
        char *t = g_key_file_get_string(kf, GROUP_GENERAL, "theme", NULL);
        if (t && *t) {
            g_free(s->theme);
            s->theme = t;
        } else {
            g_free(t);
        }
    }

    if (g_key_file_has_key(kf, GROUP_GENERAL, "monitor", NULL)) {
        char *m = g_key_file_get_string(kf, GROUP_GENERAL, "monitor", NULL);
        if (m) {
            g_free(s->monitor);
            s->monitor = m;
        }
    }

    GET_BOOL(GROUP_INTEGRATION, "enable_media", enable_media);
    GET_BOOL(GROUP_INTEGRATION, "enable_sway", enable_sway);
    GET_BOOL(GROUP_INTEGRATION, "enable_notifications", enable_notifications);
    GET_BOOL(GROUP_INTEGRATION, "enable_system_status", enable_system_status);

    GET_INT(GROUP_INTEGRATION, "workspace_timeout_ms", workspace_timeout_ms);
    GET_INT(GROUP_INTEGRATION, "volume_timeout_ms", volume_timeout_ms);
    GET_INT(GROUP_INTEGRATION, "notification_timeout_ms", notification_timeout_ms);
    GET_INT(GROUP_INTEGRATION, "battery_low_threshold", battery_low_threshold);

    #undef GET_INT
    #undef GET_BOOL

    g_key_file_free(kf);
    g_free(allocated_path);
    return s;
}

gboolean ratana_settings_save(const RatanaSettings *settings, const char *path) {
    if (!settings) return FALSE;

    char *allocated_path = NULL;
    if (!path) {
        allocated_path = ratana_settings_get_default_path();
        path = allocated_path;
    }

    char *dir = g_path_get_dirname(path);
    g_mkdir_with_parents(dir, 0755);
    g_free(dir);

    GKeyFile *kf = g_key_file_new();

    g_key_file_set_string(kf, GROUP_GENERAL, "theme", settings->theme ? settings->theme : "mac_obsidian");
    g_key_file_set_string(kf, GROUP_GENERAL, "monitor", settings->monitor ? settings->monitor : "");
    g_key_file_set_boolean(kf, GROUP_GENERAL, "low_power_mode", settings->low_power_mode);
    g_key_file_set_boolean(kf, GROUP_GENERAL, "privacy_mode", settings->privacy_mode);

    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "collapsed_width", settings->collapsed_width);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "collapsed_height", settings->collapsed_height);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "expanded_width", settings->expanded_width);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "expanded_height", settings->expanded_height);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "top_margin", settings->top_margin);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "corner_radius_collapsed", settings->corner_radius_collapsed);
    g_key_file_set_integer(kf, GROUP_DIMENSIONS, "corner_radius_expanded", settings->corner_radius_expanded);

    g_key_file_set_integer(kf, GROUP_ANIMATION, "duration_ms", settings->animation_duration_ms);
    g_key_file_set_boolean(kf, GROUP_ANIMATION, "reduced_motion", settings->reduced_motion);

    g_key_file_set_boolean(kf, GROUP_INTEGRATION, "enable_media", settings->enable_media);
    g_key_file_set_boolean(kf, GROUP_INTEGRATION, "enable_sway", settings->enable_sway);
    g_key_file_set_boolean(kf, GROUP_INTEGRATION, "enable_notifications", settings->enable_notifications);
    g_key_file_set_boolean(kf, GROUP_INTEGRATION, "enable_system_status", settings->enable_system_status);
    g_key_file_set_integer(kf, GROUP_INTEGRATION, "workspace_timeout_ms", settings->workspace_timeout_ms);
    g_key_file_set_integer(kf, GROUP_INTEGRATION, "volume_timeout_ms", settings->volume_timeout_ms);
    g_key_file_set_integer(kf, GROUP_INTEGRATION, "notification_timeout_ms", settings->notification_timeout_ms);
    g_key_file_set_integer(kf, GROUP_INTEGRATION, "battery_low_threshold", settings->battery_low_threshold);

    GError *error = NULL;
    gboolean ok = g_key_file_save_to_file(kf, path, &error);
    if (!ok) {
        g_warning("Failed to write config to %s: %s", path, error ? error->message : "unknown");
        if (error) g_error_free(error);
    }

    g_key_file_free(kf);
    g_free(allocated_path);
    return ok;
}
