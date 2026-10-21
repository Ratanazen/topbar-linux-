#include <glib.h>
#include <assert.h>
#include "../src/notifications.h"

static void test_notification_lifecycle(void) {
    NotificationInfo *n = notification_info_new(101, "Telegram", "Alice", "Hey, are you free?", "dialog-information");
    assert(n != NULL);
    assert(n->id == 101);
    assert(g_strcmp0(n->app_name, "Telegram") == 0);
    assert(g_strcmp0(n->summary, "Alice") == 0);
    assert(g_strcmp0(n->body, "Hey, are you free?") == 0);

    NotificationInfo *copy = notification_info_copy(n);
    assert(copy != NULL);
    assert(copy->id == 101);
    assert(g_strcmp0(copy->summary, "Alice") == 0);

    notification_info_free(copy);
    notification_info_free(n);
    g_print("[PASS] test_notification_lifecycle\n");
}

static void test_notification_null_safety(void) {
    NotificationInfo *n = notification_info_new(0, NULL, NULL, NULL, NULL);
    assert(n != NULL);
    assert(g_strcmp0(n->app_name, "System") == 0);
    assert(g_strcmp0(n->summary, "Notification") == 0);
    assert(g_strcmp0(n->body, "") == 0);
    notification_info_free(n);
    g_print("[PASS] test_notification_null_safety\n");
}

int main(void) {
    test_notification_lifecycle();
    test_notification_null_safety();
    g_print("All notification tests PASSED!\n");
    return 0;
}
