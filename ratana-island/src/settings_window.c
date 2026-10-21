#include "settings_window.h"
#include <glib/gstdio.h>

typedef struct {
    GtkWidget *window;
    RatanaSettings *settings;
    RatanaIslandWindow *island_win;

    /* Dimensions */
    GtkWidget *spin_col_w;
    GtkWidget *spin_col_h;
    GtkWidget *spin_exp_w;
    GtkWidget *spin_exp_h;
    GtkWidget *spin_top_margin;
    GtkWidget *spin_rad_col;
    GtkWidget *spin_rad_exp;

    /* Animation */
    GtkWidget *spin_anim_dur;
    GtkWidget *sw_reduced_motion;
    GtkWidget *sw_low_power;

    /* Integrations */
    GtkWidget *sw_media;
    GtkWidget *sw_sway;
    GtkWidget *sw_notif;
    GtkWidget *sw_privacy;
    GtkWidget *sw_status;

    /* Autostart */
    GtkWidget *sw_autostart;

    /* Theme */
    GtkWidget *dropdown_theme;

    /* Status feedback */
    GtkWidget *status_label;
} SettingsDialog;

static SettingsDialog *active_dialog = NULL;

static gboolean check_autostart_enabled(void) {
    int exit_status = 0;
    char *out = NULL;
    gboolean ok = g_spawn_command_line_sync("systemctl --user is-enabled ratana-island.service",
                                           &out, NULL, &exit_status, NULL);
    g_free(out);
    return (ok && exit_status == 0);
}

static void apply_autostart(gboolean enable) {
    const char *cfg_home = g_get_user_config_dir();
    char *user_systemd = g_build_filename(cfg_home, "systemd", "user", NULL);
    g_mkdir_with_parents(user_systemd, 0755);

    char *service_dst = g_build_filename(user_systemd, "ratana-island.service", NULL);
    g_free(user_systemd);

    if (enable) {
        if (!g_file_test(service_dst, G_FILE_TEST_EXISTS)) {
            const char *content =
                "[Unit]\n"
                "Description=Ratana Dynamic Island for Sway/SwayFX\n"
                "PartOf=graphical-session.target\n"
                "After=graphical-session.target\n\n"
                "[Service]\n"
                "Type=simple\n"
                "ExecStart=%h/.local/bin/ratana-island\n"
                "Restart=on-failure\n"
                "RestartSec=2s\n\n"
                "[Install]\n"
                "WantedBy=graphical-session.target\n";
            g_file_set_contents(service_dst, content, -1, NULL);
        }
        g_spawn_command_line_async("systemctl --user daemon-reload", NULL);
        g_spawn_command_line_async("systemctl --user enable ratana-island.service", NULL);
    } else {
        g_spawn_command_line_async("systemctl --user disable ratana-island.service", NULL);
    }
    g_free(service_dst);
}

static void on_save_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    SettingsDialog *sd = (SettingsDialog *)user_data;
    RatanaSettings *s = sd->settings;

    s->collapsed_width = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_col_w));
    s->collapsed_height = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_col_h));
    s->expanded_width = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_exp_w));
    s->expanded_height = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_exp_h));
    s->top_margin = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_top_margin));
    s->corner_radius_collapsed = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_rad_col));
    s->corner_radius_expanded = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_rad_exp));

    s->animation_duration_ms = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(sd->spin_anim_dur));
    s->reduced_motion = gtk_switch_get_active(GTK_SWITCH(sd->sw_reduced_motion));
    s->low_power_mode = gtk_switch_get_active(GTK_SWITCH(sd->sw_low_power));

    s->enable_media = gtk_switch_get_active(GTK_SWITCH(sd->sw_media));
    s->enable_sway = gtk_switch_get_active(GTK_SWITCH(sd->sw_sway));
    s->enable_notifications = gtk_switch_get_active(GTK_SWITCH(sd->sw_notif));
    s->privacy_mode = gtk_switch_get_active(GTK_SWITCH(sd->sw_privacy));
    s->enable_system_status = gtk_switch_get_active(GTK_SWITCH(sd->sw_status));

    guint sel = gtk_drop_down_get_selected(GTK_DROP_DOWN(sd->dropdown_theme));
    const char *themes[] = { "mac_obsidian", "mac_tahoe", "midnight", "sunset" };
    if (sel < G_N_ELEMENTS(themes)) {
        g_free(s->theme);
        s->theme = g_strdup(themes[sel]);
    }

    /* Save to config file */
    ratana_settings_save(s, NULL);

    /* Apply autostart change */
    gboolean autostart = gtk_switch_get_active(GTK_SWITCH(sd->sw_autostart));
    apply_autostart(autostart);

    /* Reload island window live if available */
    if (sd->island_win) {
        ratana_island_window_reload_settings(sd->island_win);
    }

    gtk_label_set_text(GTK_LABEL(sd->status_label), "✓ Preferences saved and applied live!");
}

