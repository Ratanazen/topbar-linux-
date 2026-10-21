#include <glib.h>
#include <assert.h>
#include <string.h>
#include "../src/media.h"

static void test_track_info_lifecycle(void) {
    TrackInfo *t = track_info_new();
    assert(t != NULL);
    assert(g_strcmp0(t->title, "No Media") == 0);
    assert(t->duration_sec == 0.0);
    assert(t->is_playing == FALSE);

    /* Modify fields */
    g_free(t->title);
    t->title = g_strdup("Dark Paradise");
    g_free(t->artist);
    t->artist = g_strdup("Lana Del Rey");
    t->duration_sec = 244.5;
    t->is_playing = TRUE;

    /* Copy */
    TrackInfo *copy = track_info_copy(t);
    assert(copy != NULL);
    assert(g_strcmp0(copy->title, "Dark Paradise") == 0);
    assert(g_strcmp0(copy->artist, "Lana Del Rey") == 0);
    assert(copy->duration_sec == 244.5);
    assert(copy->is_playing == TRUE);

    track_info_free(copy);
    track_info_free(t);
    g_print("[PASS] test_track_info_lifecycle\n");
}

static void test_metadata_cleaning_logic(void) {
    /* Test YouTube badge stripping regex / logic */
    const char *raw_title = "(904) Lana Del Rey - Dark Paradise - Lyrics - YouTube";
    char *title = g_strdup(raw_title);

    if (title[0] == '(') {
        char *close_paren = strchr(title, ')');
        if (close_paren) {
            char *rest = close_paren + 1;
            while (*rest == ' ') rest++;
            char *tmp = g_strdup(rest);
            g_free(title);
            title = tmp;
        }
    }
    assert(g_strcmp0(title, "Lana Del Rey - Dark Paradise - Lyrics - YouTube") == 0);

    /* Strip - YouTube */
    char *yt = g_strrstr(title, " - YouTube");
    if (yt) *yt = '\0';
    assert(g_strcmp0(title, "Lana Del Rey - Dark Paradise - Lyrics") == 0);

    /* Split Artist - Song */
    char *sep = strstr(title, " - ");
    assert(sep != NULL);
    *sep = '\0';
    char *artist = g_strdup(title);
    char *song = g_strdup(sep + 3);

    assert(g_strcmp0(artist, "Lana Del Rey") == 0);
    assert(g_str_has_prefix(song, "Dark Paradise") == TRUE);

    g_free(artist);
    g_free(song);
    g_free(title);
    g_print("[PASS] test_metadata_cleaning_logic\n");
}

int main(void) {
    test_track_info_lifecycle();
    test_metadata_cleaning_logic();
    g_print("All media tests PASSED!\n");
    return 0;
}
