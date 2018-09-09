#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import app_definition
import i3ipc
import argparse
import yaml
import yamale
import munch
import os
from collections import defaultdict
from functools import wraps
import daemon
import logging
from logging.handlers import RotatingFileHandler
import atexit
import pprint

LOG_FILE = "/tmp/i3_app_list.log"
logger = None

# set up logger
def setup_logging():
    logging.raiseExceptions = False
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    rot_handler = RotatingFileHandler(
        LOG_FILE, backupCount=1, maxBytes=10*(1024**2),
    )
    rot_handler.setFormatter(logging.Formatter(
        "%(asctime)s: [%(levelname)s] %(message)s", "%b %d %H:%M:%S"
    ))
    logger.addHandler(rot_handler)
    logger.info("--- starting ---")
    atexit.register(lambda: logger.info("--- exiting ---"))


def color_pango(text, fgcolor=None, bgcolor=None):
    """return text formatted with pango backend with foreground and
    background color tags. does not add foreground tag if fgcolor is
    None. same for bgcolor.

    :param text: string to be colored
    :type text: str
    :param fgcolor: foreground color
    :type fgcolor: str or None
    :param bgcolor: background color
    :type bgcolor: str or None
    :returns: color tagged text
    :rtype: str
    """
    fg_tag = "foreground='{}'".format(fgcolor) \
        if fgcolor else ""
    bg_tag = "background='{}'".format(bgcolor) \
        if bgcolor else ""
    return "<span {fg} {bg}>{text}</span>".format(
        fg=fg_tag, bg=bg_tag, text=text,
    )


def color_cairo(text, fgcolor=None, bgcolor=None):
    """return text formatted with cairo backend with foreground and
    background color tags. does not add foreground tag if fgcolor is
    None. same for bgcolor.

    :param text: string to be colored
    :type text: str
    :param fgcolor: foreground color
    :type fgcolor: str or None
    :param bgcolor: background color
    :type bgcolor: str or None
    :returns: color tagged text
    :rtype: str
    """
    return "{fg_start}{bg_start}{text}{fg_end}{bg_end}".format(
        fg_start="%{{F{0}}}".format(fgcolor) if fgcolor is not None else "",
        bg_start="%{{B{0}}}".format(bgcolor) if bgcolor is not None else "",
        text=text,
        fg_end="%{F-}" if fgcolor is not None else "",
        bg_end="%{B-}" if bgcolor is not None else "",
    )


def color(backend, *args):
    return {"pango": color_pango, "cairo": color_cairo}[backend](*args)


class ValidationError(Exception):
    """exception for invalid data"""
    pass


