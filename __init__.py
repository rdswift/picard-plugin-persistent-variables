# -*- coding: utf-8 -*-
#
# Copyright (C) 2022, 2025 Bob Swift (rdswift)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

# "Persistent variables display" context is based on the code from
# the "View Script Variables" plugin.

from PyQt6 import QtWidgets

from picard.plugin3.api import (
    Album,
    BaseAction,
    File,
    PluginApi,
    Track,
    t_,
)
from picard.script.parser import normalize_tagname
from picard.util import iter_files_from_objects
from picard.util.webbrowser2 import open as open_url

from .ui_persistent_variables_dialog import (
    Ui_PersistentVariablesDialog,
)


USER_GUIDE_URL = "https://picard-plugins-user-guides.readthedocs.io/en/latest/persistent_variables/user_guide.html"


class PersistentVariables:
    album_variables = {}
    session_variables = {}

    @classmethod
    def clear_album_vars(cls, album):
        if album:
            cls.album_variables[album] = {}

    @classmethod
    def set_album_var(cls, album, key, value):
        if album:
            if album not in cls.album_variables:
                cls.clear_album_vars(album)
            if key:
                cls.album_variables[album][key] = value

    @classmethod
    def unset_album_var(cls, album, key):
        if album and album in cls.album_variables:
            cls.album_variables[album].pop(key, None)

    @classmethod
    def unset_album_dict(cls, album):
        if album:
            cls.album_variables.pop(album, None)

    @classmethod
    def get_album_var(cls, album, key):
        if album in cls.album_variables:
            return cls.album_variables[album][key] if key in cls.album_variables[album] else ""
        return ""

    @classmethod
    def clear_session_vars(cls):
        cls.session_variables = {}

    @classmethod
    def set_session_var(cls, key, value):
        if key:
            cls.session_variables[key] = value

    @classmethod
    def unset_session_var(cls, key):
        cls.session_variables.pop(key, None)

    @classmethod
    def get_session_var(cls, key):
        return cls.session_variables[key] if key in cls.session_variables else ""

    @classmethod
    def get_album_dict(cls, album):
        if album and album in cls.album_variables:
            return cls.album_variables[album]
        return {}

    @classmethod
    def get_session_dict(cls):
        return cls.session_variables


class ApiHelper:
    """Helper class to provide access to the PluginApi instance."""
    _api = None

    @classmethod
    def set_api(cls, api: PluginApi):
        cls._api = api

    @classmethod
    def get_api(cls) -> PluginApi:
        return cls._api


def _get_album_id(parser):
    file = parser.file
    if file:
        if file.parent and hasattr(file.parent, 'album') and file.parent.album:
            return str(file.parent.album.id)
        else:
            return ""
    # Fall back to parser context to allow processing on albums newly retrieved from MusicBrainz
    return parser.context['musicbrainz_albumid']


def func_set_s(parser, name, value):
    if value:
        PersistentVariables.set_session_var(normalize_tagname(name), value)
    else:
        func_unset_s(parser, name)
    return ""


def func_unset_s(parser, name):
    PersistentVariables.unset_session_var(normalize_tagname(name))
    return ""


def func_get_s(parser, name):
    return PersistentVariables.get_session_var(normalize_tagname(name))


def func_clear_s(parser):
    PersistentVariables.clear_session_vars()
    return ""


def func_unset_a(parser, name):
    album_id = _get_album_id(parser)
    ApiHelper.get_api().logger.debug("Unsetting album '%s' variable '%s'", album_id, normalize_tagname(name))
    if album_id:
        PersistentVariables.unset_album_var(album_id, normalize_tagname(name))
    return ""


def func_set_a(parser, name, value):
    album_id = _get_album_id(parser)
    ApiHelper.get_api().logger.debug("Setting album '%s' persistent variable '%s' to '%s'", album_id, normalize_tagname(name), value)
    if album_id:
        PersistentVariables.set_album_var(album_id, normalize_tagname(name), value)
    return ""


def func_get_a(parser, name):
    album_id = _get_album_id(parser)
    ApiHelper.get_api().logger.debug("Getting album '%s' persistent variable '%s'", album_id, normalize_tagname(name))
    if album_id:
        return PersistentVariables.get_album_var(album_id, normalize_tagname(name))
    return ""


def func_clear_a(parser):
    album_id = _get_album_id(parser)
    ApiHelper.get_api().logger.debug("Clearing album '%s' persistent variables dictionary", album_id)
    if album_id:
        PersistentVariables.clear_album_vars(album_id)
    return ""


def initialize_album_dict(api: PluginApi, album, album_metadata, release_metadata):
    album_id = str(album.id)
    api.logger.debug("Initializing album '%s' persistent variables dictionary", album_id)
    PersistentVariables.clear_album_vars(album_id)


def destroy_album_dict(api: PluginApi, album):
    album_id = str(album.id)
    api.logger.debug("Destroying album '%s' persistent variables dictionary", album_id)
    PersistentVariables.unset_album_dict(album_id)


