#include "media.h"
#include <string.h>

struct _MediaManager {
    GDBusConnection *bus;
    guint props_sub_id;
    guint name_owner_sub_id;
    guint pos_poll_timer;

    char *active_player;
    TrackInfo *current_track;

    MediaChangedCallback callback;
    gpointer user_data;
};

TrackInfo *track_info_new(void) {
    TrackInfo *t = g_new0(TrackInfo, 1);
    t->title = g_strdup("No Media");
    t->artist = g_strdup("");
    t->album = g_strdup("");
    t->art_url = g_strdup("");
    t->local_art_path = g_strdup("");
    t->player_name = g_strdup("");
    t->duration_sec = 0.0;
    t->position_sec = 0.0;
    t->is_playing = FALSE;
    t->can_play = TRUE;
    t->can_pause = TRUE;
    t->can_go_next = TRUE;
    t->can_go_previous = TRUE;
    return t;
}

void track_info_free(TrackInfo *info) {
    if (!info) return;
    g_free(info->title);
    g_free(info->artist);
    g_free(info->album);
    g_free(info->art_url);
    g_free(info->local_art_path);
    g_free(info->player_name);
    g_free(info);
}

TrackInfo *track_info_copy(const TrackInfo *src) {
    if (!src) return NULL;
    TrackInfo *t = g_new0(TrackInfo, 1);
    t->title = g_strdup(src->title);
    t->artist = g_strdup(src->artist);
    t->album = g_strdup(src->album);
    t->art_url = g_strdup(src->art_url);
    t->local_art_path = g_strdup(src->local_art_path);
    t->player_name = g_strdup(src->player_name);
    t->duration_sec = src->duration_sec;
    t->position_sec = src->position_sec;
    t->is_playing = src->is_playing;
    t->can_play = src->can_play;
    t->can_pause = src->can_pause;
    t->can_go_next = src->can_go_next;
    t->can_go_previous = src->can_go_previous;
    return t;
}

static void media_manager_query_player(MediaManager *mgr, const char *player_name);

typedef struct {
    MediaManager *mgr;
    char *expected_url;
    char *cache_path;
} ArtFetchData;

static void on_curl_done(GObject *source_object, GAsyncResult *res, gpointer user_data) {
    GSubprocess *proc = G_SUBPROCESS(source_object);
    ArtFetchData *data = (ArtFetchData *)user_data;
    GError *err = NULL;

    if (g_subprocess_wait_finish(proc, res, &err)) {
        if (g_subprocess_get_successful(proc)) {
            if (data->mgr && data->mgr->current_track &&
                g_strcmp0(data->mgr->current_track->art_url, data->expected_url) == 0) {
                g_free(data->mgr->current_track->local_art_path);
                data->mgr->current_track->local_art_path = g_strdup(data->cache_path);
                if (data->mgr->callback) {
                    data->mgr->callback(data->mgr->current_track, data->mgr->user_data);
                }
            }
        }
    }
    if (err) g_error_free(err);
    g_free(data->expected_url);
    g_free(data->cache_path);
    g_free(data);
}

static void resolve_art_path(MediaManager *mgr, const char *art_url) {
    if (!art_url || !*art_url) {
        g_free(mgr->current_track->local_art_path);
        mgr->current_track->local_art_path = g_strdup("");
        return;
    }

    if (g_str_has_prefix(art_url, "file://")) {
        g_free(mgr->current_track->local_art_path);
        mgr->current_track->local_art_path = g_filename_from_uri(art_url, NULL, NULL);
        return;
    }

    if (g_str_has_prefix(art_url, "http://") || g_str_has_prefix(art_url, "https://")) {
        const char *cache_root = g_get_user_cache_dir();
        char *art_dir = g_build_filename(cache_root, "ratana-island", "art", NULL);
        g_mkdir_with_parents(art_dir, 0755);

        char *hash = g_compute_checksum_for_string(G_CHECKSUM_SHA256, art_url, -1);
        char *cache_file = g_strdup_printf("%s.jpg", hash);
        char *full_path = g_build_filename(art_dir, cache_file, NULL);
        g_free(hash);
        g_free(cache_file);
        g_free(art_dir);

        if (g_file_test(full_path, G_FILE_TEST_EXISTS)) {
            g_free(mgr->current_track->local_art_path);
            mgr->current_track->local_art_path = full_path;
            return;
        }

        /* Asynchronously download via curl */
        ArtFetchData *data = g_new0(ArtFetchData, 1);
        data->mgr = mgr;
        data->expected_url = g_strdup(art_url);
        data->cache_path = full_path;

        GError *sub_err = NULL;
        GSubprocess *sub = g_subprocess_new(
            G_SUBPROCESS_FLAGS_NONE,
            &sub_err,
            "curl", "-sL", "-o", data->cache_path, "--max-time", "5", art_url, NULL
        );
        if (sub) {
            g_subprocess_wait_async(sub, NULL, on_curl_done, data);
            g_object_unref(sub);
        } else {
            if (sub_err) g_error_free(sub_err);
            g_free(data->expected_url);
            g_free(data->cache_path);
            g_free(data);
        }
    }
}

