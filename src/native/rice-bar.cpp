#include <gtk/gtk.h>
#include <gtk-layer-shell.h>
#include <json-glib/json-glib.h>
#include <functional>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <ctime>
#include <thread>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#ifdef __x86_64__
extern "C" int rice_luma_u8(int red, int green, int blue);
#else
static int rice_luma_u8(int r, int g, int b) { return (54*r + 183*g + 19*b) >> 8; }
#endif

static std::string home;
static GtkWidget *audio_label, *network_label, *display_label, *bluetooth_label, *battery_label, *spotify_box, *cover_event, *cover_image;
static GtkWidget *spotify_label, *repeat_label, *shuffle_label, *workspaces[6];
static GtkCssProvider *theme_provider;

static std::string read_file(const std::string &path) {
    std::ifstream input(path);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

// Bump the kick file so bar-status --watch re-reads everything right now.
static void kick() {
    std::string path = home + "/.local/state/rice/status-kick";
    int fd = open(path.c_str(), O_WRONLY | O_CREAT, 0644);
    if (fd >= 0) close(fd);
    utimensat(AT_FDCWD, path.c_str(), nullptr, 0);
}

static std::string json_string(JsonObject *object, const char *key, const char *fallback = "") {
    if (!object || !json_object_has_member(object, key)) return fallback;
    JsonNode *node = json_object_get_member(object, key);
    return JSON_NODE_HOLDS_VALUE(node) && json_node_get_value_type(node) == G_TYPE_STRING
        ? json_node_get_string(node) : fallback;
}

static JsonParser *parse(const std::string &data) {
    JsonParser *parser = json_parser_new();
    if (!json_parser_load_from_data(parser, data.c_str(), data.size(), nullptr) ||
        !JSON_NODE_HOLDS_OBJECT(json_parser_get_root(parser))) {
        g_object_unref(parser);
        return nullptr;
    }
    return parser;
}

static std::string capture(const std::vector<std::string> &args) {
    std::vector<char*> argv;
    for (const auto &arg : args) argv.push_back(const_cast<char*>(arg.c_str()));
    argv.push_back(nullptr);
    gchar *out = nullptr, *err = nullptr;
    gint status = 0;
    if (!g_spawn_sync(nullptr, argv.data(), nullptr, G_SPAWN_SEARCH_PATH, nullptr, nullptr,
                      &out, &err, &status, nullptr)) return "";
    std::string result = out ? out : "";
    g_free(out); g_free(err);
    return status == 0 ? result : "";
}

static void launch(std::vector<std::string> args) {
    std::vector<char*> argv;
    for (auto &arg : args) argv.push_back(arg.data());
    argv.push_back(nullptr);
    g_spawn_async(nullptr, argv.data(), nullptr, G_SPAWN_SEARCH_PATH,
                  nullptr, nullptr, nullptr, nullptr);
    kick();
}

static GtkWidget *button(GtkWidget *box, const std::string &text,
                         std::function<void(guint)> action, const char *hint = nullptr) {
    GtkWidget *event = gtk_event_box_new();
    GtkWidget *label = gtk_label_new(text.c_str());
    gtk_container_add(GTK_CONTAINER(event), label);
    gtk_widget_set_name(event, "rice-button");
    gtk_widget_set_size_request(event, -1, 26);
    gtk_widget_set_margin_start(label, 7);
    gtk_widget_set_margin_end(label, 7);
    gtk_widget_set_margin_top(label, 5);
    gtk_widget_set_margin_bottom(label, 5);
    gtk_widget_add_events(event, GDK_BUTTON_PRESS_MASK | GDK_SCROLL_MASK);
    if (hint) gtk_widget_set_tooltip_text(event, hint);
    auto *callback = new std::function<void(guint)>(std::move(action));
    g_signal_connect_data(event, "button-press-event", G_CALLBACK(+[](GtkWidget*, GdkEventButton *e, gpointer data) -> gboolean {
        (*static_cast<std::function<void(guint)>*>(data))(e->button); return TRUE;
    }), callback, +[](gpointer data, GClosure*) { delete static_cast<std::function<void(guint)>*>(data); }, GConnectFlags(0));
    gtk_box_pack_start(GTK_BOX(box), event, FALSE, FALSE, 0);
    return label;
}

static void apply_palette() {
    static std::string previous;
    std::string contents = read_file(home + "/.local/state/rice/palette.json");
    if (contents == previous) return;
    previous = contents;
    JsonParser *parser = parse(contents);
    JsonObject *p = parser ? json_node_get_object(json_parser_get_root(parser)) : nullptr;
    auto val = [p](const char *key, const char *fallback) { return json_string(p, key, fallback); };
    std::string accent = val("accent", "#dedede");
    int r=222,g=222,b=222;
    if (accent.size() == 7) sscanf(accent.c_str(), "#%02x%02x%02x", &r,&g,&b);
    // The x86-64 build uses the assembly luminance routine for active text.
    std::string selected_ink = rice_luma_u8(r,g,b) < 120 ? "#ffffff" : "#181818";
    std::string css =
        "* { font-family: 'Adwaita Sans', 'JetBrainsMono Nerd Font'; font-size: 12px; color: " + val("foreground", "#e4e4e4") + "; }"
        "window { background: transparent; }"
        "#rice-group, #rice-group-left, #rice-group-right, #rice-group-center { background: " + val("background", "#161616") + "; border: 1px solid " + val("border", "#3b3b3b") + "; border-radius: 10px; padding: 2px 5px; transition: background-color 200ms ease-out, border-color 200ms ease-out; }"
        "#rice-group-left { padding-right: 19px; }"
        "#rice-group-right { padding-right: 10px; }"
        "#rice-group-center { padding: 2px 6px; }"
        "#rice-button { padding: 4px 8px; border-radius: 6px; transition: background-color 200ms ease-out, color 200ms ease-out; }"
        "#rice-button:hover { background: " + val("hover", "#303030") + "; }"
        // Transport glyphs run at double size; the label gives back its vertical
        // margin and this rule its vertical padding so the 40px bar never grows.
        "#rice-media-button { padding: 0 8px; border-radius: 6px; transition: background-color 200ms ease-out, color 200ms ease-out; }"
        "#rice-media-button:hover { background: " + val("hover", "#303030") + "; }"
        "#rice-media-icon { font-size: 24px; }"
        "#rice-media-icon-small { font-size: 16px; }"
        "#workspace-idle { border-radius: 5px; }"
        "#workspace-idle:hover { background: " + val("hover", "#303030") + "; }"
        "#workspace-attention { border: 1px solid " + accent + "; border-radius: 5px; }"
        "#workspace-attention label { color: " + accent + "; }"
        "#workspace-active { background: " + accent + "; border-radius: 5px; }"
        "#workspace-active label { color: " + selected_ink + "; }";
    gtk_css_provider_load_from_data(theme_provider, css.c_str(), -1, nullptr);
    if (parser) g_object_unref(parser);
}

static bool clock_12h() {
    JsonParser *parser = parse(read_file(home + "/.config/rice/settings.json"));
    bool result = parser && json_string(json_node_get_object(json_parser_get_root(parser)), "time_format") == "12h";
    if (parser) g_object_unref(parser);
    return result;
}

static void update_status(const std::string &status) {
    JsonParser *parser = parse(status);
    if (parser) {
        JsonObject *data = json_node_get_object(json_parser_get_root(parser));
        gtk_label_set_text(GTK_LABEL(audio_label), json_string(data, "audio", "󰝟 —").c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(audio_label), json_string(data, "audio_tooltip", "Sound").c_str());
        gtk_label_set_text(GTK_LABEL(network_label), json_string(data, "network", "󰖪").c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(network_label), json_string(data, "network_tooltip", "Networks").c_str());
        std::string display = json_string(data, "display");
        gtk_label_set_text(GTK_LABEL(display_label), display.c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(display_label), json_string(data, "display_tooltip", "Displays").c_str());
        gtk_widget_set_visible(gtk_widget_get_parent(display_label), !display.empty());
        std::string bluetooth = json_string(data, "bluetooth");
        gtk_label_set_text(GTK_LABEL(bluetooth_label), bluetooth.c_str());
        gtk_widget_set_visible(gtk_widget_get_parent(bluetooth_label), !bluetooth.empty());
        std::string battery = json_string(data, "battery");
        gtk_label_set_text(GTK_LABEL(battery_label), ("  " + battery).c_str());
        gtk_widget_set_visible(gtk_widget_get_parent(battery_label), !battery.empty());
        std::string spotify = json_string(data, "spotify");
        static std::string previous_cover;
        std::string cover = json_string(data, "cover");
        if (cover != previous_cover) {
            previous_cover = cover;
            if (!cover.empty()) {
                GdkPixbuf *pixbuf = gdk_pixbuf_new_from_file_at_scale(cover.c_str(), 24, 24, TRUE, nullptr);
                if (pixbuf) { gtk_image_set_from_pixbuf(GTK_IMAGE(cover_image), pixbuf); g_object_unref(pixbuf); }
            }
        }
        gtk_widget_set_tooltip_text(cover_event, json_string(data, "track", "Spotify").c_str());
        gtk_widget_set_visible(cover_event, !cover.empty());
        gtk_label_set_text(GTK_LABEL(spotify_label), spotify.c_str());
        gtk_label_set_text(GTK_LABEL(repeat_label), json_string(data, "repeat", "󰑗").c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(repeat_label), json_string(data, "repeat_tooltip", "Repeat").c_str());
        gtk_label_set_text(GTK_LABEL(shuffle_label), json_string(data, "shuffle", "󰒟").c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(shuffle_label), json_string(data, "shuffle_tooltip", "Shuffle").c_str());
        gtk_widget_set_visible(spotify_box, !spotify.empty());
        gtk_widget_set_visible(gtk_widget_get_parent(repeat_label), !json_string(data, "repeat").empty());
        gtk_widget_set_visible(gtk_widget_get_parent(shuffle_label), !json_string(data, "shuffle").empty());
        g_object_unref(parser);
    }
}

static void update_workspace(const std::string &state) {
    JsonParser *parser = parse(state);
    if (!parser) return;
    JsonObject *data = json_node_get_object(json_parser_get_root(parser));
    int active = json_object_get_int_member_with_default(data, "active", 0);
    int extra = json_object_get_int_member_with_default(data, "extra", 0);
    JsonArray *attention = json_object_has_member(data, "attention")
        ? json_object_get_array_member(data, "attention") : nullptr;
    auto needs_attention = [attention](int id) {
        if (!attention) return false;
        for (guint i = 0; i < json_array_get_length(attention); ++i)
            if (json_array_get_int_element(attention, i) == id) return true;
        return false;
    };
    for (int i = 0; i < 6; ++i) {
        int id = i == 5 ? extra : i + 1;
        gtk_widget_set_name(workspaces[i], id == active ? "workspace-active" :
            needs_attention(id) ? "workspace-attention" : "workspace-idle");
    }
    if (extra > 5) {
        g_object_set_data(G_OBJECT(workspaces[5]), "workspace", GINT_TO_POINTER(extra));
        gtk_label_set_text(GTK_LABEL(gtk_bin_get_child(GTK_BIN(workspaces[5]))), std::to_string(extra).c_str());
    }
    gtk_widget_set_visible(workspaces[5], extra > 5);
    g_object_unref(parser);
}

// Persistent pipeline: one bar-status --watch child, one JSON line per change,
// applied on the GTK main loop. Restarts itself if the child dies.
static void watch_status() {
    const std::string command = home + "/.local/bin/bar-status --watch";
    for (;;) {
        FILE *pipe = popen(command.c_str(), "r");
        if (!pipe) { sleep(2); continue; }
        char line[16384];
        while (fgets(line, sizeof line, pipe)) {
            auto *payload = new std::string(line);
            g_idle_add(+[](gpointer data) -> gboolean {
                update_status(*static_cast<std::string*>(data));
                delete static_cast<std::string*>(data);
                return G_SOURCE_REMOVE;
            }, payload);
        }
        pclose(pipe);
        sleep(2);
    }
}

// One helper turns workspace and urgent socket events into complete bar state.
static void watch_workspaces() {
    const std::string command = home + "/.local/bin/rice-workspace --stream";
    for (;;) {
        FILE *pipe = popen(command.c_str(), "r");
        if (!pipe) { sleep(2); continue; }
        char line[2048];
        while (fgets(line, sizeof line, pipe)) {
            auto *payload = new std::string(line);
            g_idle_add(+[](gpointer data) -> gboolean {
                update_workspace(*static_cast<std::string*>(data));
                delete static_cast<std::string*>(data);
                return G_SOURCE_REMOVE;
            }, payload);
        }
        pclose(pipe);
        sleep(2);
    }
}

int main(int argc, char **argv) {
    const char *h = g_get_home_dir(); home = h ? h : "";
    gtk_init(&argc, &argv);
    theme_provider = gtk_css_provider_new();
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(), GTK_STYLE_PROVIDER(theme_provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_widget_set_name(window, "rice-native-bar");
    gtk_layer_init_for_window(GTK_WINDOW(window));
    gtk_layer_set_layer(GTK_WINDOW(window), GTK_LAYER_SHELL_LAYER_TOP);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_RIGHT, TRUE);
    gtk_layer_set_exclusive_zone(GTK_WINDOW(window), 40);
    gtk_window_set_default_size(GTK_WINDOW(window), -1, 40);
    gtk_widget_set_size_request(window, -1, 40);
    g_signal_connect(window, "destroy", G_CALLBACK(gtk_main_quit), nullptr);
    GtkWidget *overlay = gtk_overlay_new(); gtk_container_add(GTK_CONTAINER(window), overlay);
    GtkWidget *body = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0); gtk_container_add(GTK_CONTAINER(overlay), body);
    auto group = [](GtkWidget *parent, const char *name = "rice-group") {
        GtkWidget *frame = gtk_event_box_new(); gtk_widget_set_name(frame, name);
        gtk_widget_set_size_request(frame, -1, 31);
        GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
        gtk_container_add(GTK_CONTAINER(frame), row); gtk_box_pack_start(GTK_BOX(parent), frame, FALSE, FALSE, 8);
        gtk_widget_set_valign(frame, GTK_ALIGN_CENTER); return row;
    };
    GtkWidget *left = group(body, "rice-group-left");
    GtkWidget *clock = button(left, "", [](guint){}, "Clock");
    gtk_label_set_width_chars(GTK_LABEL(clock), 8);
    audio_label = button(left, "󰝟 —", [](guint b) {
        launch({home+"/.local/bin/desktop-menu", "audio", b==2 ? "boost" : b==3 ? "menu" : "mute"});
    }, "Sound: left mute · middle boost · right settings");
    g_signal_connect(gtk_widget_get_parent(audio_label), "scroll-event",
                     G_CALLBACK(+[](GtkWidget*, GdkEventScroll *e, gpointer) -> gboolean {
        launch({home+"/.local/bin/desktop-menu", "audio", e->direction == GDK_SCROLL_UP ? "up" : "down"});
        return TRUE;
    }), nullptr);
    spotify_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0); gtk_box_pack_start(GTK_BOX(left), spotify_box, FALSE, FALSE, 0);
    cover_event = gtk_event_box_new();
    cover_image = gtk_image_new();
    gtk_container_add(GTK_CONTAINER(cover_event), cover_image);
    gtk_widget_set_margin_start(cover_event, 0);
    gtk_widget_set_margin_end(cover_event, 0);
    gtk_box_pack_start(GTK_BOX(spotify_box), cover_event, FALSE, FALSE, 0);
    g_signal_connect(cover_event, "button-press-event", G_CALLBACK(+[](GtkWidget*, GdkEventButton*, gpointer) -> gboolean {
        launch({home+"/.local/bin/desktop-panel", "media"}); return TRUE;
    }), nullptr);
    shuffle_label = button(spotify_box, "󰒟", [](guint b){
        if (b == 3) launch({home+"/.local/bin/desktop-panel", "media"});
        else launch({home+"/.local/bin/waybar-spotify", "--toggle-shuffle"});
    });
    GtkWidget *prev_label = button(spotify_box, "󰒮", [](guint){launch({home+"/.local/bin/rice-media","previous"});});
    spotify_label = button(spotify_box, "", [](guint b){
        if (b == 3) launch({home+"/.local/bin/desktop-panel", "media"});
        else launch({home+"/.local/bin/rice-media","toggle"});
    });
    g_signal_connect(gtk_widget_get_parent(spotify_label), "scroll-event",
                     G_CALLBACK(+[](GtkWidget*, GdkEventScroll *e, gpointer) -> gboolean {
        launch({home+"/.local/bin/rice-media", e->direction == GDK_SCROLL_UP ? "up" : "down"});
        return TRUE;
    }), nullptr);
    GtkWidget *next_label = button(spotify_box, "󰒭", [](guint){launch({home+"/.local/bin/rice-media","next"});});
    repeat_label = button(spotify_box, "󰑗", [](guint){launch({home+"/.local/bin/waybar-spotify", "--cycle-repeat"});});
    for (GtkWidget *label : {shuffle_label, prev_label, spotify_label, next_label, repeat_label}) {
        gtk_widget_set_margin_start(label, 9);
        gtk_widget_set_margin_end(label, 9);
        gtk_widget_set_margin_top(label, 0);
        gtk_widget_set_margin_bottom(label, 0);
        gtk_widget_set_name(gtk_widget_get_parent(label), "rice-media-button");
        gtk_widget_set_name(label, "rice-media-icon");
    }
    // Shuffle and repeat are secondary toggles, so they sit at two-thirds
    // the size of the three transport glyphs.
    for (GtkWidget *label : {shuffle_label, repeat_label})
        gtk_widget_set_name(label, "rice-media-icon-small");
    GtkWidget *spacer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0); gtk_box_pack_start(GTK_BOX(body), spacer, TRUE, TRUE, 0);
    GtkWidget *right = group(body, "rice-group-right");
    button(right, "󰨞", [](guint b){
        if (b == 2) launch({home+"/.local/bin/vscode-menu", "folder"});
        else if (b == 3) launch({home+"/.local/bin/vscode-menu", "focus"});
        else launch({home+"/.local/bin/vscode-menu"});
    }, "VS Code");
    button(right, "", [](guint){launch({"kitty"});}, "Terminal");
    button(right, "", [](guint){launch({"thunar"});}, "Files");
    display_label = button(right, "", [](guint){launch({home+"/.local/bin/desktop-panel", "display"});}, "Displays");
    bluetooth_label = button(right, "", [](guint){launch({home+"/.local/bin/desktop-menu", "bluetooth"});}, "Bluetooth");
    network_label = button(right, "󰖪", [](guint){launch({home+"/.local/bin/desktop-menu","network"});}, "Networks");
    battery_label = button(right, "", [](guint){}, "Battery");
    button(right, "", [](guint){launch({home+"/.local/bin/control-menu"});}, "Settings");
    button(right, "", [](guint){launch({home+"/.local/bin/power-click"});}, "Power");
    gtk_container_foreach(GTK_CONTAINER(right), +[](GtkWidget *event, gpointer) {
        GtkWidget *label = gtk_bin_get_child(GTK_BIN(event));
        if (GTK_IS_LABEL(label)) gtk_widget_set_margin_end(label, 8);
    }, nullptr);
    GtkWidget *center = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 2);
    gtk_widget_set_name(center, "rice-group-center"); gtk_widget_set_halign(center, GTK_ALIGN_CENTER); gtk_widget_set_valign(center, GTK_ALIGN_CENTER);
    gtk_widget_set_size_request(center, -1, 31);
    gtk_overlay_add_overlay(GTK_OVERLAY(overlay), center);
    for (int i=0; i<6; i++) {
        workspaces[i] = gtk_event_box_new();
        gtk_widget_set_name(workspaces[i], "workspace-idle");
        GtkWidget *label = gtk_label_new(std::to_string(i+1).c_str());
        gtk_container_add(GTK_CONTAINER(workspaces[i]), label);
        gtk_widget_set_size_request(workspaces[i], 39, 22);
        gtk_widget_set_margin_top(label, 3);
        gtk_widget_set_margin_bottom(label, 3);
        g_object_set_data(G_OBJECT(workspaces[i]), "workspace", GINT_TO_POINTER(i+1));
        g_signal_connect(workspaces[i], "button-press-event", G_CALLBACK(+[](GtkWidget *w, GdkEventButton*, gpointer) -> gboolean {
            // Hyprland >=0.56 evaluates dispatchers as Lua; plain
            // "workspace N" fails there, "hl.dsp.focus" works.
            launch({"hyprctl", "dispatch",
                    "hl.dsp.focus({workspace=" + std::to_string(GPOINTER_TO_INT(g_object_get_data(G_OBJECT(w), "workspace"))) + "})"}); return TRUE;
        }), nullptr);
        gtk_box_pack_start(GTK_BOX(center), workspaces[i], FALSE, FALSE, 0);
    }
    gtk_widget_show_all(window);
    gtk_widget_hide(workspaces[5]);
    apply_palette();
    std::thread(watch_status).detach();
    std::thread(watch_workspaces).detach();
    // Updating the clock does not need to wait for slower status commands.
    auto update_clock = +[](gpointer data) -> gboolean {
        time_t now=time(nullptr); char buffer[64], tip[96];
        bool twelve = clock_12h();
        tm *local = localtime(&now);
        strftime(buffer,sizeof(buffer),twelve ? "  %I:%M:%S" : "  %H:%M:%S",local);
        std::string label = buffer;
        if (twelve) label += local->tm_hour < 12 ? " AM" : " PM";
        strftime(tip,sizeof(tip),"%A, %d %B %Y",localtime(&now));
        gtk_label_set_width_chars(GTK_LABEL(data),twelve ? 12 : 8);
        gtk_label_set_text(GTK_LABEL(data),label.c_str());
        gtk_widget_set_tooltip_text(gtk_widget_get_parent(GTK_WIDGET(data)),tip);
        return G_SOURCE_CONTINUE;
    };
    update_clock(clock);
    g_timeout_add_seconds(1, update_clock, clock);
    // Atomic palette replacements wake the bar immediately; polling covers a
    // monitor failure without making normal wallpaper changes wait five seconds.
    GFile *palette_dir = g_file_new_for_path((home + "/.local/state/rice").c_str());
    GFileMonitor *palette_watch = g_file_monitor_directory(palette_dir, G_FILE_MONITOR_NONE, nullptr, nullptr);
    if (palette_watch) g_signal_connect(palette_watch, "changed",
        G_CALLBACK(+[](GFileMonitor*, GFile *file, GFile *other, GFileMonitorEvent, gpointer) {
            gchar *name = file ? g_file_get_basename(file) : nullptr;
            gchar *next = other ? g_file_get_basename(other) : nullptr;
            bool changed = (name && strcmp(name, "palette.json") == 0) ||
                           (next && strcmp(next, "palette.json") == 0);
            g_free(name); g_free(next);
            if (changed) apply_palette();
        }), nullptr);
    g_timeout_add_seconds(5, +[](gpointer) -> gboolean { apply_palette(); return G_SOURCE_CONTINUE; }, nullptr);
    gtk_main();
    if (palette_watch) g_object_unref(palette_watch);
    g_object_unref(palette_dir);
    g_object_unref(theme_provider);
    return 0;
}
