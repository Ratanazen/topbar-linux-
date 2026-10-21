#include <glib.h>
#include <math.h>
#include "animation.h"

static void test_easing_bounds(void) {
    AnimationEasing easings[] = {
        ANIM_EASE_LINEAR,
        ANIM_EASE_OUT_CUBIC,
        ANIM_EASE_IN_OUT_CUBIC,
        ANIM_EASE_OUT_EXPO
    };

    for (int i = 0; i < 4; i++) {
        AnimationEasing e = easings[i];
        g_assert_cmpfloat_with_epsilon(animation_ease(e, 0.0), 0.0, 0.0001);
        g_assert_cmpfloat_with_epsilon(animation_ease(e, 1.0), 1.0, 0.0001);
        g_assert_cmpfloat_with_epsilon(animation_ease(e, -0.5), 0.0, 0.0001);
        g_assert_cmpfloat_with_epsilon(animation_ease(e, 1.5), 1.0, 0.0001);

        /* Monotonic check */
        double prev = 0.0;
        for (double t = 0.1; t <= 1.0; t += 0.1) {
            double cur = animation_ease(e, t);
            g_assert_true(cur >= prev);
            prev = cur;
        }
    }
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/animation/easing_bounds", test_easing_bounds);
    return g_test_run();
}
