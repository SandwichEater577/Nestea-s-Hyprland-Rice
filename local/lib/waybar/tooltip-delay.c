#define _GNU_SOURCE
#include <dlfcn.h>
#include <glib.h>
#include <stdlib.h>
#include <string.h>

/* GTK 3 hardcodes its hover timeout. Adjust only its named tooltip source. */
void g_source_set_name_by_id(guint id, const char *name) {
    static void (*original)(guint, const char *);
    if (!original) original = dlsym(RTLD_NEXT, "g_source_set_name_by_id");
    original(id, name);
    if (!name || strcmp(name, "[gtk+] tooltip_popup_timeout")) return;
    const char *value = getenv("WAYBAR_TOOLTIP_DELAY_MS");
    if (!value) return;
    char *end;
    long ms = strtol(value, &end, 10);
    if (*end || ms < 0 || ms > 10000) return;
    GSource *source = g_main_context_find_source_by_id(NULL, id);
    if (source) g_source_set_ready_time(source, g_get_monotonic_time() + ms * 1000);
}

/* Do not preload this helper into applications started by Waybar. */
__attribute__((constructor)) static void isolate_preload(void) {
    Dl_info info;
    const char *preload = getenv("LD_PRELOAD");
    if (!preload || !dladdr((void *)isolate_preload, &info)) return;
    size_t n = strlen(info.dli_fname);
    if (strncmp(preload, info.dli_fname, n)) return;
    if (preload[n] == ':') setenv("LD_PRELOAD", preload + n + 1, 1);
    else if (!preload[n]) unsetenv("LD_PRELOAD");
}