static void clean_media_metadata(MediaManager *mgr, const char *raw_url) {
    if (!mgr || !mgr->current_track) return;
    TrackInfo *t = mgr->current_track;

    char *title = t->title ? g_strdup(t->title) : g_strdup("");
    char *artist = t->artist ? g_strdup(t->artist) : g_strdup("");

    /* 1. Strip leading notification badge: e.g. "(904) " */
    if (title[0] == '(') {
        char *close_paren = strchr(title, ')');
        if (close_paren) {
            gboolean all_digits = TRUE;
            for (char *p = title + 1; p < close_paren; p++) {
                if (!g_ascii_isdigit(*p)) { all_digits = FALSE; break; }
            }
            if (all_digits && (close_paren > title + 1)) {
                char *rest = close_paren + 1;
                while (*rest == ' ') rest++;
                char *new_title = g_strdup(rest);
                g_free(title);
                title = new_title;
            }
        }
    }

    /* 2. Strip trailing " - YouTube" or " - YouTube Music" */
    char *yt_suffix = g_strrstr(title, " - YouTube");
    if (yt_suffix && (g_strcmp0(yt_suffix, " - YouTube") == 0 || g_strcmp0(yt_suffix, " - YouTube Music") == 0)) {
        *yt_suffix = '\0';
    }

    /* 3. If artist is empty or Unknown Artist or channel, try "Artist - Song" */
    if (!artist || !*artist || g_strcmp0(artist, "Unknown Artist") == 0 || g_strrstr(title, " - ") != NULL) {
        char *sep = strstr(title, " - ");
        if (sep) {
            *sep = '\0';
            char *art_cand = g_strstrip(g_strdup(title));
            char *song_cand = g_strstrip(g_strdup(sep + 3));

            /* Remove trailing (Lyrics), [Official Video], etc. from song_cand */
            char *suffixes[] = {
                " - Lyrics", " (Lyrics)", " [Lyrics]",
                " (Official Music Video)", " (Official Video)", " [Official Video]",
                " (Official Audio)", " [Official Audio]", " (Audio)", " [Audio]",
                NULL
            };
            for (int i = 0; suffixes[i]; i++) {
                char *sub = g_strrstr(song_cand, suffixes[i]);
                if (sub) {
                    *sub = '\0';
                    break;
                }
            }

            g_free(artist);
            artist = art_cand;

            g_free(title);
            title = song_cand;
        }
    }

    /* 4. If art_url is missing or empty, check raw_url for YouTube */
    if ((!t->art_url || !*t->art_url) && raw_url && *raw_url) {
        char *vid = NULL;
        char *v_param = strstr(raw_url, "v=");
        if (v_param) {
            vid = g_strndup(v_param + 2, 11);
        } else {
            char *be = strstr(raw_url, "youtu.be/");
            if (be) vid = g_strndup(be + 9, 11);
        }
        if (vid) {
            g_free(t->art_url);
            t->art_url = g_strdup_printf("https://img.youtube.com/vi/%s/hqdefault.jpg", vid);
            g_free(vid);
            resolve_art_path(mgr, t->art_url);
        }
    }

    g_free(t->title);
    t->title = title;
    g_free(t->artist);
    t->artist = artist;
}

