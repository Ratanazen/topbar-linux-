#include "notifications.h"
#include <gio/gio.h>

struct _NotificationManager {
    GDBusConnection *bus;
    guint sub_id;
    gboolean privacy_mode;
    NotificationReceivedCallback callback;
    gpointer user_data;
};

NotificationInfo *notification_info_new(guint32 id, const char *app, const char *summary, const char *body, const char *icon) {
    NotificationInfo *n = g_new0(NotificationInfo, 1);
    n->id = id;
    n->app_name = g_strdup(app ? app : "Notification");
    n->summary = g_strdup(summary ? summary : "");
    n->body = g_strdup(body ? body : "");
    n->icon_name = g_strdup(icon ? icon : "dialog-information-symbolic");
    return n;
}

void notification_info_free(NotificationInfo *n) {
    if (!n) return;
    g_free(n->app_name);
    g_free(n->summary);
    g_free(n->body);
    g_free(n->icon_name);
    g_free(n);
}

NotificationInfo *notification_info_copy(const NotificationInfo *src) {
    if (!src) return NULL;
    return notification_info_new(src->id, src->app_name, src->summary, src->body, src->icon_name);
}

static void on_notify_signal(GDBusConnection *connection,
                             const gchar *sender_name,
                             const gchar *object_path,
                             const gchar *interface_name,
                             const gchar *signal_name,
                             GVariant *parameters,
                             gpointer user_data) {
    (void)connection;
    (void)sender_name;
    (void)object_path;
    (void)interface_name;
    NotificationManager *mgr = (NotificationManager *)user_data;

    if (g_strcmp0(signal_name, "NotificationClosed") == 0) {
        /* Handled or dismissed */
        return;
    }

    if (g_strcmp0(signal_name, "Notify") == 0 || g_strcmp0(signal_name, "Notification") == 0) {
        const char *app = "Notification";
        const char *summary = "";
        const char *body = "";
        const char *icon = "";
        guint32 id = 1;

        if (g_variant_is_of_type(parameters, G_VARIANT_TYPE("(susssasa{sv}i)"))) {
            g_variant_get(parameters, "(&su&s&s&sas@a{sv}i)", &app, &id, &icon, &summary, &body, NULL, NULL, NULL);
        }

        const char *display_summary = summary;
        const char *display_body = body;
        if (mgr->privacy_mode) {
            display_summary = "New Notification";
            display_body = "Notification hidden in privacy mode";
        }

        NotificationInfo *info = notification_info_new(id, app, display_summary, display_body, icon);
        if (mgr->callback) {
            mgr->callback(info, mgr->user_data);
        }
        notification_info_free(info);
    }
}

NotificationManager *notification_manager_new(NotificationReceivedCallback cb, gpointer user_data, gboolean privacy_mode) {
    NotificationManager *mgr = g_new0(NotificationManager, 1);
    mgr->callback = cb;
    mgr->user_data = user_data;
    mgr->privacy_mode = privacy_mode;

    GError *err = NULL;
    mgr->bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &err);
    if (mgr->bus) {
        mgr->sub_id = g_dbus_connection_signal_subscribe(
            mgr->bus,
            NULL,
            "org.freedesktop.Notifications",
            NULL,
            "/org/freedesktop/Notifications",
            NULL,
            G_DBUS_SIGNAL_FLAGS_NONE,
            on_notify_signal,
            mgr,
            NULL
        );
    } else {
        if (err) g_error_free(err);
    }

    return mgr;
}

void notification_manager_free(NotificationManager *mgr) {
    if (!mgr) return;
    if (mgr->bus) {
        if (mgr->sub_id > 0) g_dbus_connection_signal_unsubscribe(mgr->bus, mgr->sub_id);
        g_object_unref(mgr->bus);
    }
    g_free(mgr);
}

void notification_manager_set_privacy_mode(NotificationManager *mgr, gboolean privacy_mode) {
    if (!mgr) return;
    mgr->privacy_mode = privacy_mode;
}
