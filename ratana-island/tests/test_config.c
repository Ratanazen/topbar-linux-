#include <glib.h>
#include <glib/gstdio.h>
#include "settings.h"

static void test_config_lifecycle(void) {
    RatanaSettings *s = ratana_settings_new_default();
    g_assert_nonnull(s);
    g_assert_cmpint(s->collapsed_width, ==, 190);
    g_assert_cmpint(s->collapsed_height, ==, 32);
    g_assert_cmpint(s->expanded_width, ==, 380);
    g_assert_cmpint(s->expanded_height, ==, 165);
    g_assert_cmpstr(s->theme, ==, "mac_obsidian");

    char *tmp_path = g_build_filename(g_get_tmp_dir(), "ratana_test_config.ini", NULL);
    g_unlink(tmp_path);

    /* Modify and save */
    s->collapsed_width = 220;
    s->expanded_width = 420;
    g_assert_true(ratana_settings_save(s, tmp_path));
    ratana_settings_free(s);

    /* Reload and verify */
    RatanaSettings *loaded = ratana_settings_load(tmp_path);
    g_assert_nonnull(loaded);
    g_assert_cmpint(loaded->collapsed_width, ==, 220);
    g_assert_cmpint(loaded->expanded_width, ==, 420);
    g_assert_cmpint(loaded->collapsed_height, ==, 32);

    ratana_settings_free(loaded);
    g_unlink(tmp_path);
    g_free(tmp_path);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/config/lifecycle", test_config_lifecycle);
    return g_test_run();
}