def log_exceptions(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(
                ("{funcname}({_args}, {_kwargs}) "
                 "raised {exc_class}: {exc_msg}").format(
                     funcname=func.__name__,
                     _args=', '.join(map(repr, args)),
                     _kwargs=', '.join(map(repr, kwargs)),
                     exc_class=type(e).__name__,
                     exc_msg=e,
                 )
            )
    return wrapped


class App:

    """Application class to extend :class`i3ipc.i3ipc.Con`."""

    def __init__(self, con, settings):
        """
        :type con: :class:`i3ipc.i3ipc.Con`
        """
        assert isinstance(con, i3ipc.i3ipc.Con), \
            "con must be an instance of :class:`i3ipc.i3ipc.Con`"
        self.settings = settings
        self._con = con

    def __getattr__(self, attr):
        """delegate to the underlying :class`i3ipc.i3ipc.Con`'s
        attributes.
        """
        # `app.class_` returns `app.window_class` and
        # `app.instance_` returns `app.window_instance`
        # to make writing app definitions easier
        attr = 'window_class' if attr == 'class_' else attr
        attr = 'window_instance' if attr == 'instance_' else attr
        return getattr(self._con, attr)

    @property
    @log_exceptions
    def glyph(self):
        """get a small string representation for the app.
        try to get it from the user-customized module
        :module:`app_definition`. in case of exceptions,
        simply return the `undefined` glyph.  if `debug`
        is true, break the program (so that the dev knows
        that app definitions are broken).

        :return: repr for the app
        :rtype: str
        """
        try:
            glyph = app_definition.get_glyph(self, self.settings.glyphs)
            if glyph is not None:
                return glyph
        except Exception as e:
            if self.settings.debug is True:
                raise e

        return self.settings.glyphs.get('undefined')


    def __repr__(self):
        return "<{0}:\n{1}>".format(
            type(self).__name__,
            pprint.pformat({
                "name": self.name,
                "class_": self.class_,
                "instance_": self.instance_,
            }),
        )


    def __str__(self):
        """return a string repr of the application, formatted
        according to user settings
        """
        color_group = self.settings.apps.focused if self.focused \
            else self.settings.apps.unfocused
        return color(self.settings.backend, self.glyph, color_group.fg, color_group.bg)


class Settings:

    """class for user configuration."""

    SCHEMA_FILE = "./settings.yaml"

    def __init__(self, _file):
        """
        :param _file: file to read settins from
        :type _file: str
        """
        self._file = _file
        self.read_settings_file()
        self._create_sensible_attrs()

    @classmethod
    def validate_settings_file(cls, _file):
        """validate the structure of  the settings file. raise
        :class:`ValidationError` if found invalid.

        :param _file: settings file to validate
        :type file: str
        :raises: :class:`ValidationError`
        """
        schema = yamale.make_schema(cls.SCHEMA_FILE)
        try:
            data = yamale.make_data(_file)
            yamale.validate(schema, data)
        except (OSError, ValueError) as e:
            raise ValidationError(e)

    def read_settings_file(self):
        """parse the settings file and populate user settings.
        raise :class:`ValidationError` if found invalid.
        """
        with open(self._file) as fp:
            contents = yaml.load(fp)
        munched_dict = munch.munchify(contents)
        self.__dict__.update(**munched_dict)

    def _create_sensible_attrs(self):
        """mofify object's attrs to more sensible data strucutres"""

        # create separators from settings
        self.parts.separator = color(
            self.backend,
            self.parts.separator.str,
            self.parts.separator.fg,
            self.parts.separator.bg,
        )
        self.apps.separator = color(
            self.backend,
            self.apps.separator.str,
            self.apps.separator.fg,
            self.apps.separator.bg,
        )
        # unmunch glyphs
        self.glyphs = self.glyphs.__dict__


class Workspace:

    """Workspace class based on top of :class:`i3ipc.i3ipc.Con`."""

    def __init__(self, con, settings, i3, custom_name=None, num=None):
        """
        :param settings: user settings
        :type settings: :class:`Settings`
        :param con: i3 workspace Con to use for name, num, etc
        :type con: :class:`i3ipc.i3ipc.Con`
        :param i3: i3 connection to use
        :type i3: :class:`i3ipc.i3ipc.Connection`
        :param custom_name: custom name to use for workspace
        :type custom_name: str or None
        :param num: workspace num to set to
        :type num: int
        """
        self._con = con
        self.settings = settings
        self.i3 = i3
        self.apps = []
        if num is not None:
            self._con.num = num
        self.custom_name = custom_name

    def __str__(self):
        """return a string representation to be printed on workspace
        buttons.
        """
        num = str(self.num)
        apps_str = self.settings.apps.separator.join(
            str(app) for app in self.apps
        )
        return self.settings.parts.separator.join(
            filter(bool, [num, self.custom_name, apps_str])
        )

    def __getattr__(self, attr):
        """delegate to the underlying
        :class`i3ipc.i3ipc.Con`.
        """
        return getattr(self._con, attr)

    def output(self):
        """print workspace to bar."""
        # workspace names have to be wrapped in double quotes
        # single quotes don't work, for some reason
        new_name = str(self)
        if new_name != self.name:
            self.i3.command('rename workspace "{old}" to "{new}"'.format(
                old=self.name, new=new_name
            ))
            self.name = new_name


class Tree:

    """Class for  i3 tree."""

    def __init__(self, i3, settings, custom_names=None):
        """
        :param i3: TODO
        :param settings: TODO
        """
        super().__init__()

        self.i3 = i3
        self.settings = settings
        self.custom_names = custom_names if custom_names is not None else {}
        self.workspaces = self.get_workspaces()

    def get_apps(self):
        """get mapping of workspace numbers: apps under workspace.

        :returns: mapping of workspace number: apps
        :rtype: defaultdict
        """
        apps = [App(app, self.settings) for app in self.i3.get_tree().leaves()]
        ws_app_mapping = defaultdict(list)
        for app in apps:
            ws_app_mapping[app.workspace().id].append(app)
        return ws_app_mapping

    def get_workspaces(self):
        """get a list of workspaces in the tree initialized with
        their apps.

        :returns: list of initialized workspaces
        :rtype: list
        """
        workspaces = [
            Workspace(ws_con, self.settings, self.i3,
                      custom_name=self.custom_names.get(ws_con.id))
            for ws_con in self.i3.get_tree().workspaces()
        ]
        workspace_apps = self.get_apps()
        for workspace in workspaces:
            workspace.apps = workspace_apps[workspace.id]
        return workspaces

    def get_workspace(self, _id):
        """get a workspace from the tree which has the given id.

        :param _id: workspace id to match
        :type _id: int
        :returns: worspace from the tree which has that id, if it exists
        :rtype: :class:`Workspace` or None
        """
        for workspace in self.workspaces:
            if workspace.id == _id:
                return workspace

    def set_workspace_num(self, _id, num):
        """set the number of a workspace which has the given id.

        :param _id: workspace id to match
        :type _id: int
        :param num: what to set workspace number to
        :type num: int
        """
        self.get_workspace(_id).num = num

    def output(self):
        """print tree to bar."""
        for workspace in self.workspaces:
            workspace.output()


class Watcher:
    """Watch for i3 events and rename workspaces."""

    def __init__(self, settings):
        self.i3 = i3ipc.Connection()
        self.settings = settings
        self.tree = Tree(self.i3, self.settings)
        self.custom_names = {}
        self.subscribe()

    def subscribe(self):
        """subscribe to i3 events."""
        self.i3.on("workspace::rename", self.on_workspace_rename)
        self.i3.on("workspace::focus", self.rename_everything)
        self.i3.on("window::focus", self.rename_everything)
        self.i3.on("window::move", self.rename_everything)
        self.i3.on("window::title", self.rename_everything)
        self.i3.on("window::new", self.rename_everything)
        self.i3.on("window::close", self.rename_everything)

    def gc_custom_names(self):
        """remove records of custom names of workspaces that have
        disappeared. if we don't do this then `custom_names` will slowly
        accumulate a lot of entries for workspaces which have
        disappeared because of losing all apps.
        """
        workspace_ids = {workspace.id for workspace in self.tree.workspaces}
        for workspace_id in tuple(self.custom_names.keys()):
            if workspace_id not in workspace_ids:
                del self.custom_names[workspace_id]

    def on_workspace_rename(self, i3, event):
        """if workspace name changed externally, use it as the custom
        name for the workspace and print workspaces to bar.
        """
        event_ws = event.current
        if event_ws.name == str(event_ws.num) or \
                event_ws.name.startswith(str(event_ws.num)
                                         + self.settings.parts.separator):
            # if new name is of the form
            # "<num>" or "<num><separator>...",
            # then we assume that the change was internal
            return

        self.custom_names[event_ws.id] = event_ws.name.strip()
        # only garbage collect custom names when we add one
        self.gc_custom_names()
        # store workspace name and set it for the new tree,
        # because if a workspace name doesn't start with a
        # number, then it is set to `-1`
        workspace_num = self.tree.get_workspace(event_ws.id).num
        self.tree = Tree(self.i3, self.settings, self.custom_names)
        self.tree.set_workspace_num(event_ws.id, workspace_num)
        self.tree.output()

    def rename_everything(self, *args):
        """get a new tree and print every workspace to bar."""
        self.tree = Tree(self.i3, self.settings, self.custom_names)
        self.tree.output()

    def run(self):
        self.rename_everything()
        self.i3.main()


def parse_args():
    """parse command line arguments."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--config-file", default="settings.yaml")
    group.add_argument("-l", "--list-apps", action="store_true")
    return parser.parse_args()


def list_applications():
    """print the details of all running applications. helpful when
    writing app definitions."""
    i3 = i3ipc.Connection()
    for window in i3.get_tree().leaves():
        print(
            "name: {:80}\nclass: {}\ninstance: {}".format(
                window.name, window.window_class, window.window_instance
        ))
        print('---')


def run(args):
    """start the watcher."""
    settings = Settings(args.config_file)
    watcher = Watcher(settings)
    watcher.run()


def main():
    args = parse_args()
    if args.list_apps:
        list_applications()
    else:
        with daemon.DaemonContext(
                working_directory=os.path.dirname(os.path.abspath(__file__))):
            setup_logging()
            run(args)


if __name__ == "__main__":
    main()