static void on_reset_clicked(GtkButton *btn, gpointer user_data) {
    (void)btn;
    SettingsDialog *sd = (SettingsDialog *)user_data;
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_col_w), 190);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_col_h), 32);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_exp_w), 380);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_exp_h), 165);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_top_margin), 4);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_rad_col), 16);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_rad_exp), 36);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_anim_dur), 240);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_reduced_motion), FALSE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_low_power), FALSE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_media), TRUE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_sway), TRUE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_notif), TRUE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_privacy), FALSE);
    gtk_switch_set_active(GTK_SWITCH(sd->sw_status), TRUE);
    gtk_drop_down_set_selected(GTK_DROP_DOWN(sd->dropdown_theme), 0);
    gtk_label_set_text(GTK_LABEL(sd->status_label), "Reset to macOS Tahoe defaults (click Apply to save)");
}

static GtkWidget *create_row(const char *title, const char *desc, GtkWidget *control) {
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_margin_top(box, 6);
    gtk_widget_set_margin_bottom(box, 6);

    GtkWidget *label_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    GtkWidget *lbl_title = gtk_label_new(title);
    gtk_label_set_xalign(GTK_LABEL(lbl_title), 0.0);
    gtk_widget_add_css_class(lbl_title, "heading");
    gtk_box_append(GTK_BOX(label_box), lbl_title);

    if (desc && *desc) {
        GtkWidget *lbl_desc = gtk_label_new(desc);
        gtk_label_set_xalign(GTK_LABEL(lbl_desc), 0.0);
        gtk_widget_add_css_class(lbl_desc, "dim-label");
        gtk_box_append(GTK_BOX(label_box), lbl_desc);
    }
    gtk_widget_set_hexpand(label_box, TRUE);
    gtk_box_append(GTK_BOX(box), label_box);

    gtk_widget_set_valign(control, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(box), control);

    return box;
}

static GtkWidget *create_section_card(const char *header_title) {
    GtkWidget *card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_add_css_class(card, "card");
    gtk_widget_set_margin_bottom(card, 12);

    GtkWidget *header = gtk_label_new(header_title);
    gtk_label_set_xalign(GTK_LABEL(header), 0.0);
    gtk_widget_add_css_class(header, "title-4");
    gtk_widget_set_margin_bottom(header, 4);
    gtk_box_append(GTK_BOX(card), header);

    return card;
}

static void on_dialog_destroy(GtkWidget *widget, gpointer user_data) {
    (void)widget;
    (void)user_data;
    active_dialog = NULL;
}

