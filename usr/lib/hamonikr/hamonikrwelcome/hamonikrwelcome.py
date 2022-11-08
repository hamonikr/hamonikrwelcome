#!/usr/bin/python3
import apt
import gettext
import gi
import os
import platform
import subprocess
import locale
import cairo
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf

NORUN_FLAG = os.path.expanduser("~/.hamonikr/hamonikrwelcome/norun.flag")

# i18n
gettext.install("hamonikrwelcome", "/usr/share/hamonikr/locale")
from locale import gettext as _
locale.bindtextdomain("hamonikrwelcome", "/usr/share/hamonikr/locale")
locale.textdomain("hamonikrwelcome")

LAYOUT_STYLE_LEGACY, LAYOUT_STYLE_NEW = range(2)

class SidebarRow(Gtk.ListBoxRow):

    def __init__(self, page_widget, page_name, icon_name):
        Gtk.ListBoxRow.__init__(self)
        self.page_widget = page_widget
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_border_width(6)
        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        box.pack_start(image, False, False, 0)
        label = Gtk.Label()
        label.set_text(page_name)
        box.pack_start(label, False, False, 0)
        self.add(box)

class HamonikrWelcome():

    def __init__(self):
        builder = Gtk.Builder()
        builder.set_translation_domain("hamonikrwelcome")
        builder.add_from_file('/usr/share/hamonikr/hamonikrwelcome/hamonikrwelcome.ui')

        window = builder.get_object("main_window")
        window.set_icon_name("hamonikrwelcome")
        window.set_position(Gtk.WindowPosition.CENTER)
        window.connect("destroy", Gtk.main_quit)

        with open("/etc/hamonikr/info") as f:
            config = dict([line.strip().split("=") for line in f])
        codename = config['CODENAME'].capitalize()
        edition = config['EDITION'].replace('"', '')
        release = config['RELEASE']
        desktop = config['DESKTOP']
        release_notes = config['RELEASE_NOTES_URL']
        new_features = config['NEW_FEATURES_URL']
        architecture = "64-bit"

        # distro-specific
        dist_name = "HamoniKR"

        # Setup the labels in the Mint badge
        builder.get_object("label_version").set_text("%s %s" % (dist_name, release))
        builder.get_object("label_edition").set_text("%s %s" % (edition, architecture))

        # Setup the main stack
        self.stack = Gtk.Stack()
        builder.get_object("center_box").pack_start(self.stack, True, True, 0)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        # Action buttons
        builder.get_object("button_forums").connect("clicked", self.visit, "https://hamonikr.org")
        builder.get_object("button_documentation").connect("clicked", self.visit, "https://docs.hamonikr.org/hamonikr-6.0/")
        builder.get_object("button_contribute").connect("clicked", self.visit, "https://github.com/hamonikr")
        builder.get_object("button_irc").connect("clicked", self.visit, "https://hamonikr.slack.com/")
        builder.get_object("button_codecs").connect("clicked", self.visit, "apt://mint-meta-codecs?refresh=yes")
        builder.get_object("button_new_features").connect("clicked", self.visit, new_features)
        builder.get_object("button_release_notes").connect("clicked", self.visit, release_notes)
        builder.get_object("button_mintupdate").connect("clicked", self.launch, "mintupdate")
        builder.get_object("button_mintinstall").connect("clicked", self.launch, "mintinstall")
        builder.get_object("button_timeshift").connect("clicked", self.pkexec, "timeshift-gtk")
        builder.get_object("button_mintdrivers").connect("clicked", self.pkexec, "driver-manager")
        builder.get_object("button_gufw").connect("clicked", self.launch, "gufw")
        builder.get_object("button_layout_legacy").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_LEGACY)
        builder.get_object("button_layout_new").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_NEW)

        # Custom Second Step (recommended software)
        builder.get_object("button_hancom").connect("clicked", self.pkexec, "/usr/share/hamonikr/hamonikrwelcome/scripts/hoffice-install")
        builder.get_object("button_kakaotalk").connect("clicked", self.pkexec, "/usr/share/hamonikr/hamonikrwelcome/scripts/kakaotalk-install")
        builder.get_object("button_site_compatibility_support").connect("clicked", self.pkexec, "/usr/share/hamonikr/hamonikrwelcome/scripts/site-compatibility-support")
        builder.get_object("button_kodi").connect("clicked", self.pkexec, "/usr/share/hamonikr/hamonikrwelcome/scripts/kodi-install")
        builder.get_object("button_korean_language").connect("clicked", self.on_button_korean_language)
        
        # Custom Third Step (development software)
            # Development Language
        builder.get_object("button_default_jdk").connect("clicked", self.visit, "apt://default-jdk?refresh=yes")
        builder.get_object("button_python_pip").connect("clicked", self.visit, "apt://python3-pip?refresh=yes")
            # WEB/WAS
        builder.get_object("button_apache").connect("clicked", self.visit, "apt://apache2?refresh=yes")
        builder.get_object("button_tomcat").connect("clicked", self.visit, "apt://tomcat9?refresh=yes")
            # Editor (IDE)
        builder.get_object("button_vscode").connect("clicked", self.pkexec, "/usr/share/hamonikr/hamonikrwelcome/scripts/vscode-install")
            # DBMS
        builder.get_object("button_mysql").connect("clicked", self.visit, "apt://mysql-server?refresh=yes")
        builder.get_object("button_postgresql").connect("clicked", self.visit, "apt://postgresql?refresh=yes")
            # etc
        builder.get_object("button_asbru").connect("clicked", self.visit, "apt://asbru-cm?refresh=yes")
        builder.get_object("button_git").connect("clicked", self.visit, "apt://git?refresh=yes")
        builder.get_object("button_rabbitvcs").connect("clicked", self.visit, "apt://hamonikr-nemo-rabbitvcs?refresh=yes")
        builder.get_object("button_avahi").connect("clicked", self.visit, "apt://hamonikr-avahi-service?refresh=yes")

        # Settings button depends on DE
        de_is_cinnamon = False
        self.theme = None
        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            builder.get_object("button_settings").connect("clicked", self.launch, "cinnamon-settings")
            de_is_cinnamon = True
            self.theme = Gio.Settings(schema="org.cinnamon.desktop.interface").get_string("gtk-theme")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            builder.get_object("button_settings").connect("clicked", self.launch, "mate-control-center")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            builder.get_object("button_settings").connect("clicked", self.launch, "xfce4-settings-manager")
        else:
            # Hide settings
            builder.get_object("box_first_steps").remove(builder.get_object("box_settings"))

        # Hide Desktop colors
        builder.get_object("box_first_steps").remove(builder.get_object("box_colors"))

        # Hide Cinnamon layout settings in other DEs
        if not de_is_cinnamon:
            builder.get_object("box_first_steps").remove(builder.get_object("box_cinnamon"))

        # Hide codecs box if they're already installed
        cache = apt.Cache()
        if "mint-meta-codecs" in cache and cache["mint-meta-codecs"].is_installed:
            builder.get_object("box_first_steps").remove(builder.get_object("box_codecs"))

        # Hide drivers if mintdrivers is absent (LMDE)
        if not os.path.exists("/usr/bin/mintdrivers"):
            builder.get_object("box_first_steps").remove(builder.get_object("box_drivers"))

        # Hide new features page for LMDE
        if dist_name == "LMDE":
            builder.get_object("box_documentation").remove(builder.get_object("box_new_features"))

        # Construct the stack switcher
        list_box = builder.get_object("list_navigation")

        page = builder.get_object("page_home")
        self.stack.add_named(page, "page_home")
        list_box.add(SidebarRow(page, _("Welcome"), "go-home-symbolic"))
        self.stack.set_visible_child(page)

        page = builder.get_object("page_first_steps")
        self.stack.add_named(page, "page_first_steps")
        list_box.add(SidebarRow(page, _("First Steps"), "dialog-information-symbolic"))

        page = builder.get_object("page_second_steps")
        self.stack.add_named(page, "page_second_steps")
        list_box.add(SidebarRow(page, _("Second Steps"), "dialog-information-symbolic"))

        page = builder.get_object("page_third_steps")
        self.stack.add_named(page, "page_third_steps")
        list_box.add(SidebarRow(page, _("Third Steps"), "dialog-information-symbolic"))

        page = builder.get_object("page_documentation")
        self.stack.add_named(page, "page_documentation")
        list_box.add(SidebarRow(page, _("Documentation"), "accessories-dictionary-symbolic"))

        page = builder.get_object("page_help")
        self.stack.add_named(page, "page_help")
        list_box.add(SidebarRow(page, _("Help"), "help-browser-symbolic"))

        page = builder.get_object("page_contribute")
        self.stack.add_named(page, "page_contribute")
        list_box.add(SidebarRow(page, _("Contribute"), "starred-symbolic"))

        list_box.connect("row-activated", self.sidebar_row_selected_cb)

        # Construct the bottom toolbar
        box = builder.get_object("toolbar_bottom")
        checkbox = Gtk.CheckButton()
        checkbox.set_label(_("Show this dialog at startup"))
        if not os.path.exists(NORUN_FLAG):
            checkbox.set_active(True)
        checkbox.connect("toggled", self.on_button_toggled)
        box.pack_end(checkbox)

        scale = window.get_scale_factor()

        self.all_colors = ["green", "aqua", "blue", "brown", "grey", "orange", "pink", "purple", "red", "sand", "teal"]
        self.init_color_info()  # Sets self.dark_mode and self.color based on current system configuration

        # Use HIDPI pictures if appropriate
        if scale == 1:
            surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/legacy.png", scale)
            builder.get_object("img_legacy").set_from_surface(surface)
            surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/modern.png", scale)
            builder.get_object("img_modern").set_from_surface(surface)
        else:
            # Desktop theme image is too large to use.
            # surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/legacy-hidpi.png", scale)
            surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/legacy.png", scale)
            builder.get_object("img_legacy").set_from_surface(surface)
            # surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/modern-hidpi.png", scale)
            surface = self.surface_for_path("/usr/share/hamonikr/hamonikrwelcome/modern.png", scale)
            builder.get_object("img_modern").set_from_surface(surface)

        path = "/usr/share/hamonikr/hamonikrwelcome/colors/"
        if scale == 2:
            path = "/usr/share/hamonikr/hamonikrwelcome/colors/hidpi/"
        for color in self.all_colors:
            builder.get_object("img_" + color).set_from_surface(self.surface_for_path("%s/%s.png" % (path, color), scale))
            builder.get_object("button_" + color).connect("clicked", self.on_color_button_clicked, color)

        builder.get_object("switch_dark").set_active(self.dark_mode)
        builder.get_object("switch_dark").connect("state-set", self.on_dark_mode_changed)

        window.set_default_size(800, 500)
        window.show_all()

    def surface_for_path(self, path, scale):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

        return Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale)

    def sidebar_row_selected_cb(self, list_box, row):
        self.stack.set_visible_child(row.page_widget)

    def on_button_toggled(self, button):
        if button.get_active():
            if os.path.exists(NORUN_FLAG):
                os.system("rm -rf %s" % NORUN_FLAG)
        else:
            os.system("mkdir -p ~/.hamonikr/hamonikrwelcome")
            os.system("touch %s" % NORUN_FLAG)

    def on_button_layout_clicked (self, button, style):
        # HamoniKR themes change
        if style == LAYOUT_STYLE_LEGACY:
            os.system("hamonikr-theme-setting restore && hamonikr-theme-setting winstyle")
        elif style == LAYOUT_STYLE_NEW:
            os.system("hamonikr-theme-setting restore && sleep 1 && hamonikr-theme-setting macstyle")
        os.system("cinnamon --replace &")

    def on_dark_mode_changed(self, button, state):
        self.dark_mode = state
        self.change_color()

    def on_color_button_clicked(self, button, color):
        self.color = color
        self.change_color()

    def change_color(self):
        theme = "Mint-Y"
        wm_theme = "Mint-Y"
        cinnamon_theme = "Mint-Y-Dark"
        if self.dark_mode:
            theme = "%s-Dark" % theme
        if self.color != "green":
            theme = "%s-%s" % (theme, self.color.title())
            cinnamon_theme = "Mint-Y-Dark-%s" % self.color.title()

        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            settings = Gio.Settings(schema="org.cinnamon.desktop.interface")
            settings.set_string("gtk-theme", theme)
            settings.set_string("icon-theme", theme)
            Gio.Settings(schema="org.cinnamon.desktop.wm.preferences").set_string("theme", wm_theme)
            Gio.Settings(schema="org.cinnamon.theme").set_string("name", cinnamon_theme)
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            settings = Gio.Settings(schema="org.mate.interface")
            settings.set_string("gtk-theme", theme)
            settings.set_string("icon-theme", theme)
            Gio.Settings(schema="org.mate.Marco.general").set_string("theme", wm_theme)
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            subprocess.call(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", theme])
            subprocess.call(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-s", theme])
            subprocess.call(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", theme])

    def init_color_info(self):
        theme = "Mint-Y"
        dark_theme = "Mint-Y-Dark"
        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            setting = Gio.Settings(schema="org.cinnamon.desktop.interface").get_string("gtk-theme")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            setting = Gio.Settings(schema="org.mate.interface").get_string("gtk-theme")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            setting = subprocess.check_output(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"]).decode("utf-8").strip()
        
        if setting.startswith(theme):
            self.dark_mode = setting.startswith(dark_theme)
            if self.dark_mode:
                setting = setting.replace(dark_theme, "")
            else:
                setting = setting.replace(theme, "")
            if len(setting) <= 1:
                self.color = "green"
            else:
                self.color = setting[1:].lower()
                if not self.color in self.all_colors:  # Assume green if our color is invalid
                    self.color = "green"
        else:
            self.init_default_color_info()  # Bail out if we aren't working with a Mint-Y theme or the theme is unknown
    
    def init_default_color_info(self):
        self.color = "green"
        self.dark_mode = False

    def visit(self, button, url):
        subprocess.Popen(["xdg-open", url])

    def launch(self, button, command):
        subprocess.Popen([command])

    def pkexec(self, button, command):
        subprocess.Popen(["pkexec", command])

    def on_button_korean_language (self, button):
        os.system("sh -c /usr/share/hamonikr/hamonikrwelcome/scripts/kodi_korean_support")

if __name__ == "__main__":
    HamonikrWelcome()
    Gtk.main()
