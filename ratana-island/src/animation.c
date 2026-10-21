#include "animation.h"
#include <math.h>

struct _Animation {
    GtkWidget *target_widget;
    guint tick_id;
    gint64 start_time_us;
    gint64 duration_us;

    int from_w, to_w;
    int from_h, to_h;
    int from_r, to_r;

    AnimationEasing easing;
    AnimationStepCallback step_cb;
    AnimationDoneCallback done_cb;
    gpointer user_data;

    gboolean is_running;
};

double animation_ease(AnimationEasing easing, double t) {
    if (t <= 0.0) return 0.0;
    if (t >= 1.0) return 1.0;

    switch (easing) {
        case ANIM_EASE_LINEAR:
            return t;
        case ANIM_EASE_OUT_CUBIC: {
            double inv = 1.0 - t;
            return 1.0 - (inv * inv * inv);
        }
        case ANIM_EASE_IN_OUT_CUBIC: {
            return t < 0.5 ? 4.0 * t * t * t : 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0;
        }
        case ANIM_EASE_OUT_EXPO: {
            return 1.0 - pow(2.0, -10.0 * t);
        }
        default:
            return t;
    }
}

Animation *animation_new(GtkWidget *target_widget) {
    Animation *anim = g_new0(Animation, 1);
    anim->target_widget = target_widget;
    return anim;
}

void animation_stop(Animation *anim) {
    if (!anim) return;
    if (anim->is_running && anim->tick_id > 0 && anim->target_widget && GTK_IS_WIDGET(anim->target_widget)) {
        gtk_widget_remove_tick_callback(anim->target_widget, anim->tick_id);
    }
    anim->tick_id = 0;
    anim->is_running = FALSE;
}

void animation_free(Animation *anim) {
    if (!anim) return;
    animation_stop(anim);
    g_free(anim);
}

static gboolean on_animation_tick(GtkWidget *widget, GdkFrameClock *frame_clock, gpointer user_data) {
    (void)widget;
    (void)frame_clock;
    Animation *anim = (Animation *)user_data;
    if (!anim || !anim->is_running) return G_SOURCE_REMOVE;

    gint64 now = g_get_monotonic_time();
    gint64 elapsed = now - anim->start_time_us;

    double progress = (anim->duration_us > 0) ? (double)elapsed / (double)anim->duration_us : 1.0;
    if (progress > 1.0) progress = 1.0;

    double eased = animation_ease(anim->easing, progress);

    int cur_w = (int)round(anim->from_w + (anim->to_w - anim->from_w) * eased);
    int cur_h = (int)round(anim->from_h + (anim->to_h - anim->from_h) * eased);
    int cur_r = (int)round(anim->from_r + (anim->to_r - anim->from_r) * eased);

    if (anim->step_cb) {
        anim->step_cb(eased, cur_w, cur_h, cur_r, anim->user_data);
    }

    if (progress >= 1.0) {
        anim->is_running = FALSE;
        anim->tick_id = 0;
        if (anim->done_cb) {
            anim->done_cb(anim->user_data);
        }
        return G_SOURCE_REMOVE;
    }

    return G_SOURCE_CONTINUE;
}

void animation_start(Animation *anim,
                     int from_w, int from_h, int from_r,
                     int to_w, int to_h, int to_r,
                     guint duration_ms,
                     AnimationEasing easing,
                     AnimationStepCallback step_cb,
                     AnimationDoneCallback done_cb,
                     gpointer user_data) {
    if (!anim) return;
    animation_stop(anim);

    if (duration_ms == 0) {
        if (step_cb) step_cb(1.0, to_w, to_h, to_r, user_data);
        if (done_cb) done_cb(user_data);
        return;
    }

    anim->from_w = from_w;
    anim->to_w = to_w;
    anim->from_h = from_h;
    anim->to_h = to_h;
    anim->from_r = from_r;
    anim->to_r = to_r;

    anim->start_time_us = g_get_monotonic_time();
    anim->duration_us = (gint64)duration_ms * 1000;
    anim->easing = easing;
    anim->step_cb = step_cb;
    anim->done_cb = done_cb;
    anim->user_data = user_data;
    anim->is_running = TRUE;

    if (anim->target_widget && GTK_IS_WIDGET(anim->target_widget)) {
        anim->tick_id = gtk_widget_add_tick_callback(anim->target_widget, on_animation_tick, anim, NULL);
    }
}

gboolean animation_is_running(const Animation *anim) {
    return anim ? anim->is_running : FALSE;
}
