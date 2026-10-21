#include <gtk/gtk.h>
#include <gio/gio.h>
#include "settings.h"
#include "state_manager.h"
#include "media.h"
#include "sway_ipc.h"
#include "notifications.h"
#include "system_status.h"
#include "island_window.h"
#include "settings_window.h"

typedef struct {
    RatanaSettings *settings;
    StateManager *state_mgr;
    MediaManager *media_mgr;
    SwayClient *sway_client;
    NotificationManager *notif_mgr;
    SystemStatusManager *status_mgr;
    RatanaIslandWindow *window;
} AppContext;

static void on_state_changed(IslandState old_state, IslandState new_state, gpointer user_data) {
    (void)old_state;
    AppContext *ctx = (AppContext *)user_data;
    if (ctx->window) {
        ratana_island_window_apply_state(ctx->window, new_state, TRUE);
    }
}

static void on_media_changed(const TrackInfo *track, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;
    if (ctx->window) {
        ratana_island_window_update_media(ctx->window, track);
        if (track->is_playing) {
            IslandState cur = state_manager_get_current(ctx->state_mgr);
            if (cur == STATE_IDLE) {
                state_manager_transition_to(ctx->state_mgr, STATE_COMPACT_MEDIA, 0);
            }
        }
    }
}

static void on_sway_workspace(const char *change, const char *ws_name, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;
    if (ctx->window && ctx->settings->enable_sway) {
        ratana_island_window_update_workspace(ctx->window, change, ws_name);
    }
}

static void on_notification_received(const NotificationInfo *notif, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;
    if (ctx->window && ctx->settings->enable_notifications) {
        ratana_island_window_update_notification(ctx->window, notif);
    }
}

static void on_system_status(const SystemStatusInfo *status, gboolean is_vol, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;
    if (ctx->window && ctx->settings->enable_system_status) {
        ratana_island_window_update_status(ctx->window, status, is_vol);
    }
}

static void load_css(void) {
    GtkCssProvider *provider = gtk_css_provider_new();

    /* Try user config first, then project relative or default */
    const char *cfg_home = g_get_user_config_dir();
    char *user_css = g_build_filename(cfg_home, "ratana-island", "style.css", NULL);
    char *rel_css = g_build_filename("config", "style.css", NULL);

    if (g_file_test(user_css, G_FILE_TEST_EXISTS)) {
        gtk_css_provider_load_from_path(provider, user_css);
    } else if (g_file_test(rel_css, G_FILE_TEST_EXISTS)) {
        gtk_css_provider_load_from_path(provider, rel_css);
    } else {
        /* Fallback embedded CSS string */
        const char *fallback =
            "* { font-family: 'SF Pro Display', 'Inter', sans-serif; }\n"
            "#island-root { background: transparent; }\n"
            "#island-capsule { background: #000000; border: 1px solid rgba(255,255,255,0.12); border-radius: 22px; }\n"
            "#island-capsule.expanded { border-radius: 36px; }\n";
        gtk_css_provider_load_from_string(provider, fallback);
    }

    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION
    );

    g_free(user_css);
    g_free(rel_css);
    g_object_unref(provider);
}

static void on_activate(GtkApplication *app, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;

    load_css();

    if (!ctx->window) {
        ctx->window = ratana_island_window_new(app, ctx->settings, ctx->state_mgr, ctx->media_mgr);

        /* Initial state update */
        if (ctx->media_mgr) {
            const TrackInfo *cur = media_manager_get_current_track(ctx->media_mgr);
            if (cur) ratana_island_window_update_media(ctx->window, cur);
        }

        ratana_island_window_apply_state(ctx->window, STATE_IDLE, FALSE);
    }

    gtk_window_present(GTK_WINDOW(ctx->window));
}

static int on_command_line(GApplication *app, GApplicationCommandLine *cmd, gpointer user_data) {
    AppContext *ctx = (AppContext *)user_data;
    int argc = 0;
    char **argv = g_application_command_line_get_arguments(cmd, &argc);

    for (int i = 1; i < argc; i++) {
        if (g_strcmp0(argv[i], "--toggle") == 0) {
            if (ctx->window) ratana_island_window_toggle_expanded(ctx->window);
            g_strfreev(argv);
            return 0;
        } else if (g_strcmp0(argv[i], "--expand") == 0) {
            state_manager_transition_to(ctx->state_mgr, STATE_EXPANDED_MEDIA, 0);
            g_strfreev(argv);
            return 0;
        } else if (g_strcmp0(argv[i], "--compact") == 0) {
            state_manager_transition_to(ctx->state_mgr, STATE_IDLE, 0);
            g_strfreev(argv);
            return 0;
        } else if (g_strcmp0(argv[i], "--settings") == 0) {
            ratana_settings_window_present(GTK_APPLICATION(app), ctx->settings, ctx->window);
            g_strfreev(argv);
            return 0;
        } else if (g_strcmp0(argv[i], "--quit") == 0) {
            g_application_quit(app);
            g_strfreev(argv);
            return 0;
        }
    }

    g_application_activate(app);
    g_strfreev(argv);
    return 0;
}

int main(int argc, char **argv) {
    AppContext ctx;
    memset(&ctx, 0, sizeof(AppContext));

    ctx.settings = ratana_settings_load(NULL);
    ctx.state_mgr = state_manager_new();

    state_manager_set_callback(ctx.state_mgr, on_state_changed, &ctx);

    if (ctx.settings->enable_media) {
        ctx.media_mgr = media_manager_new(on_media_changed, &ctx);
    }
    if (ctx.settings->enable_sway) {
        ctx.sway_client = sway_client_new(on_sway_workspace, &ctx);
    }
    if (ctx.settings->enable_notifications) {
        ctx.notif_mgr = notification_manager_new(on_notification_received, &ctx, ctx.settings->privacy_mode);
    }
    if (ctx.settings->enable_system_status) {
        ctx.status_mgr = system_status_manager_new(on_system_status, &ctx);
    }

    GtkApplication *app = gtk_application_new(
        "io.ratana.RatanaIsland",
        G_APPLICATION_HANDLES_COMMAND_LINE
    );

    g_signal_connect(app, "activate", G_CALLBACK(on_activate), &ctx);
    g_signal_connect(app, "command-line", G_CALLBACK(on_command_line), &ctx);

    int status = g_application_run(G_APPLICATION(app), argc, argv);

    /* Cleanup */
    if (ctx.status_mgr) system_status_manager_free(ctx.status_mgr);
    if (ctx.notif_mgr) notification_manager_free(ctx.notif_mgr);
    if (ctx.sway_client) sway_client_free(ctx.sway_client);
    if (ctx.media_mgr) media_manager_free(ctx.media_mgr);
    if (ctx.state_mgr) state_manager_free(ctx.state_mgr);
    if (ctx.settings) ratana_settings_free(ctx.settings);
    g_object_unref(app);

    return status;
}
