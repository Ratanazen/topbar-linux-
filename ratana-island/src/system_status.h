#ifndef RATANA_SYSTEM_STATUS_H
#define RATANA_SYSTEM_STATUS_H

#include <glib.h>

G_BEGIN_DECLS

typedef struct _SystemStatusInfo {
    int volume_percent;
    gboolean is_muted;
    double battery_percent;
    gboolean battery_charging;
    gboolean battery_present;
} SystemStatusInfo;

typedef struct _SystemStatusManager SystemStatusManager;

typedef void (*SystemStatusCallback)(const SystemStatusInfo *status, gboolean is_volume_event, gpointer user_data);

SystemStatusManager *system_status_manager_new(SystemStatusCallback cb, gpointer user_data);
void system_status_manager_free(SystemStatusManager *mgr);

const SystemStatusInfo *system_status_manager_get_info(const SystemStatusManager *mgr);

G_END_DECLS

#endif /* RATANA_SYSTEM_STATUS_H */
