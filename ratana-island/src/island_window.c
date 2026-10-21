#include "island_window.h"
#include "animation.h"
#include "settings_window.h"
#include <gtk4-layer-shell.h>
#include <math.h>

struct _RatanaIslandWindow {
    GtkApplicationWindow parent_instance;

    RatanaSettings *settings;
    StateManager *state_mgr;
    MediaManager *media_mgr;
    Animation *anim;

    /* Widgets */
    GtkWidget *root_box;
    GtkWidget *capsule_box;
    GtkWidget *stack;

    /* Compact widgets */
    GtkWidget *compact_box;
    GtkWidget *compact_art;
    GtkWidget *compact_title;
    GtkWidget *compact_waveform;

    /* Expanded Media widgets */
    GtkWidget *expanded_media_box;
    GtkWidget *art_stack;
    GtkWidget *media_art_picture;
    GtkWidget *media_art_fallback;
    GtkWidget *media_title;
    GtkWidget *media_artist;
    GtkWidget *media_waveform;
    GtkWidget *elapsed_label;
    GtkWidget *total_label;
    GtkWidget *progress_scale;
    GtkWidget *prev_btn;
    GtkWidget *play_btn;
    GtkWidget *next_btn;
    GtkWidget *shuffle_btn;
    GtkWidget *output_btn;

    /* Expanded Workspace widgets */
    GtkWidget *expanded_ws_box;
    GtkWidget *ws_icon;
    GtkWidget *ws_label;

    /* Expanded Volume widgets */
    GtkWidget *expanded_vol_box;
    GtkWidget *vol_icon;
    GtkWidget *vol_label;
    GtkWidget *vol_scale;

    /* Expanded Notification widgets */
    GtkWidget *expanded_notif_box;
    GtkWidget *notif_icon;
    GtkWidget *notif_app;
    GtkWidget *notif_summary;
    GtkWidget *notif_body;

    /* Waveform Animation */
    guint waveform_timer;
    double waveform_phase;
    gboolean is_playing;

    int current_width;
    int current_height;
    int current_radius;

    GtkCssProvider *dynamic_css_provider;
    const char *target_child_name;
    gboolean is_animating_transition;
};

G_DEFINE_TYPE(RatanaIslandWindow, ratana_island_window, GTK_TYPE_APPLICATION_WINDOW)

static char *format_time(double seconds) {
    int s = (int)fmax(0.0, seconds);
    int m = s / 60;
    int sec = s % 60;
    return g_strdup_printf("%d:%02d", m, sec);
}

/* Waveform drawing function for coral-orange equalizer bars */
static void draw_waveform(GtkDrawingArea *area, cairo_t *cr, int width, int height, gpointer user_data) {
    (void)area;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;

    int num_bars = 5;
    double bar_width = 3.0;
    double spacing = 2.5;
    double total_w = num_bars * bar_width + (num_bars - 1) * spacing;
    double start_x = (width - total_w) / 2.0;

    static const double paused_bars[5] = { 6.0, 12.0, 7.0, 14.0, 8.0 };

    if (win->is_playing) {
        cairo_set_source_rgb(cr, 1.0, 0.38, 0.21); /* Coral-orange #ff6036 */
    } else {
        cairo_set_source_rgba(cr, 1.0, 0.38, 0.21, 0.70); /* Elegant paused waveform */
    }

    for (int i = 0; i < num_bars; i++) {
        double x = start_x + i * (bar_width + spacing);
        double bar_h = paused_bars[i];
        if (win->is_playing) {
            double s = sin(win->waveform_phase + i * 1.3);
            bar_h = 5.0 + fabs(s) * (height - 8.0);
        }
        double y = (height - bar_h) / 2.0;

        /* Draw rounded bar */
        cairo_new_sub_path(cr);
        cairo_arc(cr, x + bar_width / 2.0, y + bar_width / 2.0, bar_width / 2.0, M_PI, 0);
        cairo_arc(cr, x + bar_width / 2.0, y + bar_h - bar_width / 2.0, bar_width / 2.0, 0, M_PI);
        cairo_close_path(cr);
        cairo_fill(cr);
    }
}

