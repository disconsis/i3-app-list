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
from functools import partial


def color(text, fgcolor=None, bgcolor=None):
    """return text formatted with foreground and background
    color tags. does not add foreground tag if fgcolor is None.
    same for bgcolor.

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


class ValidationError(Exception):
    """exception for invalid data"""
    pass


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
    def glyph(self):
        """get a small string representation for the app.
        try to get it from the user-customized module
        :module:`app_definition`. in case of exceptions,
        simply return the `undefined` glyph.
        if `debug` is true, break the program for everything other
        than an AttributeError (since that can be caused by the config
        file not having an entry for an glyph class name referenced by
        the module :module:`app_definition`)

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


    def __str__(self):
        """return a string repr of the application, formatted
        according to user settings
        """
        color_group = self.settings.apps.focused if self.focused \
            else self.settings.apps.unfocused
        return color(self.glyph, color_group.fg, color_group.bg)


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
            self.parts.separator.str,
            self.parts.separator.fg,
            self.parts.separator.bg,
        )
        self.apps.separator = color(
            self.apps.separator.str,
            self.apps.separator.fg,
            self.apps.separator.bg,
        )
        # unmunch glyphs
        self.glyphs = self.glyphs.__dict__


class Workspace:

    """Workspace class based on top of
    :class:`i3ipc.i3ipc.WorkspaceReply`.
    """

    def __init__(self, reply, settings, i3):
        """
        :param settings: user settings
        :type settings: :class:`Settings`
        :param reply: i3 workspace reply to use for name, num, etc
        :type reply: :class:`i3ipc.i3ipc.WorkspaceReply`
        """
        self._reply = reply
        self.settings = settings
        self.i3 = i3
        self.apps = []

    def __str__(self):
        """return a string representation to be printed on workspace
        buttons.
        """
        num = str(self.num)
        apps_str = self.settings.apps.separator.join(
            str(app) for app in self.apps
        )
        return self.settings.parts.separator.join(
            filter(bool, [num, apps_str])
        )

    def __getattr__(self, attr):
        """delegate to the underlying
        :class`i3ipc.i3ipc.WorkspaceReply`'s.
        """
        return getattr(self._reply, attr)

    def output(self):
        """print workspace to bar."""
        # workspace names have to be wrapped in double quotes
        # single quotes don't work, for some reason
        self.i3.command('rename workspace "{old}" to "{new}"'.format(
            old=self.name, new=str(self)
        ))


class Tree:

    """Class for  i3 tree."""

    def __init__(self, i3, settings):
        """
        :param i3: TODO
        :param settings: TODO
        """
        super().__init__()

        self.i3 = i3
        self.settings = settings
        self.workspaces = self.get_workspaces()

    def get_apps(self):
        """get mapping of workspace numbers: apps under workspace.

        :returns: mapping of workspace number: apps
        :rtype: defaultdict
        """
        apps = [App(app, self.settings) for app in self.i3.get_tree().leaves()]
        ws_app_mapping = defaultdict(list)
        for app in apps:
            ws_app_mapping[app.workspace().num].append(app)
        return ws_app_mapping

    def get_workspaces(self):
        """get a list of workspaces in the tree initialized with
        their apps.

        :returns: list of initialized workspaces
        :rtype: list
        """
        workspaces = [
            Workspace(ws_reply, self.settings, self.i3)
            for ws_reply in self.i3.get_workspaces()
        ]
        workspace_apps = self.get_apps()
        for workspace in workspaces:
            workspace.apps = workspace_apps[workspace.num]
        return workspaces

    def output(self):
        """print tree to bar."""
        for workspace in self.workspaces:
            workspace.output()


def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--config-file", default="settings.yaml")
    group.add_argument("-l", "--list-apps", action="store_true")
    return parser.parse_args()


def rename_everything(i3, event, settings):
    tree = Tree(i3, settings)
    tree.output()


def list_applications(i3):
    for window in i3.get_tree().leaves():
        print(
            "name: {:80}\nclass: {}\ninstance: {}".format(
                window.name, window.window_class, window.window_instance
        ))
        print('---')


def run(i3, args):
    settings = Settings(args.config_file)
    rename_everything(i3, None, settings)

    event_handler = partial(rename_everything, settings=settings)
    i3.on('workspace::focus', event_handler)
    i3.on('window::focus', event_handler)
    i3.on('window::move', event_handler)
    i3.on('window::title', event_handler)
    i3.on('window::close', event_handler)
    i3.main()


def main():
    args = parse_args()
    i3 = i3ipc.Connection()
    if args.list_apps:
        list_applications(i3)
    else:
        run(i3, args)


if __name__ == "__main__":
    main()
