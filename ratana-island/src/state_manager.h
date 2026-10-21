#ifndef RATANA_STATE_MANAGER_H
#define RATANA_STATE_MANAGER_H

#include <glib.h>

G_BEGIN_DECLS

typedef enum {
    STATE_IDLE = 0,
    STATE_COMPACT_MEDIA,
    STATE_COMPACT_NOTIFICATION,
    STATE_EXPANDED_MEDIA,
    STATE_EXPANDED_NOTIFICATION,
    STATE_EXPANDED_WORKSPACE,
    STATE_EXPANDED_VOLUME,
    STATE_EXPANDED_BATTERY,
    STATE_COUNT
} IslandState;

typedef struct _StateManager StateManager;

typedef void (*StateChangedCallback)(IslandState old_state, IslandState new_state, gpointer user_data);

StateManager *state_manager_new(void);
void state_manager_free(StateManager *sm);

IslandState state_manager_get_current(const StateManager *sm);
IslandState state_manager_get_previous(const StateManager *sm);
gboolean state_is_expanded(IslandState state);
const char *state_to_string(IslandState state);

gboolean state_manager_transition_to(StateManager *sm, IslandState new_state, guint timeout_ms);
void state_manager_restore_previous(StateManager *sm);

void state_manager_set_callback(StateManager *sm, StateChangedCallback cb, gpointer user_data);

G_END_DECLS

#endif /* RATANA_STATE_MANAGER_H */