static gboolean on_waveform_tick(gpointer user_data) {
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (!win->is_playing) return G_SOURCE_CONTINUE;

    win->waveform_phase += 0.28;
    if (win->waveform_phase > 2.0 * M_PI) {
        win->waveform_phase -= 2.0 * M_PI;
    }

    if (win->compact_waveform && GTK_IS_WIDGET(win->compact_waveform)) {
        gtk_widget_queue_draw(win->compact_waveform);
    }
    if (win->media_waveform && GTK_IS_WIDGET(win->media_waveform)) {
        gtk_widget_queue_draw(win->media_waveform);
    }

    return G_SOURCE_CONTINUE;
}

static void set_active_panel(RatanaIslandWindow *win, const char *child_name) {
    if (!win || !child_name) return;
    gtk_widget_set_visible(win->compact_box, g_strcmp0(child_name, "compact") == 0);
    gtk_widget_set_visible(win->expanded_media_box, g_strcmp0(child_name, "expanded_media") == 0);
    gtk_widget_set_visible(win->expanded_ws_box, g_strcmp0(child_name, "expanded_ws") == 0);
    gtk_widget_set_visible(win->expanded_vol_box, g_strcmp0(child_name, "expanded_vol") == 0);
    gtk_widget_set_visible(win->expanded_notif_box, g_strcmp0(child_name, "expanded_notif") == 0);
    gtk_stack_set_visible_child_name(GTK_STACK(win->stack), child_name);
}

static void on_animation_step(double progress, int w, int h, int r, gpointer user_data) {
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    win->current_width = w;
    win->current_height = h;
    win->current_radius = r;

    gtk_widget_set_size_request(win->capsule_box, w, h);

    if (win->dynamic_css_provider) {
        char *radius_css = g_strdup_printf("#island-capsule { border-radius: %dpx; }", r);
        gtk_css_provider_load_from_string(win->dynamic_css_provider, radius_css);
        g_free(radius_css);
    }

    if (win->is_animating_transition && win->target_child_name) {
        if (progress < 0.35) {
            double alpha = 1.0 - (progress / 0.35);
            gtk_widget_set_opacity(win->stack, alpha);
        } else {
            if (g_strcmp0(gtk_stack_get_visible_child_name(GTK_STACK(win->stack)), win->target_child_name) != 0) {
                set_active_panel(win, win->target_child_name);
            }
            double alpha = (progress - 0.35) / 0.65;
            gtk_widget_set_opacity(win->stack, alpha);
        }
    }
}

static void on_animation_done(gpointer user_data) {
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    win->is_animating_transition = FALSE;
    if (win->target_child_name) {
        set_active_panel(win, win->target_child_name);
    }
    gtk_widget_set_opacity(win->stack, 1.0);
}

static void on_capsule_clicked(GtkGestureClick *gesture, int n_press, double x, double y, gpointer user_data) {
    (void)gesture;
    (void)n_press;
    (void)x;
    (void)y;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    ratana_island_window_toggle_expanded(win);
}

static void on_capsule_secondary_clicked(GtkGestureClick *gesture, int n_press, double x, double y, gpointer user_data) {
    (void)gesture;
    (void)n_press;
    (void)x;
    (void)y;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    ratana_island_window_open_settings(win);
}

static void on_output_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (win->media_mgr) {
        media_manager_cycle_player(win->media_mgr);
    }
}

static void on_play_pause_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (win->media_mgr) {
        media_manager_play_pause(win->media_mgr);
    }
}

static void on_next_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (win->media_mgr) {
        media_manager_next(win->media_mgr);
    }
}

static void on_prev_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (win->media_mgr) {
        media_manager_previous(win->media_mgr);
    }
}

static gboolean on_progress_change_value(GtkRange *range, GtkScrollType scroll, double value, gpointer user_data) {
    (void)range;
    (void)scroll;
    RatanaIslandWindow *win = (RatanaIslandWindow *)user_data;
    if (win->media_mgr) {
        media_manager_seek(win->media_mgr, value);
    }
    return FALSE;
}

