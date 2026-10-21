#include "state_manager.h"

struct _StateManager {
    IslandState current_state;
    IslandState previous_state;
    guint timeout_id;
    StateChangedCallback callback;
    gpointer user_data;
};

static const char *state_names[] = {
    [STATE_IDLE]                   = "IDLE",
    [STATE_COMPACT_MEDIA]          = "COMPACT_MEDIA",
    [STATE_COMPACT_NOTIFICATION]   = "COMPACT_NOTIFICATION",
    [STATE_EXPANDED_MEDIA]         = "EXPANDED_MEDIA",
    [STATE_EXPANDED_NOTIFICATION]  = "EXPANDED_NOTIFICATION",
    [STATE_EXPANDED_WORKSPACE]     = "EXPANDED_WORKSPACE",
    [STATE_EXPANDED_VOLUME]        = "EXPANDED_VOLUME",
    [STATE_EXPANDED_BATTERY]       = "EXPANDED_BATTERY",
};

const char *state_to_string(IslandState state) {
    if (state >= 0 && state < STATE_COUNT) {
        return state_names[state];
    }
    return "UNKNOWN";
}

gboolean state_is_expanded(IslandState state) {
    switch (state) {
        case STATE_EXPANDED_MEDIA:
        case STATE_EXPANDED_NOTIFICATION:
        case STATE_EXPANDED_WORKSPACE:
        case STATE_EXPANDED_VOLUME:
        case STATE_EXPANDED_BATTERY:
            return TRUE;
        default:
            return FALSE;
    }
}

StateManager *state_manager_new(void) {
    StateManager *sm = g_new0(StateManager, 1);
    sm->current_state = STATE_IDLE;
    sm->previous_state = STATE_IDLE;
    sm->timeout_id = 0;
    return sm;
}

void state_manager_free(StateManager *sm) {
    if (!sm) return;
    if (sm->timeout_id > 0) {
        g_source_remove(sm->timeout_id);
        sm->timeout_id = 0;
    }
    g_free(sm);
}

IslandState state_manager_get_current(const StateManager *sm) {
    return sm ? sm->current_state : STATE_IDLE;
}

IslandState state_manager_get_previous(const StateManager *sm) {
    return sm ? sm->previous_state : STATE_IDLE;
}

static gboolean on_state_timeout(gpointer user_data) {
    StateManager *sm = (StateManager *)user_data;
    sm->timeout_id = 0;
    state_manager_restore_previous(sm);
    return G_SOURCE_REMOVE;
}

gboolean state_manager_transition_to(StateManager *sm, IslandState new_state, guint timeout_ms) {
    if (!sm || sm->current_state == new_state) return FALSE;

    if (sm->timeout_id > 0) {
        g_source_remove(sm->timeout_id);
        sm->timeout_id = 0;
    }

    IslandState old_state = sm->current_state;
    if (old_state != STATE_EXPANDED_WORKSPACE &&
        old_state != STATE_EXPANDED_VOLUME &&
        old_state != STATE_EXPANDED_BATTERY) {
        sm->previous_state = old_state;
    }

    sm->current_state = new_state;

    if (sm->callback) {
        sm->callback(old_state, new_state, sm->user_data);
    }

    if (timeout_ms > 0) {
        sm->timeout_id = g_timeout_add(timeout_ms, on_state_timeout, sm);
    }

    return TRUE;
}

void state_manager_restore_previous(StateManager *sm) {
    if (!sm) return;
    IslandState target = sm->previous_state;
    state_manager_transition_to(sm, target, 0);
}

void state_manager_set_callback(StateManager *sm, StateChangedCallback cb, gpointer user_data) {
    if (!sm) return;
    sm->callback = cb;
    sm->user_data = user_data;
}
