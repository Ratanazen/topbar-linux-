#include "sway_ipc.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <json-glib/json-glib.h>

#define I3_IPC_MAGIC "i3-ipc"
#define I3_IPC_MAGIC_LEN 6
#define I3_IPC_TYPE_SUBSCRIBE 2

struct _SwayClient {
    int socket_fd;
    GIOChannel *channel;
    guint watch_id;
    guint reconnect_timer;

    SwayWorkspaceCallback callback;
    gpointer user_data;
};

static gboolean sway_client_connect(SwayClient *client);

static gboolean on_socket_io(GIOChannel *source, GIOCondition condition, gpointer user_data) {
    SwayClient *client = (SwayClient *)user_data;
    if (condition & (G_IO_HUP | G_IO_ERR)) {
        g_warning("Sway IPC socket disconnected. Scheduling reconnect...");
        if (client->watch_id > 0) {
            client->watch_id = 0;
        }
        if (client->socket_fd >= 0) {
            close(client->socket_fd);
            client->socket_fd = -1;
        }
        if (client->channel) {
            g_io_channel_unref(client->channel);
            client->channel = NULL;
        }
        if (client->reconnect_timer == 0) {
            client->reconnect_timer = g_timeout_add_seconds(3, (GSourceFunc)sway_client_connect, client);
        }
        return G_SOURCE_REMOVE;
    }

    if (condition & G_IO_IN) {
        int fd = g_io_channel_unix_get_fd(source);
        uint8_t header[14];
        ssize_t n = recv(fd, header, 14, MSG_WAITALL);
        if (n == 14 && memcmp(header, I3_IPC_MAGIC, I3_IPC_MAGIC_LEN) == 0) {
            uint32_t len = *(uint32_t *)(header + 6);
            uint32_t type = *(uint32_t *)(header + 10);

            if (len > 0 && len < 1024 * 1024) {
                char *payload = g_malloc(len + 1);
                ssize_t pn = recv(fd, payload, len, MSG_WAITALL);
                if (pn == (ssize_t)len) {
                    payload[len] = '\0';
                    /* Check if it's an event (bit 31 set) */
                    if (type & (1U << 31)) {
                        JsonParser *parser = json_parser_new();
                        if (json_parser_load_from_data(parser, payload, len, NULL)) {
                            JsonNode *root = json_parser_get_root(parser);
                            if (JSON_NODE_HOLDS_OBJECT(root)) {
                                JsonObject *obj = json_node_get_object(root);
                                const char *change = json_object_get_string_member_with_default(obj, "change", "focus");
                                const char *ws_name = NULL;
                                if (json_object_has_member(obj, "current")) {
                                    JsonObject *cur = json_object_get_object_member(obj, "current");
                                    if (cur && json_object_has_member(cur, "name")) {
                                        ws_name = json_object_get_string_member(cur, "name");
                                    }
                                }
                                if (ws_name && client->callback) {
                                    client->callback(change, ws_name, client->user_data);
                                }
                            }
                        }
                        g_object_unref(parser);
                    }
                }
                g_free(payload);
            }
        }
    }

    return G_SOURCE_CONTINUE;
}

static gboolean sway_client_connect(SwayClient *client) {
    const char *sock_path = g_getenv("SWAYSOCK");
    if (!sock_path || !*sock_path) {
        sock_path = g_getenv("I3SOCK");
    }
    if (!sock_path || !*sock_path) {
        g_warning("Neither SWAYSOCK nor I3SOCK set in environment");
        return G_SOURCE_CONTINUE;
    }

    client->socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (client->socket_fd < 0) return G_SOURCE_CONTINUE;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, sock_path, sizeof(addr.sun_path) - 1);

    if (connect(client->socket_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(client->socket_fd);
        client->socket_fd = -1;
        return G_SOURCE_CONTINUE;
    }

    /* Subscribe to workspace events */
    const char *payload = "[\"workspace\"]";
    uint32_t payload_len = (uint32_t)strlen(payload);
    uint32_t msg_type = I3_IPC_TYPE_SUBSCRIBE;

    uint8_t packet[14 + 64];
    memcpy(packet, I3_IPC_MAGIC, I3_IPC_MAGIC_LEN);
    memcpy(packet + 6, &payload_len, 4);
    memcpy(packet + 10, &msg_type, 4);
    memcpy(packet + 14, payload, payload_len);

    if (send(client->socket_fd, packet, 14 + payload_len, 0) < 0) {
        close(client->socket_fd);
        client->socket_fd = -1;
        return G_SOURCE_CONTINUE;
    }

    client->channel = g_io_channel_unix_new(client->socket_fd);
    g_io_channel_set_encoding(client->channel, NULL, NULL);
    g_io_channel_set_buffered(client->channel, FALSE);
    client->watch_id = g_io_add_watch(client->channel, G_IO_IN | G_IO_HUP | G_IO_ERR, on_socket_io, client);

    client->reconnect_timer = 0;
    return G_SOURCE_REMOVE;
}

SwayClient *sway_client_new(SwayWorkspaceCallback cb, gpointer user_data) {
    SwayClient *client = g_new0(SwayClient, 1);
    client->callback = cb;
    client->user_data = user_data;
    client->socket_fd = -1;

    sway_client_connect(client);

    return client;
}

void sway_client_free(SwayClient *client) {
    if (!client) return;
    if (client->reconnect_timer > 0) {
        g_source_remove(client->reconnect_timer);
        client->reconnect_timer = 0;
    }
    if (client->watch_id > 0) {
        g_source_remove(client->watch_id);
        client->watch_id = 0;
    }
    if (client->channel) {
        g_io_channel_unref(client->channel);
        client->channel = NULL;
    }
    if (client->socket_fd >= 0) {
        close(client->socket_fd);
        client->socket_fd = -1;
    }
    g_free(client);
}