static void ratana_island_window_dispose(GObject *object) {
    RatanaIslandWindow *win = RATANA_ISLAND_WINDOW(object);

    if (win->dynamic_css_provider) {
        g_object_unref(win->dynamic_css_provider);
        win->dynamic_css_provider = NULL;
    }
    if (win->waveform_timer > 0) {
        g_source_remove(win->waveform_timer);
        win->waveform_timer = 0;
    }
    if (win->anim) {
        animation_free(win->anim);
        win->anim = NULL;
    }

    G_OBJECT_CLASS(ratana_island_window_parent_class)->dispose(object);
}

static void ratana_island_window_class_init(RatanaIslandWindowClass *klass) {
    GObjectClass *object_class = G_OBJECT_CLASS(klass);
    object_class->dispose = ratana_island_window_dispose;
}

static void ratana_island_window_init(RatanaIslandWindow *win) {
    win->current_width = 190;
    win->current_height = 32;
    win->current_radius = 16;
    win->waveform_phase = 0.0;
    win->is_playing = FALSE;
    win->target_child_name = "compact";
    win->is_animating_transition = FALSE;
}

RatanaIslandWindow *ratana_island_window_new(GtkApplication *app,
                                             RatanaSettings *settings,
                                             StateManager *state_mgr,
                                             MediaManager *media_mgr) {
    RatanaIslandWindow *win = g_object_new(RATANA_TYPE_ISLAND_WINDOW, "application", app, NULL);
    win->settings = settings;
    win->state_mgr = state_mgr;
    win->media_mgr = media_mgr;

    /* Wayland GTK Layer Shell setup */
    gtk_layer_init_for_window(GTK_WINDOW(win));
    gtk_layer_set_layer(GTK_WINDOW(win), GTK_LAYER_SHELL_LAYER_OVERLAY);
    gtk_layer_set_namespace(GTK_WINDOW(win), "ratana-island");
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_LEFT, FALSE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_RIGHT, FALSE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_BOTTOM, FALSE);
    gtk_layer_set_exclusive_zone(GTK_WINDOW(win), 0);
    gtk_layer_set_keyboard_mode(GTK_WINDOW(win), GTK_LAYER_SHELL_KEYBOARD_MODE_NONE);
    gtk_layer_set_margin(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_TOP, settings->top_margin);

    /* Root container */
    win->root_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_name(win->root_box, "island-root");
    gtk_widget_set_halign(win->root_box, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(win->root_box, GTK_ALIGN_START);
    gtk_widget_set_margin_top(win->root_box, 0);
    gtk_widget_set_margin_bottom(win->root_box, 6);
    gtk_widget_set_margin_start(win->root_box, 6);
    gtk_widget_set_margin_end(win->root_box, 6);
    gtk_window_set_child(GTK_WINDOW(win), win->root_box);

    /* Island capsule container */
    win->capsule_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_name(win->capsule_box, "island-capsule");
    gtk_widget_set_size_request(win->capsule_box, settings->collapsed_width, settings->collapsed_height);
    gtk_widget_set_overflow(win->capsule_box, GTK_OVERFLOW_HIDDEN);
    gtk_widget_set_halign(win->capsule_box, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(win->capsule_box, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(win->root_box), win->capsule_box);

    win->dynamic_css_provider = gtk_css_provider_new();
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(win->dynamic_css_provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION + 1
    );

    GtkGesture *click = gtk_gesture_click_new();
    gtk_gesture_single_set_button(GTK_GESTURE_SINGLE(click), GDK_BUTTON_PRIMARY);
    g_signal_connect(click, "pressed", G_CALLBACK(on_capsule_clicked), win);
    gtk_widget_add_controller(win->capsule_box, GTK_EVENT_CONTROLLER(click));

    GtkGesture *sec_click = gtk_gesture_click_new();
    gtk_gesture_single_set_button(GTK_GESTURE_SINGLE(sec_click), GDK_BUTTON_SECONDARY);
    g_signal_connect(sec_click, "pressed", G_CALLBACK(on_capsule_secondary_clicked), win);
    gtk_widget_add_controller(win->capsule_box, GTK_EVENT_CONTROLLER(sec_click));

    /* Stack for views */
    win->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(win->stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    gtk_stack_set_transition_duration(GTK_STACK(win->stack), 160);
    gtk_stack_set_hhomogeneous(GTK_STACK(win->stack), FALSE);
    gtk_stack_set_vhomogeneous(GTK_STACK(win->stack), FALSE);
    gtk_box_append(GTK_BOX(win->capsule_box), win->stack);

    /* ========================================================
     * 1. COMPACT VIEW
     * ======================================================== */
    win->compact_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(win->compact_box, "compact-box");
    gtk_widget_set_valign(win->compact_box, GTK_ALIGN_CENTER);
    gtk_widget_set_halign(win->compact_box, GTK_ALIGN_FILL);
    gtk_widget_set_vexpand(win->compact_box, TRUE);
    gtk_widget_set_hexpand(win->compact_box, TRUE);

    win->compact_art = gtk_image_new_from_icon_name("audio-x-generic-symbolic");
    gtk_widget_add_css_class(win->compact_art, "compact-art");
    gtk_image_set_pixel_size(GTK_IMAGE(win->compact_art), 16);
    gtk_widget_set_valign(win->compact_art, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(win->compact_box), win->compact_art);

    win->compact_title = gtk_label_new("Ratana Island");
    gtk_widget_add_css_class(win->compact_title, "compact-title");
    gtk_label_set_ellipsize(GTK_LABEL(win->compact_title), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(win->compact_title), 16);
    gtk_label_set_yalign(GTK_LABEL(win->compact_title), 0.5);
    gtk_widget_set_valign(win->compact_title, GTK_ALIGN_CENTER);
    gtk_widget_set_hexpand(win->compact_title, TRUE);
    gtk_box_append(GTK_BOX(win->compact_box), win->compact_title);

    win->compact_waveform = gtk_drawing_area_new();
    gtk_widget_set_size_request(win->compact_waveform, 22, 14);
    gtk_widget_set_valign(win->compact_waveform, GTK_ALIGN_CENTER);
    gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(win->compact_waveform), draw_waveform, win, NULL);
    gtk_box_append(GTK_BOX(win->compact_box), win->compact_waveform);

    gtk_stack_add_named(GTK_STACK(win->stack), win->compact_box, "compact");

    /* ========================================================
     * 2. EXPANDED MEDIA VIEW (Matches Apple Music Dynamic Island)
     * ======================================================== */
    win->expanded_media_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_add_css_class(win->expanded_media_box, "expanded-media-box");

    /* Row 1: Artwork + Title/Artist + Right Waveform */
    GtkWidget *row1 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_valign(row1, GTK_ALIGN_CENTER);

    GtkWidget *art_frame = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_size_request(art_frame, 52, 52);
    gtk_widget_add_css_class(art_frame, "media-artwork");
    gtk_widget_set_overflow(art_frame, GTK_OVERFLOW_HIDDEN);

    win->art_stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(win->art_stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    gtk_stack_set_transition_duration(GTK_STACK(win->art_stack), 200);

    win->media_art_picture = gtk_picture_new();
    gtk_widget_set_size_request(win->media_art_picture, 52, 52);
    gtk_picture_set_can_shrink(GTK_PICTURE(win->media_art_picture), TRUE);
    gtk_picture_set_content_fit(GTK_PICTURE(win->media_art_picture), GTK_CONTENT_FIT_COVER);
    gtk_stack_add_named(GTK_STACK(win->art_stack), win->media_art_picture, "picture");

    win->media_art_fallback = gtk_image_new_from_icon_name("audio-x-generic-symbolic");
    gtk_image_set_pixel_size(GTK_IMAGE(win->media_art_fallback), 30);
    gtk_widget_add_css_class(win->media_art_fallback, "art-fallback-icon");
    gtk_stack_add_named(GTK_STACK(win->art_stack), win->media_art_fallback, "fallback");
    gtk_stack_set_visible_child_name(GTK_STACK(win->art_stack), "fallback");

    gtk_box_append(GTK_BOX(art_frame), win->art_stack);
    gtk_box_append(GTK_BOX(row1), art_frame);

    GtkWidget *meta_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_valign(meta_box, GTK_ALIGN_CENTER);
    gtk_widget_set_hexpand(meta_box, TRUE);

    win->media_title = gtk_label_new("Lose Control");
    gtk_widget_add_css_class(win->media_title, "media-title");
    gtk_label_set_xalign(GTK_LABEL(win->media_title), 0.0);
    gtk_label_set_ellipsize(GTK_LABEL(win->media_title), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(win->media_title), 22);
    gtk_box_append(GTK_BOX(meta_box), win->media_title);

    win->media_artist = gtk_label_new("Teddy Swims");
    gtk_widget_add_css_class(win->media_artist, "media-artist");
    gtk_label_set_xalign(GTK_LABEL(win->media_artist), 0.0);
    gtk_label_set_ellipsize(GTK_LABEL(win->media_artist), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(win->media_artist), 24);
    gtk_box_append(GTK_BOX(meta_box), win->media_artist);
    gtk_box_append(GTK_BOX(row1), meta_box);

    win->media_waveform = gtk_drawing_area_new();
    gtk_widget_set_size_request(win->media_waveform, 32, 22);
    gtk_widget_set_valign(win->media_waveform, GTK_ALIGN_CENTER);
    gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(win->media_waveform), draw_waveform, win, NULL);
    gtk_box_append(GTK_BOX(row1), win->media_waveform);

    gtk_box_append(GTK_BOX(win->expanded_media_box), row1);

    /* Row 2: Elapsed time + sleek progress bar + Total time */
    GtkWidget *row2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_valign(row2, GTK_ALIGN_CENTER);

    win->elapsed_label = gtk_label_new("0:00");
    gtk_widget_add_css_class(win->elapsed_label, "time-label");
    gtk_box_append(GTK_BOX(row2), win->elapsed_label);

    win->progress_scale = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.0, 100.0, 1.0);
    gtk_widget_add_css_class(win->progress_scale, "media-progress");
    gtk_scale_set_draw_value(GTK_SCALE(win->progress_scale), FALSE);
    gtk_widget_set_hexpand(win->progress_scale, TRUE);
    g_signal_connect(win->progress_scale, "change-value", G_CALLBACK(on_progress_change_value), win);
    gtk_box_append(GTK_BOX(row2), win->progress_scale);

    win->total_label = gtk_label_new("0:00");
    gtk_widget_add_css_class(win->total_label, "time-label");
    gtk_box_append(GTK_BOX(row2), win->total_label);

    gtk_box_append(GTK_BOX(win->expanded_media_box), row2);

    /* Row 3: 5 Playback controls (Shuffle, Prev, Play/Pause, Next, Output) */
    GtkWidget *row3 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_valign(row3, GTK_ALIGN_CENTER);

    win->shuffle_btn = gtk_button_new_from_icon_name("media-playlist-shuffle-symbolic");
    gtk_widget_add_css_class(win->shuffle_btn, "media-btn");
    gtk_widget_add_css_class(win->shuffle_btn, "subtle-btn");
    gtk_box_append(GTK_BOX(row3), win->shuffle_btn);

    GtkWidget *center_btns = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 24);
    gtk_widget_set_hexpand(center_btns, TRUE);
    gtk_widget_set_halign(center_btns, GTK_ALIGN_CENTER);

    win->prev_btn = gtk_button_new_from_icon_name("media-skip-backward-symbolic");
    gtk_widget_add_css_class(win->prev_btn, "media-btn");
    g_signal_connect(win->prev_btn, "clicked", G_CALLBACK(on_prev_clicked), win);
    gtk_box_append(GTK_BOX(center_btns), win->prev_btn);

    win->play_btn = gtk_button_new_from_icon_name("media-playback-start-symbolic");
    gtk_widget_add_css_class(win->play_btn, "media-btn");
    gtk_widget_add_css_class(win->play_btn, "play-btn");
    g_signal_connect(win->play_btn, "clicked", G_CALLBACK(on_play_pause_clicked), win);
    gtk_box_append(GTK_BOX(center_btns), win->play_btn);

    win->next_btn = gtk_button_new_from_icon_name("media-skip-forward-symbolic");
    gtk_widget_add_css_class(win->next_btn, "media-btn");
    g_signal_connect(win->next_btn, "clicked", G_CALLBACK(on_next_clicked), win);
    gtk_box_append(GTK_BOX(center_btns), win->next_btn);
    gtk_box_append(GTK_BOX(row3), center_btns);

    win->output_btn = gtk_button_new_from_icon_name("audio-speakers-symbolic");
    gtk_widget_add_css_class(win->output_btn, "media-btn");
    gtk_widget_add_css_class(win->output_btn, "subtle-btn");
    g_signal_connect(win->output_btn, "clicked", G_CALLBACK(on_output_clicked), win);
    gtk_box_append(GTK_BOX(row3), win->output_btn);

    gtk_box_append(GTK_BOX(win->expanded_media_box), row3);
    gtk_stack_add_named(GTK_STACK(win->stack), win->expanded_media_box, "expanded_media");

    /* ========================================================
     * 3. EXPANDED WORKSPACE VIEW
     * ======================================================== */
    win->expanded_ws_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_add_css_class(win->expanded_ws_box, "expanded-ws-box");
    gtk_widget_set_valign(win->expanded_ws_box, GTK_ALIGN_CENTER);

    win->ws_icon = gtk_image_new_from_icon_name("view-paged-symbolic");
    gtk_widget_add_css_class(win->ws_icon, "ws-icon");
    gtk_image_set_pixel_size(GTK_IMAGE(win->ws_icon), 24);
    gtk_box_append(GTK_BOX(win->expanded_ws_box), win->ws_icon);

    win->ws_label = gtk_label_new("Workspace 1");
    gtk_widget_add_css_class(win->ws_label, "ws-label");
    gtk_label_set_xalign(GTK_LABEL(win->ws_label), 0.0);
    gtk_box_append(GTK_BOX(win->expanded_ws_box), win->ws_label);

    gtk_stack_add_named(GTK_STACK(win->stack), win->expanded_ws_box, "expanded_ws");

    /* ========================================================
     * 4. EXPANDED VOLUME VIEW
     * ======================================================== */
    win->expanded_vol_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_add_css_class(win->expanded_vol_box, "expanded-vol-box");
    gtk_widget_set_valign(win->expanded_vol_box, GTK_ALIGN_CENTER);

    win->vol_icon = gtk_image_new_from_icon_name("audio-volume-high-symbolic");
    gtk_image_set_pixel_size(GTK_IMAGE(win->vol_icon), 24);
    gtk_box_append(GTK_BOX(win->expanded_vol_box), win->vol_icon);

    win->vol_scale = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.0, 100.0, 5.0);
    gtk_scale_set_draw_value(GTK_SCALE(win->vol_scale), FALSE);
    gtk_widget_set_hexpand(win->vol_scale, TRUE);
    gtk_box_append(GTK_BOX(win->expanded_vol_box), win->vol_scale);

    win->vol_label = gtk_label_new("50%");
    gtk_widget_add_css_class(win->vol_label, "vol-label");
    gtk_box_append(GTK_BOX(win->expanded_vol_box), win->vol_label);

    gtk_stack_add_named(GTK_STACK(win->stack), win->expanded_vol_box, "expanded_vol");

    /* ========================================================
     * 5. EXPANDED NOTIFICATION VIEW
     * ======================================================== */
    win->expanded_notif_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_add_css_class(win->expanded_notif_box, "expanded-notif-box");

    win->notif_icon = gtk_image_new_from_icon_name("dialog-information-symbolic");
    gtk_image_set_pixel_size(GTK_IMAGE(win->notif_icon), 32);
    gtk_box_append(GTK_BOX(win->expanded_notif_box), win->notif_icon);

    GtkWidget *notif_txt = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_hexpand(notif_txt, TRUE);

    win->notif_summary = gtk_label_new("Notification");
    gtk_widget_add_css_class(win->notif_summary, "notif-summary");
    gtk_label_set_xalign(GTK_LABEL(win->notif_summary), 0.0);
    gtk_box_append(GTK_BOX(notif_txt), win->notif_summary);

    win->notif_body = gtk_label_new("");
    gtk_widget_add_css_class(win->notif_body, "notif-body");
    gtk_label_set_xalign(GTK_LABEL(win->notif_body), 0.0);
    gtk_label_set_ellipsize(GTK_LABEL(win->notif_body), PANGO_ELLIPSIZE_END);
    gtk_box_append(GTK_BOX(notif_txt), win->notif_body);
    gtk_box_append(GTK_BOX(win->expanded_notif_box), notif_txt);

    gtk_stack_add_named(GTK_STACK(win->stack), win->expanded_notif_box, "expanded_notif");

    /* Default view */
    set_active_panel(win, "compact");

    /* Initialize animation engine */
    win->anim = animation_new(win->capsule_box);

    /* Start Waveform loop */
    win->waveform_timer = g_timeout_add(70, on_waveform_tick, win);

    return win;
}