void ratana_settings_window_present(GtkApplication *app,
                                    RatanaSettings *settings,
                                    RatanaIslandWindow *island_win) {
    if (active_dialog) {
        gtk_window_present(GTK_WINDOW(active_dialog->window));
        return;
    }

    SettingsDialog *sd = g_new0(SettingsDialog, 1);
    sd->settings = settings;
    sd->island_win = island_win;
    active_dialog = sd;

    sd->window = gtk_window_new();
    gtk_window_set_application(GTK_WINDOW(sd->window), app);
    gtk_window_set_title(GTK_WINDOW(sd->window), "Ratana Dynamic Island Settings");
    gtk_window_set_default_size(GTK_WINDOW(sd->window), 520, 620);
    g_signal_connect(sd->window, "destroy", G_CALLBACK(on_dialog_destroy), sd);

    GtkWidget *header = gtk_header_bar_new();
    GtkWidget *title_lbl = gtk_label_new("Dynamic Island Settings");
    gtk_widget_add_css_class(title_lbl, "title-3");
    gtk_header_bar_set_title_widget(GTK_HEADER_BAR(header), title_lbl);

    GtkWidget *save_btn = gtk_button_new_with_label("Apply & Save");
    gtk_widget_add_css_class(save_btn, "suggested-action");
    g_signal_connect(save_btn, "clicked", G_CALLBACK(on_save_clicked), sd);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(header), save_btn);

    GtkWidget *reset_btn = gtk_button_new_with_label("Reset");
    g_signal_connect(reset_btn, "clicked", G_CALLBACK(on_reset_clicked), sd);
    gtk_header_bar_pack_start(GTK_HEADER_BAR(header), reset_btn);

    gtk_window_set_titlebar(GTK_WINDOW(sd->window), header);

    GtkWidget *scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_window_set_child(GTK_WINDOW(sd->window), scroll);

    GtkWidget *main_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(main_box, 16);
    gtk_widget_set_margin_bottom(main_box, 16);
    gtk_widget_set_margin_start(main_box, 20);
    gtk_widget_set_margin_end(main_box, 20);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll), main_box);

    /* Status label */
    sd->status_label = gtk_label_new("");
    gtk_widget_add_css_class(sd->status_label, "accent");
    gtk_widget_set_margin_bottom(sd->status_label, 8);
    gtk_box_append(GTK_BOX(main_box), sd->status_label);

    /* 1. Dimensions */
    GtkWidget *card_dim = create_section_card("Dimensions & Positioning");
    sd->spin_top_margin = gtk_spin_button_new_with_range(-60, 60, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_top_margin), settings->top_margin);
    gtk_box_append(GTK_BOX(card_dim), create_row("Top Margin", "Distance in pixels (-32 aligns directly in Topbar)", sd->spin_top_margin));

    sd->spin_col_w = gtk_spin_button_new_with_range(120, 320, 5);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_col_w), settings->collapsed_width);
    gtk_box_append(GTK_BOX(card_dim), create_row("Compact Width", "Pill width when collapsed", sd->spin_col_w));

    sd->spin_col_h = gtk_spin_button_new_with_range(24, 48, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_col_h), settings->collapsed_height);
    gtk_box_append(GTK_BOX(card_dim), create_row("Compact Height", "Pill height when collapsed", sd->spin_col_h));

    sd->spin_exp_w = gtk_spin_button_new_with_range(280, 500, 5);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_exp_w), settings->expanded_width);
    gtk_box_append(GTK_BOX(card_dim), create_row("Expanded Width", "Card width when opened", sd->spin_exp_w));

    sd->spin_exp_h = gtk_spin_button_new_with_range(120, 240, 5);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_exp_h), settings->expanded_height);
    gtk_box_append(GTK_BOX(card_dim), create_row("Expanded Height", "Card height when opened", sd->spin_exp_h));

    sd->spin_rad_col = gtk_spin_button_new_with_range(10, 24, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_rad_col), settings->corner_radius_collapsed);
    gtk_box_append(GTK_BOX(card_dim), create_row("Compact Corner Radius", "Corner rounding for compact pill", sd->spin_rad_col));

    sd->spin_rad_exp = gtk_spin_button_new_with_range(20, 48, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_rad_exp), settings->corner_radius_expanded);
    gtk_box_append(GTK_BOX(card_dim), create_row("Expanded Corner Radius", "Corner rounding for expanded card", sd->spin_rad_exp));
    gtk_box_append(GTK_BOX(main_box), card_dim);

    /* 2. Animation & Motion */
    GtkWidget *card_anim = create_section_card("Animation & Motion");
    sd->spin_anim_dur = gtk_spin_button_new_with_range(100, 600, 20);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(sd->spin_anim_dur), settings->animation_duration_ms);
    gtk_box_append(GTK_BOX(card_anim), create_row("Animation Duration (ms)", "Transition time in milliseconds", sd->spin_anim_dur));

    sd->sw_reduced_motion = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_reduced_motion), settings->reduced_motion);
    gtk_box_append(GTK_BOX(card_anim), create_row("Reduced Motion", "Instantly switch states without easing animation", sd->sw_reduced_motion));

    sd->sw_low_power = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_low_power), settings->low_power_mode);
    gtk_box_append(GTK_BOX(card_anim), create_row("Low Power Mode", "Throttle equalizer tick callbacks", sd->sw_low_power));
    gtk_box_append(GTK_BOX(main_box), card_anim);

    /* 3. Appearance & Themes */
    GtkWidget *card_theme = create_section_card("Theme & Appearance");
    const char *themes[] = { "Mac Obsidian (Pitch Black)", "Mac Tahoe (Dark Glass)", "Midnight Navy", "Sunset Coral", NULL };
    sd->dropdown_theme = gtk_drop_down_new_from_strings(themes);
    if (g_strcmp0(settings->theme, "mac_tahoe") == 0) gtk_drop_down_set_selected(GTK_DROP_DOWN(sd->dropdown_theme), 1);
    else if (g_strcmp0(settings->theme, "midnight") == 0) gtk_drop_down_set_selected(GTK_DROP_DOWN(sd->dropdown_theme), 2);
    else if (g_strcmp0(settings->theme, "sunset") == 0) gtk_drop_down_set_selected(GTK_DROP_DOWN(sd->dropdown_theme), 3);
    else gtk_drop_down_set_selected(GTK_DROP_DOWN(sd->dropdown_theme), 0);
    gtk_box_append(GTK_BOX(card_theme), create_row("Theme Style", "Color palette and glass opacity", sd->dropdown_theme));
    gtk_box_append(GTK_BOX(main_box), card_theme);

    /* 4. Integrations & Privacy */
    GtkWidget *card_int = create_section_card("Desktop Integrations");
    sd->sw_media = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_media), settings->enable_media);
    gtk_box_append(GTK_BOX(card_int), create_row("Media Player (MPRIS)", "Track Spotify, YouTube, browser & local players", sd->sw_media));

    sd->sw_sway = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_sway), settings->enable_sway);
    gtk_box_append(GTK_BOX(card_int), create_row("Sway Workspaces", "Show animated pill on workspace change", sd->sw_sway));

    sd->sw_notif = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_notif), settings->enable_notifications);
    gtk_box_append(GTK_BOX(card_int), create_row("Notifications Preview", "Display incoming desktop notifications", sd->sw_notif));

    sd->sw_privacy = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_privacy), settings->privacy_mode);
    gtk_box_append(GTK_BOX(card_int), create_row("Notification Privacy Mode", "Mask sensitive notification body and summary", sd->sw_privacy));

    sd->sw_status = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_status), settings->enable_system_status);
    gtk_box_append(GTK_BOX(card_int), create_row("System Status", "Show volume and battery level overlays", sd->sw_status));
    gtk_box_append(GTK_BOX(main_box), card_int);

    /* 5. Autostart */
    GtkWidget *card_auto = create_section_card("Startup");
    sd->sw_autostart = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(sd->sw_autostart), check_autostart_enabled());
    gtk_box_append(GTK_BOX(card_auto), create_row("Systemd User Autostart", "Launch Ratana Island on login via systemd service", sd->sw_autostart));
    gtk_box_append(GTK_BOX(main_box), card_auto);

    gtk_window_present(GTK_WINDOW(sd->window));
}
