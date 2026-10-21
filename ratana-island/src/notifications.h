#ifndef RATANA_NOTIFICATIONS_H
#define RATANA_NOTIFICATIONS_H

#include <glib.h>

G_BEGIN_DECLS

typedef struct _NotificationInfo {
    guint32 id;
    char *app_name;
    char *summary;
    char *body;
    char *icon_name;
} NotificationInfo;

NotificationInfo *notification_info_new(guint32 id, const char *app, const char *summary, const char *body, const char *icon);
void notification_info_free(NotificationInfo *n);
NotificationInfo *notification_info_copy(const NotificationInfo *src);

typedef struct _NotificationManager NotificationManager;

typedef void (*NotificationReceivedCallback)(const NotificationInfo *notif, gpointer user_data);

NotificationManager *notification_manager_new(NotificationReceivedCallback cb, gpointer user_data, gboolean privacy_mode);
void notification_manager_free(NotificationManager *mgr);
void notification_manager_set_privacy_mode(NotificationManager *mgr, gboolean privacy_mode);

G_END_DECLS

#endif /* RATANA_NOTIFICATIONS_H */