class ViewPersistentVariables(BaseAction):

    TITLE = t_("action.title", "View persistent variables")

    def callback(self, objs):
        obj = objs[0]
        files = list(iter_files_from_objects(objs))
        if files:
            obj = files[0]
        dialog = ViewPersistentVariablesDialog(obj, api=self.api)
        dialog.exec()


class ViewPersistentVariablesDialog(QtWidgets.QDialog):

    def __init__(self, obj, parent=None, api: PluginApi = None):
        super().__init__(parent=parent)
        self.api = api
        self.ui = Ui_PersistentVariablesDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.buttonBox.helpRequested.connect(self.show_help)
        self.album_id = ""

        if isinstance(obj, Album):
            self.album_id = str(obj.id)
        if isinstance(obj, File):
            if obj.parent and hasattr(obj.parent, 'album') and obj.parent.album:
                self.album_id = str(obj.parent.album.id)
        elif isinstance(obj, Track):
            if obj.album:
                self.album_id = str(obj.album.id)

        album_dict = PersistentVariables.get_album_dict(self.album_id)
        album_count = len(album_dict)
        session_dict = PersistentVariables.get_session_dict()
        session_count = len(session_dict)

        table = self.ui.metadata_table
        key_example, value_example = self.get_table_items(table, 0)
        self.key_flags = key_example.flags()
        self.value_flags = value_example.flags()
        table.setRowCount(album_count + session_count + 2)
        i = 0
        self.add_separator_row(table, i, self.api.tr('ui.section.album', "Album Variables"), album_count)
        i += 1
        for key in sorted(album_dict.keys()):
            key_item, value_item = self.get_table_items(table, i)
            key_item.setText(key)
            value_item.setText(album_dict[key])
            i += 1
        self.add_separator_row(table, i, self.api.tr('ui.section.session', "Session Variables"), session_count)
        i += 1
        for key in sorted(session_dict.keys()):
            key_item, value_item = self.get_table_items(table, i)
            key_item.setText(key)
            value_item.setText(session_dict[key])
            i += 1

    def add_separator_row(self, table, i, title, count):
        key_item, value_item = self.get_table_items(table, i)
        font = key_item.font()
        font.setBold(True)
        key_item.setFont(font)
        key_item.setText(title)
        value_item.setText(self.api.trn('ui.table.item_count', "{n:,} item", "{n:,} items", n=count))

    def get_table_items(self, table, i):
        key_item = table.item(i, 0)
        value_item = table.item(i, 1)
        if not key_item:
            key_item = QtWidgets.QTableWidgetItem()
            key_item.setFlags(self.key_flags)
            table.setItem(i, 0, key_item)
        if not value_item:
            value_item = QtWidgets.QTableWidgetItem()
            value_item.setFlags(self.value_flags)
            table.setItem(i, 1, value_item)
        return key_item, value_item

    def show_help(self):
        open_url(USER_GUIDE_URL)


def enable(api: PluginApi):
    """Called when plugin is enabled."""
    ApiHelper.set_api(api)

    # Register the new functions
    api.register_script_function(
        func_set_a,
        name='set_a',
        documentation=api.tr('help.set_a', "`$set_a(name,value)`\n\nSets the album variable `name` to `value`."),
    )
    api.register_script_function(
        func_unset_a,
        name='unset_a',
        documentation=api.tr('help.unset_a', "`$unset_a(name)`\n\nClears the album variable `name`."),
    )
    api.register_script_function(
        func_get_a,
        name='get_a',
        documentation=api.tr('help.get_a', "`$get_a(name)`\n\nGets the value of the album variable `name`."),
    )
    api.register_script_function(
        func_clear_a,
        name='clear_a',
        documentation=api.tr('help.clear_a', "`$clear_a()`\n\nClears all album variables for the current album."),
    )
    api.register_script_function(
        func_set_s,
        name='set_s',
        documentation=api.tr('help.set_s', "`$set_s(name,value)`\n\nSets the session variable `name` to `value`."),
    )
    api.register_script_function(
        func_unset_s,
        name='unset_s',
        documentation=api.tr('help.unset_s', "`$unset_s(name)`\n\nClears the session variable `name`."),
    )
    api.register_script_function(
        func_get_s,
        name='get_s',
        documentation=api.tr('help.get_s', "`$get_s(name)`\n\nGets the value of the session variable `name`."),
    )
    api.register_script_function(
        func_clear_s,
        name='clear_s',
        documentation=api.tr('help.clear_s', "`$clear_s()`\n\nClears all session variables."),
    )

    # Register the processers
    api.register_album_metadata_processor(initialize_album_dict)
    api.register_album_post_removal_processor(destroy_album_dict)

    # Register context actions
    api.register_file_action(ViewPersistentVariables)
    api.register_track_action(ViewPersistentVariables)
    api.register_album_action(ViewPersistentVariables)