static void on_properties_changed(GDBusConnection *connection,
                                  const gchar *sender_name,
                                  const gchar *object_path,
                                  const gchar *interface_name,
                                  const gchar *signal_name,
                                  GVariant *parameters,
                                  gpointer user_data) {
    (void)connection;
    (void)object_path;
    (void)interface_name;
    (void)signal_name;
    MediaManager *mgr = (MediaManager *)user_data;

    const gchar *iface = NULL;
    GVariantIter *changed_props = NULL;
    g_variant_get(parameters, "(&sa{sv}as)", &iface, &changed_props, NULL);

    if (g_strcmp0(iface, "org.mpris.MediaPlayer2.Player") == 0) {
        const gchar *key;
        GVariant *value;
        gboolean changed = FALSE;
        char *raw_url = NULL;

        while (g_variant_iter_loop(changed_props, "{&sv}", &key, &value)) {
            if (g_strcmp0(key, "PlaybackStatus") == 0) {
                const char *status = g_variant_get_string(value, NULL);
                mgr->current_track->is_playing = (g_strcmp0(status, "Playing") == 0);
                changed = TRUE;
            } else if (g_strcmp0(key, "Metadata") == 0) {
                GVariantIter *meta_iter;
                g_variant_get(value, "a{sv}", &meta_iter);
                const char *mkey;
                GVariant *mval;

                while (g_variant_iter_loop(meta_iter, "{&sv}", &mkey, &mval)) {
                    if (g_strcmp0(mkey, "xesam:title") == 0) {
                        g_free(mgr->current_track->title);
                        mgr->current_track->title = g_strdup(g_variant_get_string(mval, NULL));
                        changed = TRUE;
                    } else if (g_strcmp0(mkey, "xesam:artist") == 0) {
                        g_free(mgr->current_track->artist);
                        if (g_variant_is_of_type(mval, G_VARIANT_TYPE_STRING_ARRAY)) {
                            char **artists = g_variant_dup_strv(mval, NULL);
                            mgr->current_track->artist = g_strjoinv(", ", artists);
                            g_strfreev(artists);
                        } else if (g_variant_is_of_type(mval, G_VARIANT_TYPE_STRING)) {
                            mgr->current_track->artist = g_strdup(g_variant_get_string(mval, NULL));
                        }
                        changed = TRUE;
                    } else if (g_strcmp0(mkey, "xesam:url") == 0) {
                        g_free(raw_url);
                        raw_url = g_strdup(g_variant_get_string(mval, NULL));
                    } else if (g_strcmp0(mkey, "mpris:artUrl") == 0) {
                        g_free(mgr->current_track->art_url);
                        mgr->current_track->art_url = g_strdup(g_variant_get_string(mval, NULL));
                        resolve_art_path(mgr, mgr->current_track->art_url);
                        changed = TRUE;
                    } else if (g_strcmp0(mkey, "mpris:length") == 0) {
                        gint64 len_us = 0;
                        if (g_variant_is_of_type(mval, G_VARIANT_TYPE_INT64)) len_us = g_variant_get_int64(mval);
                        else if (g_variant_is_of_type(mval, G_VARIANT_TYPE_UINT64)) len_us = (gint64)g_variant_get_uint64(mval);
                        mgr->current_track->duration_sec = (double)len_us / 1000000.0;
                        changed = TRUE;
                    }
                }
                g_variant_iter_free(meta_iter);
            }
        }

        if (changed) {
            clean_media_metadata(mgr, raw_url);
            if (mgr->callback) {
                mgr->callback(mgr->current_track, mgr->user_data);
            }
        }
        g_free(raw_url);
    }

    g_variant_iter_free(changed_props);
}

