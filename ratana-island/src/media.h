#ifndef RATANA_MEDIA_H
#define RATANA_MEDIA_H

#include <glib.h>
#include <gio/gio.h>

G_BEGIN_DECLS

typedef struct _TrackInfo {
    char *title;
    char *artist;
    char *album;
    char *art_url;
    char *local_art_path;
    char *player_name;
    double duration_sec;
    double position_sec;
    gboolean is_playing;
    gboolean can_play;
    gboolean can_pause;
    gboolean can_go_next;
    gboolean can_go_previous;
} TrackInfo;

TrackInfo *track_info_new(void);
void track_info_free(TrackInfo *info);
TrackInfo *track_info_copy(const TrackInfo *src);

typedef struct _MediaManager MediaManager;

typedef void (*MediaChangedCallback)(const TrackInfo *track, gpointer user_data);

MediaManager *media_manager_new(MediaChangedCallback cb, gpointer user_data);
void media_manager_free(MediaManager *mgr);

void media_manager_play_pause(MediaManager *mgr);
void media_manager_next(MediaManager *mgr);
void media_manager_previous(MediaManager *mgr);
void media_manager_seek(MediaManager *mgr, double position_sec);

const TrackInfo *media_manager_get_current_track(const MediaManager *mgr);
void media_manager_cycle_player(MediaManager *mgr);
void media_manager_select_player(MediaManager *mgr, const char *player_name);

G_END_DECLS

#endif /* RATANA_MEDIA_H */