void ratana_island_window_update_media(RatanaIslandWindow *win, const TrackInfo *track) {
    if (!win || !track) return;

    win->is_playing = track->is_playing;

    /* Compact text */
    if (track->title && *track->title) {
        gtk_label_set_text(GTK_LABEL(win->compact_title), track->title);
    } else {
        gtk_label_set_text(GTK_LABEL(win->compact_title), "Ratana Island");
    }

    /* Expanded Text */
    gtk_label_set_text(GTK_LABEL(win->media_title), track->title ? track->title : "No Track");
    gtk_label_set_text(GTK_LABEL(win->media_artist), track->artist && *track->artist ? track->artist : "Unknown Artist");

    /* Play/Pause Button Icon */
    gtk_button_set_icon_name(GTK_BUTTON(win->play_btn),
                             track->is_playing ? "media-playback-pause-symbolic" : "media-playback-start-symbolic");

    /* Progress & Time */
    gtk_range_set_range(GTK_RANGE(win->progress_scale), 0.0, fmax(1.0, track->duration_sec));
    gtk_range_set_value(GTK_RANGE(win->progress_scale), track->position_sec);

    char *el_str = format_time(track->position_sec);
    gtk_label_set_text(GTK_LABEL(win->elapsed_label), el_str);
    g_free(el_str);

    char *tot_str = format_time(track->duration_sec);
    gtk_label_set_text(GTK_LABEL(win->total_label), tot_str);
    g_free(tot_str);

    /* Artwork */
    if (track->local_art_path && *track->local_art_path && g_file_test(track->local_art_path, G_FILE_TEST_EXISTS)) {
        gtk_picture_set_filename(GTK_PICTURE(win->media_art_picture), track->local_art_path);
        gtk_stack_set_visible_child_name(GTK_STACK(win->art_stack), "picture");
    } else {
        gtk_stack_set_visible_child_name(GTK_STACK(win->art_stack), "fallback");
    }

    gtk_widget_queue_draw(win->compact_waveform);
    gtk_widget_queue_draw(win->media_waveform);
}

