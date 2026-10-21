#include "system_status.h"
#include <pulse/pulseaudio.h>
#include <pulse/glib-mainloop.h>
#include <libupower-glib/upower.h>

struct _SystemStatusManager {
    SystemStatusInfo info;
    SystemStatusCallback callback;
    gpointer user_data;

    /* PulseAudio */
    pa_glib_mainloop *pa_mainloop;
    pa_context *pa_ctx;

    /* UPower */
    UpClient *up_client;
    UpDevice *up_device;
    gulong up_sig_pct;
    gulong up_sig_state;
};

static void sink_info_callback(pa_context *c, const pa_sink_info *i, int eol, void *userdata) {
    (void)c;
    if (eol > 0 || !i) return;
    SystemStatusManager *mgr = (SystemStatusManager *)userdata;

    int vol = (int)(((double)pa_cvolume_avg(&i->volume) / (double)PA_VOLUME_NORM) * 100.0);
    if (vol > 100) vol = 100;
    if (vol < 0) vol = 0;

    gboolean changed = (mgr->info.volume_percent != vol || mgr->info.is_muted != (gboolean)i->mute);
    mgr->info.volume_percent = vol;
    mgr->info.is_muted = i->mute ? TRUE : FALSE;

    if (changed && mgr->callback) {
        mgr->callback(&mgr->info, TRUE, mgr->user_data);
    }
}

static void pa_subscribe_callback(pa_context *c, pa_subscription_event_type_t t, uint32_t idx, void *userdata) {
    (void)idx;
    if ((t & PA_SUBSCRIPTION_EVENT_FACILITY_MASK) == PA_SUBSCRIPTION_EVENT_SINK) {
        pa_operation *op = pa_context_get_sink_info_list(c, sink_info_callback, userdata);
        if (op) pa_operation_unref(op);
    }
}

static void pa_state_callback(pa_context *c, void *userdata) {
    SystemStatusManager *mgr = (SystemStatusManager *)userdata;
    pa_context_state_t state = pa_context_get_state(c);

    if (state == PA_CONTEXT_READY) {
        pa_context_set_subscribe_callback(c, pa_subscribe_callback, mgr);
        pa_operation *op1 = pa_context_subscribe(c, PA_SUBSCRIPTION_MASK_SINK, NULL, NULL);
        if (op1) pa_operation_unref(op1);

        pa_operation *op2 = pa_context_get_sink_info_list(c, sink_info_callback, mgr);
        if (op2) pa_operation_unref(op2);
    }
}

static void on_battery_notify(GObject *gobject, GParamSpec *pspec, gpointer user_data) {
    (void)pspec;
    SystemStatusManager *mgr = (SystemStatusManager *)user_data;
    UpDevice *dev = UP_DEVICE(gobject);

    double pct = 0.0;
    guint state = 0;
    gboolean is_present = FALSE;

    g_object_get(dev,
                 "percentage", &pct,
                 "state", &state,
                 "is-present", &is_present,
                 NULL);

    mgr->info.battery_percent = pct;
    mgr->info.battery_charging = (state == UP_DEVICE_STATE_CHARGING || state == UP_DEVICE_STATE_FULLY_CHARGED);
    mgr->info.battery_present = is_present;

    if (mgr->callback) {
        mgr->callback(&mgr->info, FALSE, mgr->user_data);
    }
}

SystemStatusManager *system_status_manager_new(SystemStatusCallback cb, gpointer user_data) {
    SystemStatusManager *mgr = g_new0(SystemStatusManager, 1);
    mgr->callback = cb;
    mgr->user_data = user_data;
    mgr->info.volume_percent = 50;
    mgr->info.is_muted = FALSE;
    mgr->info.battery_percent = 100.0;
    mgr->info.battery_charging = FALSE;
    mgr->info.battery_present = FALSE;

    /* Initialize PulseAudio with GLib mainloop */
    mgr->pa_mainloop = pa_glib_mainloop_new(NULL);
    if (mgr->pa_mainloop) {
        pa_mainloop_api *api = pa_glib_mainloop_get_api(mgr->pa_mainloop);
        mgr->pa_ctx = pa_context_new(api, "RatanaIsland");
        if (mgr->pa_ctx) {
            pa_context_set_state_callback(mgr->pa_ctx, pa_state_callback, mgr);
            pa_context_connect(mgr->pa_ctx, NULL, PA_CONTEXT_NOFLAGS, NULL);
        }
    }

    /* Initialize UPower */
    mgr->up_client = up_client_new();
    if (mgr->up_client) {
        mgr->up_device = up_client_get_display_device(mgr->up_client);
        if (mgr->up_device) {
            mgr->up_sig_pct = g_signal_connect(mgr->up_device, "notify::percentage", G_CALLBACK(on_battery_notify), mgr);
            mgr->up_sig_state = g_signal_connect(mgr->up_device, "notify::state", G_CALLBACK(on_battery_notify), mgr);
            on_battery_notify(G_OBJECT(mgr->up_device), NULL, mgr);
        }
    }

    return mgr;
}

void system_status_manager_free(SystemStatusManager *mgr) {
    if (!mgr) return;

    if (mgr->up_device) {
        if (mgr->up_sig_pct > 0) g_signal_handler_disconnect(mgr->up_device, mgr->up_sig_pct);
        if (mgr->up_sig_state > 0) g_signal_handler_disconnect(mgr->up_device, mgr->up_sig_state);
        g_object_unref(mgr->up_device);
    }
    if (mgr->up_client) {
        g_object_unref(mgr->up_client);
    }

    if (mgr->pa_ctx) {
        pa_context_disconnect(mgr->pa_ctx);
        pa_context_unref(mgr->pa_ctx);
    }
    if (mgr->pa_mainloop) {
        pa_glib_mainloop_free(mgr->pa_mainloop);
    }

    g_free(mgr);
}

const SystemStatusInfo *system_status_manager_get_info(const SystemStatusManager *mgr) {
    return mgr ? &mgr->info : NULL;
}
