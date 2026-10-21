#include <glib.h>
#include <json-glib/json-glib.h>
#include <assert.h>
#include <string.h>

static void test_workspace_json_parser(void) {
    const char *sample_json =
        "{\"change\":\"focus\",\"current\":{\"id\":2,\"name\":\"3: Work\",\"num\":3,\"focused\":true}}";

    JsonParser *parser = json_parser_new();
    GError *err = NULL;
    gboolean ok = json_parser_load_from_data(parser, sample_json, -1, &err);
    assert(ok && err == NULL);

    JsonNode *root = json_parser_get_root(parser);
    assert(root != NULL);
    JsonObject *obj = json_node_get_object(root);
    assert(obj != NULL);

    const char *change = json_object_get_string_member(obj, "change");
    assert(g_strcmp0(change, "focus") == 0);

    JsonObject *cur = json_object_get_object_member(obj, "current");
    assert(cur != NULL);

    const char *name = json_object_get_string_member(cur, "name");
    assert(g_strcmp0(name, "3: Work") == 0);

    g_object_unref(parser);
    g_print("[PASS] test_workspace_json_parser\n");
}

static void test_malformed_json_resilience(void) {
    const char *bad_json = "{\"change\":\"focus\",\"current\": incomplete...";

    JsonParser *parser = json_parser_new();
    GError *err = NULL;
    gboolean ok = json_parser_load_from_data(parser, bad_json, -1, &err);
    assert(!ok);
    assert(err != NULL);
    g_error_free(err);
    g_object_unref(parser);
    g_print("[PASS] test_malformed_json_resilience\n");
}

int main(void) {
    test_workspace_json_parser();
    test_malformed_json_resilience();
    g_print("All IPC robustness tests PASSED!\n");
    return 0;
}