static void on_name_owner_changed(GDBusConnection *connection,
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
    (void)signal_name;
    MediaManager *mgr = (MediaManager *)user_data;

    const gchar *name = NULL;
    const gchar *old_owner = NULL;
    const gchar *new_owner = NULL;
    g_variant_get(parameters, "(&s&s&s)", &name, &old_owner, &new_owner);

    if (g_str_has_prefix(name, "org.mpris.MediaPlayer2.")) {
        if (new_owner && *new_owner) {
            /* Player appeared or took ownership */
            if (!mgr->active_player) {
                mgr->active_player = g_strdup(name);
                media_manager_query_player(mgr, name);
            }
        } else if (old_owner && *old_owner) {
            /* Player disappeared */
            if (mgr->active_player && g_strcmp0(mgr->active_player, name) == 0) {
                g_free(mgr->active_player);
                mgr->active_player = NULL;
                mgr->current_track->is_playing = FALSE;
                if (mgr->callback) {
                    mgr->callback(mgr->current_track, mgr->user_data);
                }
            }
        }
    }
}

static void media_manager_query_player(MediaManager *mgr, const char *player_name) {
    if (!mgr->bus || !player_name) return;

    g_free(mgr->current_track->player_name);
    mgr->current_track->player_name = g_strdup(player_name + 23); /* strip "org.mpris.MediaPlayer2." */

    GError *err = NULL;
    char *raw_url = NULL;
    GVariant *status_var = g_dbus_connection_call_sync(
        mgr->bus,
        player_name,
        "/org/mpris/MediaPlayer2",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "PlaybackStatus"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE,
        500,
        NULL,
        &err
    );

    if (status_var) {
        GVariant *v = NULL;
        g_variant_get(status_var, "(v)", &v);
        const char *status = g_variant_get_string(v, NULL);
        mgr->current_track->is_playing = (g_strcmp0(status, "Playing") == 0);
        g_variant_unref(v);
        g_variant_unref(status_var);
    }
    if (err) g_error_free(err);

    err = NULL;
    GVariant *meta_var = g_dbus_connection_call_sync(
        mgr->bus,
        player_name,
        "/org/mpris/MediaPlayer2",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE,
        500,
        NULL,
        &err
    );

    if (meta_var) {
        GVariant *inner = NULL;
        g_variant_get(meta_var, "(v)", &inner);
        GVariantIter *meta_iter = NULL;
        g_variant_get(inner, "a{sv}", &meta_iter);
        const char *mkey;
        GVariant *mval;

        while (g_variant_iter_loop(meta_iter, "{&sv}", &mkey, &mval)) {
            if (g_strcmp0(mkey, "xesam:title") == 0) {
                g_free(mgr->current_track->title);
                mgr->current_track->title = g_strdup(g_variant_get_string(mval, NULL));
            } else if (g_strcmp0(mkey, "xesam:artist") == 0) {
                g_free(mgr->current_track->artist);
                if (g_variant_is_of_type(mval, G_VARIANT_TYPE_STRING_ARRAY)) {
                    char **artists = g_variant_dup_strv(mval, NULL);
                    mgr->current_track->artist = g_strjoinv(", ", artists);
                    g_strfreev(artists);
                } else if (g_variant_is_of_type(mval, G_VARIANT_TYPE_STRING)) {
                    mgr->current_track->artist = g_strdup(g_variant_get_string(mval, NULL));
                }
            } else if (g_strcmp0(mkey, "xesam:url") == 0) {
                g_free(raw_url);
                raw_url = g_strdup(g_variant_get_string(mval, NULL));
            } else if (g_strcmp0(mkey, "mpris:artUrl") == 0) {
                g_free(mgr->current_track->art_url);
                mgr->current_track->art_url = g_strdup(g_variant_get_string(mval, NULL));
                resolve_art_path(mgr, mgr->current_track->art_url);
            } else if (g_strcmp0(mkey, "mpris:length") == 0) {
                gint64 len_us = 0;
                if (g_variant_is_of_type(mval, G_VARIANT_TYPE_INT64)) len_us = g_variant_get_int64(mval);
                else if (g_variant_is_of_type(mval, G_VARIANT_TYPE_UINT64)) len_us = (gint64)g_variant_get_uint64(mval);
                mgr->current_track->duration_sec = (double)len_us / 1000000.0;
            }
        }
        g_variant_iter_free(meta_iter);
        g_variant_unref(inner);
        g_variant_unref(meta_var);
    }
    if (err) g_error_free(err);

    clean_media_metadata(mgr, raw_url);
    g_free(raw_url);

    if (mgr->callback) {
        mgr->callback(mgr->current_track, mgr->user_data);
    }
}

