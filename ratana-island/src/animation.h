#ifndef RATANA_ANIMATION_H
#define RATANA_ANIMATION_H

#include <glib.h>
#include <gtk/gtk.h>

G_BEGIN_DECLS

typedef enum {
    ANIM_EASE_LINEAR = 0,
    ANIM_EASE_OUT_CUBIC,
    ANIM_EASE_IN_OUT_CUBIC,
    ANIM_EASE_OUT_EXPO
} AnimationEasing;

typedef struct _Animation Animation;

typedef void (*AnimationStepCallback)(double progress,
                                      int current_width,
                                      int current_height,
                                      int current_radius,
                                      gpointer user_data);

typedef void (*AnimationDoneCallback)(gpointer user_data);

Animation *animation_new(GtkWidget *target_widget);
void animation_free(Animation *anim);

void animation_start(Animation *anim,
                     int from_w, int from_h, int from_r,
                     int to_w, int to_h, int to_r,
                     guint duration_ms,
                     AnimationEasing easing,
                     AnimationStepCallback step_cb,
                     AnimationDoneCallback done_cb,
                     gpointer user_data);

void animation_stop(Animation *anim);
gboolean animation_is_running(const Animation *anim);
double animation_ease(AnimationEasing easing, double t);

G_END_DECLS

#endif /* RATANA_ANIMATION_H */
