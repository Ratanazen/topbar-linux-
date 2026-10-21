#include <glib.h>
#include "state_manager.h"

static int callback_count = 0;
static IslandState last_old = STATE_IDLE;
static IslandState last_new = STATE_IDLE;

static void on_test_state_changed(IslandState old_state, IslandState new_state, gpointer user_data) {
    (void)user_data;
    callback_count++;
    last_old = old_state;
    last_new = new_state;
}

static void test_state_basic(void) {
    StateManager *sm = state_manager_new();
    g_assert_nonnull(sm);
    g_assert_cmpint(state_manager_get_current(sm), ==, STATE_IDLE);
    g_assert_false(state_is_expanded(STATE_IDLE));
    g_assert_false(state_is_expanded(STATE_COMPACT_MEDIA));
    g_assert_true(state_is_expanded(STATE_EXPANDED_MEDIA));
    g_assert_true(state_is_expanded(STATE_EXPANDED_WORKSPACE));
    g_assert_true(state_is_expanded(STATE_EXPANDED_VOLUME));
    g_assert_true(state_is_expanded(STATE_EXPANDED_NOTIFICATION));

    state_manager_set_callback(sm, on_test_state_changed, NULL);

    gboolean transitioned = state_manager_transition_to(sm, STATE_EXPANDED_MEDIA, 0);
    g_assert_true(transitioned);
    g_assert_cmpint(state_manager_get_current(sm), ==, STATE_EXPANDED_MEDIA);
    g_assert_cmpint(state_manager_get_previous(sm), ==, STATE_IDLE);
    g_assert_cmpint(callback_count, ==, 1);
    g_assert_cmpint(last_old, ==, STATE_IDLE);
    g_assert_cmpint(last_new, ==, STATE_EXPANDED_MEDIA);

    /* Transitioning to the same state should return FALSE */
    g_assert_false(state_manager_transition_to(sm, STATE_EXPANDED_MEDIA, 0));

    state_manager_restore_previous(sm);
    g_assert_cmpint(state_manager_get_current(sm), ==, STATE_IDLE);

    state_manager_free(sm);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/state/basic", test_state_basic);
    return g_test_run();
}