static gboolean on_position_poll(gpointer user_data) {
    MediaManager *mgr = (MediaManager *)user_data;
    if (!mgr || !mgr->bus || !mgr->active_player || !mgr->current_track->is_playing) return G_SOURCE_CONTINUE;

    GError *err = NULL;
    GVariant *pos_var = g_dbus_connection_call_sync(
        mgr->bus,
        mgr->active_player,
        "/org/mpris/MediaPlayer2",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "Position"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE,
        300,
        NULL,
        &err
    );

    if (pos_var) {
        GVariant *v = NULL;
        g_variant_get(pos_var, "(v)", &v);
        gint64 pos_us = g_variant_get_int64(v);
        mgr->current_track->position_sec = (double)pos_us / 1000000.0;
        g_variant_unref(v);
        g_variant_unref(pos_var);
        if (mgr->callback) {
            mgr->callback(mgr->current_track, mgr->user_data);
        }
    }
    if (err) g_error_free(err);

    return G_SOURCE_CONTINUE;
}

static GList *get_all_mpris_players(MediaManager *mgr) {
    if (!mgr || !mgr->bus) return NULL;
    GError *err = NULL;
    GVariant *res = g_dbus_connection_call_sync(
        mgr->bus,
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "ListNames",
        NULL,
        G_VARIANT_TYPE("(as)"),
        G_DBUS_CALL_FLAGS_NONE,
        500,
        NULL,
        &err
    );
    if (!res) {
        if (err) g_error_free(err);
        return NULL;
    }

    GList *list = NULL;
    GVariantIter *iter = NULL;
    g_variant_get(res, "(as)", &iter);
    char *name = NULL;
    while (g_variant_iter_loop(iter, "s", &name)) {
        if (g_str_has_prefix(name, "org.mpris.MediaPlayer2.")) {
            list = g_list_append(list, g_strdup(name));
        }
    }
    g_variant_iter_free(iter);
    g_variant_unref(res);
    return list;
}

static char *pick_best_player(MediaManager *mgr) {
    GList *players = get_all_mpris_players(mgr);
    if (!players) return NULL;

    char *best = NULL;
    int best_score = -1;

    for (GList *l = players; l != NULL; l = l->next) {
        const char *pname = (const char *)l->data;
        int score = 0;

        if (strstr(pname, "plasma-browser-integration")) score += 20;
        else if (strstr(pname, "spotify")) score += 15;
        else if (strstr(pname, "mpv") || strstr(pname, "vlc")) score += 10;

        GError *err = NULL;
        GVariant *v = g_dbus_connection_call_sync(
            mgr->bus, pname, "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties", "Get",
            g_variant_new("(ss)", "org.mpris.MediaPlayer2.Player", "PlaybackStatus"),
            G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, 300, NULL, &err
        );
        if (v) {
            GVariant *inner = NULL;
            g_variant_get(v, "(v)", &inner);
            const char *st = g_variant_get_string(inner, NULL);
            if (g_strcmp0(st, "Playing") == 0) score += 50;
            else if (g_strcmp0(st, "Paused") == 0) score += 5;
            g_variant_unref(inner);
            g_variant_unref(v);
        }
        if (err) g_error_free(err);

        if (score > best_score) {
            best_score = score;
            g_free(best);
            best = g_strdup(pname);
        }
    }

    g_list_free_full(players, g_free);
    return best;
}

MediaManager *media_manager_new(MediaChangedCallback cb, gpointer user_data) {
    MediaManager *mgr = g_new0(MediaManager, 1);
    mgr->callback = cb;
    mgr->user_data = user_data;
    mgr->current_track = track_info_new();

    GError *err = NULL;
    mgr->bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &err);
    if (!mgr->bus) {
        g_warning("Could not connect to D-Bus session bus: %s", err ? err->message : "unknown");
        if (err) g_error_free(err);
        return mgr;
    }

    mgr->props_sub_id = g_dbus_connection_signal_subscribe(
        mgr->bus,
        NULL,
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        "/org/mpris/MediaPlayer2",
        "org.mpris.MediaPlayer2.Player",
        G_DBUS_SIGNAL_FLAGS_NONE,
        on_properties_changed,
        mgr,
        NULL
    );

    mgr->name_owner_sub_id = g_dbus_connection_signal_subscribe(
        mgr->bus,
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "NameOwnerChanged",
        "/org/freedesktop/DBus",
        NULL,
        G_DBUS_SIGNAL_FLAGS_NONE,
        on_name_owner_changed,
        mgr,
        NULL
    );

    /* Discover best active player */
    mgr->active_player = pick_best_player(mgr);
    if (mgr->active_player) {
        media_manager_query_player(mgr, mgr->active_player);
    }

    mgr->pos_poll_timer = g_timeout_add(1000, on_position_poll, mgr);

    return mgr;
}

