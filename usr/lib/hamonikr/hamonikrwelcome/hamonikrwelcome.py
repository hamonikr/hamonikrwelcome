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
        user_guide_url = config['USER_GUIDE_URL']
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
        builder.get_object("button_documentation").connect("clicked", self.visit, user_guide_url)
        builder.get_object("button_contribute").connect("clicked", self.visit, "https://github.com/hamonikr")
        builder.get_object("button_irc").connect("clicked", self.visit, "https://hamonikr.slack.com/")
        builder.get_object("button_new_features").connect("clicked", self.visit, new_features)
        builder.get_object("button_release_notes").connect("clicked", self.visit, release_notes)
        builder.get_object("button_layout_legacy").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_LEGACY)
        builder.get_object("button_layout_new").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_NEW)

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

        # Hide Cinnamon layout settings in other DEs
        if not de_is_cinnamon:
            builder.get_object("box_first_steps").remove(builder.get_object("box_cinnamon"))

        # Construct the stack switcher
        list_box = builder.get_object("list_navigation")

        page = builder.get_object("page_home")
        self.stack.add_named(page, "page_home")
        list_box.add(SidebarRow(page, _("Welcome"), "go-home-symbolic"))
        self.stack.set_visible_child(page)

        page = builder.get_object("page_first_steps")
        self.stack.add_named(page, "page_first_steps")
        list_box.add(SidebarRow(page, _("First Steps"), "dialog-information-symbolic"))

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
            os.system("rm ~/.hamonikr/theme/hamonikr-theme-setting.done && hamonikr-theme-setting winstyle")
        elif style == LAYOUT_STYLE_NEW:
            os.system("rm ~/.hamonikr/theme/hamonikr-theme-setting.done && hamonikr-theme-setting macstyle")
        os.system("cinnamon --replace &")
    
    def visit(self, button, url):
        subprocess.Popen(["xdg-open", url])

    def launch(self, button, command):
        subprocess.Popen([command])

    def pkexec(self, button, command):
        subprocess.Popen(["pkexec", command])

if __name__ == "__main__":
    HamonikrWelcome()
    Gtk.main()
