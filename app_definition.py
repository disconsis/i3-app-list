"""module for app defintions to select a glyph.

the only function this module exports is :func:`get_glyph()`,
everything else here is to facilitate user to write app definitions
with minimal boilerplate.
for anyone wishing to extend the module for their own configuration
(as you should), define your app definitions in :class:`AppDefinition`
as a function of the form `is_{app_name}`, and put an entry in your
config file under glyphs with "{app_name}: {glyph}"
"""

import inspect


def is_app_definition(f):
    return inspect.isfunction(f) and f.__name__.startswith("is_")


def get_app_name(app_def):
    return app_def.__name__[3:]


class StaticMethodMeta(type):
    """convert all methods of a deriving class into staticmethods"""
    def __init__(cls, name, bases, attrs):
        for attr in attrs.values():
            if is_app_definition(attr):
                attr = staticmethod(attr)
        super().__init__(name, bases, attrs)


class AppDefinition(metaclass=StaticMethodMeta):
    """class for app definitions.

    all the methods in this class are converted to staticmethods through
    the metaclass. functions should be of the form "is_{app_name}", and
    should return a bool, which represents whether that app name is
    correct for the app. these are used by :func:`get_glyph`.
    all such (is_{app_name}) functions should take a single argument
    (app), and can use `app.name`, `app.class_`, `app.instance_` attrs
    to get access to the app's window title, window class string, and
    window instance string, in addition to other attributes of
    `i3ipc.i3ipc.Con`.
    """

    def is_download_manager(app):
        return app.class_ == "Uget-gtk"

    def is_browser(app):
        return app.class_ in ("Firefox", "Google-chrome", "qutebrowser")

    def is_tor(app):
        return app.class_ == "Tor Browser"

    def is_ebook_reader(app):
        return app.class_ in ("Okular", "Zathura")

    def is_virtual_machine(app):
        return app.class_ in \
            ("Vmplayer", "VirtualBox", "VirtualBox Manager", "VirtualBox Machine")

    def is_media_player(app):
        return app.class_ and app.class_.lower() in ("vlc", "mplayer")

    def is_wireshark(app):
        return app.class_ == "Wireshark"

    def is_terminal(app):
        return app.class_ in ("Gnome-terminal", "URxvt", "XTerm", "st-256color")

    def is_file_browser(app):
        return app.class_ == "Nautilus"

    def is_image_viewer(app):
        return app.class_ in ("Pinta", "Pqiv", "feh", "Eog")

    def is_fontforge(app):
        return app.class_ == "fontforge"

    def is_office(app):
        return app.class_ and app.class_.startswith("libreoffice")

    def is_gvim(app):
        return app.class_ == "Gvim"

    def is_editor(app):
        return app.class_ == "Gedit"

    def is_android_studio(app):
        return app.class_ == "jetbrains-studio" \
            and app.instance_ == "sun-awt-X11-XFramePeer" \
            and "Android Studio" in app.name.split(" - ")[-1]

    def is_skype(app):
        return app.class_ == "Skype"

    def is_ida(app):
        return app.class_ == "IDA"

    def is_steam(app):
        return app.class_ == "Steam"

    def is_burp_suite(app):
        return app.name and app.name.startswith("Burp Suite")

    def is_gephi(app):
        return "Gephi" in app.class_


def get_glyph(app, glyphs):
    """choose a glyph for the app.

    find app definitions from :class:`AppDefintion` - these are the
    functions of the form `is_{app_name}`.  for each app, these are
    tried (in no particular order) and the first one that returns true
    is picked, and the glyph for that app name is chosen from `glyphs`.
    return None if no app definitions match, and the function calling
    this one chooses the glyph for "undefined".

    :param app: app to get glyph for
    :type app: :class:`i3_app_list.App`
    :param glyphs: dictionary of glyphs (app name: glyph) to use to get
        the appropriate glyph
    :type glyphs: dict
    :returns: glyph for app
    :rtype: str
    """

    app_definitions = [
        attr for attr in
        AppDefinition.__dict__.values()
        if is_app_definition(attr)
    ]
    for app_def_func in app_definitions:
        app_name = get_app_name(app_def_func)
        if app_name in glyphs and app_def_func(app):
            return glyphs.get(app_name)