void ratana_island_window_update_workspace(RatanaIslandWindow *win, const char *change, const char *ws_name) {
    (void)change;
    if (!win || !ws_name) return;

    char *msg = g_strdup_printf("Workspace %s", ws_name);
    gtk_label_set_text(GTK_LABEL(win->ws_label), msg);
    g_free(msg);

    state_manager_transition_to(win->state_mgr, STATE_EXPANDED_WORKSPACE, win->settings->workspace_timeout_ms);
}

void ratana_island_window_update_notification(RatanaIslandWindow *win, const NotificationInfo *notif) {
    if (!win || !notif) return;

    gtk_label_set_text(GTK_LABEL(win->notif_summary), notif->summary ? notif->summary : "Notification");
    gtk_label_set_text(GTK_LABEL(win->notif_body), notif->body ? notif->body : "");
    if (notif->icon_name && *notif->icon_name) {
        gtk_image_set_from_icon_name(GTK_IMAGE(win->notif_icon), notif->icon_name);
    }

    state_manager_transition_to(win->state_mgr, STATE_EXPANDED_NOTIFICATION, win->settings->notification_timeout_ms);
}

void ratana_island_window_update_status(RatanaIslandWindow *win, const SystemStatusInfo *status, gboolean is_vol) {
    if (!win || !status) return;

    if (is_vol) {
        char *str = g_strdup_printf("%d%%", status->volume_percent);
        gtk_label_set_text(GTK_LABEL(win->vol_label), str);
        g_free(str);

        gtk_range_set_value(GTK_RANGE(win->vol_scale), status->volume_percent);
        if (status->is_muted) {
            gtk_image_set_from_icon_name(GTK_IMAGE(win->vol_icon), "audio-volume-muted-symbolic");
        } else if (status->volume_percent > 60) {
            gtk_image_set_from_icon_name(GTK_IMAGE(win->vol_icon), "audio-volume-high-symbolic");
        } else if (status->volume_percent > 20) {
            gtk_image_set_from_icon_name(GTK_IMAGE(win->vol_icon), "audio-volume-medium-symbolic");
        } else {
            gtk_image_set_from_icon_name(GTK_IMAGE(win->vol_icon), "audio-volume-low-symbolic");
        }

        state_manager_transition_to(win->state_mgr, STATE_EXPANDED_VOLUME, win->settings->volume_timeout_ms);
    }
}

