def get_icon(app, glyphs):
    """get an icon class for the given app

    :param app: application to get an icon class name for
    :type app: :class:`i3_app_list.App`
    :returns: class name of icon for app
    :rtype: str
    """

    if app.class_ in ('Gnome-terminal', 'URxvt', 'XTerm', 'st-256color'):
        return glyphs['terminal']