void media_manager_free(MediaManager *mgr) {
    if (!mgr) return;
    if (mgr->pos_poll_timer > 0) {
        g_source_remove(mgr->pos_poll_timer);
        mgr->pos_poll_timer = 0;
    }
    if (mgr->bus) {
        if (mgr->props_sub_id > 0) g_dbus_connection_signal_unsubscribe(mgr->bus, mgr->props_sub_id);
        if (mgr->name_owner_sub_id > 0) g_dbus_connection_signal_unsubscribe(mgr->bus, mgr->name_owner_sub_id);
        g_object_unref(mgr->bus);
    }
    g_free(mgr->active_player);
    track_info_free(mgr->current_track);
    g_free(mgr);
}

void media_manager_play_pause(MediaManager *mgr) {
    if (!mgr || !mgr->bus || !mgr->active_player) return;
    g_dbus_connection_call(mgr->bus, mgr->active_player, "/org/mpris/MediaPlayer2",
                           "org.mpris.MediaPlayer2.Player", "PlayPause", NULL, NULL,
                           G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
}

void media_manager_next(MediaManager *mgr) {
    if (!mgr || !mgr->bus || !mgr->active_player) return;
    g_dbus_connection_call(mgr->bus, mgr->active_player, "/org/mpris/MediaPlayer2",
                           "org.mpris.MediaPlayer2.Player", "Next", NULL, NULL,
                           G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
}

void media_manager_previous(MediaManager *mgr) {
    if (!mgr || !mgr->bus || !mgr->active_player) return;
    g_dbus_connection_call(mgr->bus, mgr->active_player, "/org/mpris/MediaPlayer2",
                           "org.mpris.MediaPlayer2.Player", "Previous", NULL, NULL,
                           G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
}

void media_manager_seek(MediaManager *mgr, double position_sec) {
    if (!mgr || !mgr->bus || !mgr->active_player) return;
    gint64 pos_us = (gint64)(position_sec * 1000000.0);
    g_dbus_connection_call(mgr->bus, mgr->active_player, "/org/mpris/MediaPlayer2",
                           "org.mpris.MediaPlayer2.Player", "SetPosition",
                           g_variant_new("(ox)", "/org/mpris/MediaPlayer2/TrackList/NoTrack", pos_us),
                           NULL, G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL, NULL);
}

const TrackInfo *media_manager_get_current_track(const MediaManager *mgr) {
    return mgr ? mgr->current_track : NULL;
}

void media_manager_select_player(MediaManager *mgr, const char *player_name) {
    if (!mgr || !player_name) return;
    g_free(mgr->active_player);
    mgr->active_player = g_strdup(player_name);
    media_manager_query_player(mgr, player_name);
}

void media_manager_cycle_player(MediaManager *mgr) {
    if (!mgr) return;
    GList *players = get_all_mpris_players(mgr);
    if (!players) return;

    guint count = g_list_length(players);
    if (count <= 1) {
        g_list_free_full(players, g_free);
        return;
    }

    int cur_idx = -1;
    int idx = 0;
    for (GList *l = players; l != NULL; l = l->next, idx++) {
        if (g_strcmp0(mgr->active_player, (const char *)l->data) == 0) {
            cur_idx = idx;
            break;
        }
    }

    int next_idx = (cur_idx + 1) % count;
    char *next_player = (char *)g_list_nth_data(players, next_idx);
    if (next_player) {
        media_manager_select_player(mgr, next_player);
    }
    g_list_free_full(players, g_free);
}