void ratana_island_window_apply_state(RatanaIslandWindow *win, IslandState state, gboolean animated) {
    if (!win) return;

    int target_w = win->settings->collapsed_width;
    int target_h = win->settings->collapsed_height;
    int target_r = win->settings->corner_radius_collapsed;
    const char *child_name = "compact";

    switch (state) {
        case STATE_EXPANDED_MEDIA:
            target_w = win->settings->expanded_width;
            target_h = win->settings->expanded_height;
            target_r = win->settings->corner_radius_expanded;
            child_name = "expanded_media";
            break;
        case STATE_EXPANDED_WORKSPACE:
            target_w = 260;
            target_h = 56;
            target_r = 28;
            child_name = "expanded_ws";
            break;
        case STATE_EXPANDED_VOLUME:
            target_w = 300;
            target_h = 56;
            target_r = 28;
            child_name = "expanded_vol";
            break;
        case STATE_EXPANDED_NOTIFICATION:
            target_w = 360;
            target_h = 76;
            target_r = 32;
            child_name = "expanded_notif";
            break;
        case STATE_COMPACT_MEDIA:
        case STATE_COMPACT_NOTIFICATION:
        case STATE_IDLE:
        default:
            target_w = win->settings->collapsed_width;
            target_h = win->settings->collapsed_height;
            target_r = win->settings->corner_radius_collapsed;
            child_name = "compact";
            break;
    }

    win->target_child_name = child_name;
    win->is_animating_transition = animated;

    if (state_is_expanded(state)) {
        gtk_widget_add_css_class(win->capsule_box, "expanded");
    } else {
        gtk_widget_remove_css_class(win->capsule_box, "expanded");
    }

    if (animated && !win->settings->reduced_motion) {
        animation_start(
            win->anim,
            win->current_width, win->current_height, win->current_radius,
            target_w, target_h, target_r,
            win->settings->animation_duration_ms,
            ANIM_EASE_OUT_CUBIC,
            on_animation_step,
            on_animation_done,
            win
        );
    } else {
        set_active_panel(win, child_name);
        gtk_widget_set_opacity(win->stack, 1.0);
        on_animation_step(1.0, target_w, target_h, target_r, win);
    }
}

void ratana_island_window_toggle_expanded(RatanaIslandWindow *win) {
    if (!win) return;
    IslandState cur = state_manager_get_current(win->state_mgr);
    if (state_is_expanded(cur)) {
        state_manager_transition_to(win->state_mgr, STATE_IDLE, 0);
    } else {
        state_manager_transition_to(win->state_mgr, STATE_EXPANDED_MEDIA, 0);
    }
}

void ratana_island_window_reload_settings(RatanaIslandWindow *win) {
    if (!win) return;
    gtk_layer_set_margin(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_TOP, win->settings->top_margin);
    ratana_island_window_apply_state(win, state_manager_get_current(win->state_mgr), FALSE);
}

void ratana_island_window_open_settings(RatanaIslandWindow *win) {
    if (!win) return;
    GtkApplication *app = gtk_window_get_application(GTK_WINDOW(win));
    ratana_settings_window_present(app, win->settings, win);
}
