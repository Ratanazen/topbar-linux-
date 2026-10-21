#ifndef RATANA_SWAY_IPC_H
#define RATANA_SWAY_IPC_H

#include <glib.h>

G_BEGIN_DECLS

typedef struct _SwayClient SwayClient;

typedef void (*SwayWorkspaceCallback)(const char *change, const char *ws_name, gpointer user_data);

SwayClient *sway_client_new(SwayWorkspaceCallback cb, gpointer user_data);
void sway_client_free(SwayClient *client);

G_END_DECLS

#endif /* RATANA_SWAY_IPC_H */
