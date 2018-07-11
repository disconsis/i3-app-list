
def get_glyph(app, glyphs):
    """choose a glyph for the app.

    :param app: app to get glyph for
    :type app: :class:`i3_app_list.App`
    :returns: glyph for app
    :rtype: str
    """

    if app.class_ in ('Gnome-terminal', 'URxvt', 'XTerm', 'st-256color'):
        return glyphs['terminal']
