```
    ___                            _
o  /   \                          | | o
     __/      __,    _    _       | |     , _|_
|      \-----/  |  |/ \_|/ \_-----|/  |  / \_|
|_/\___/     \_/|_/|__/ |__/      |__/|_/ \/ |_/
------------------/|---/|-----------------------
                  \|   \|
```

# What
Add glyphs for each application to the workspace name.  
The glyph for the currently focused application is highlighted.  
Workspaces can still be renamed - these are displayed along with the app glyphs.  
  
![screenshot](demo/screenshot.png)


# Why
I use a lot of workspaces, and it becomes hard to keep track of what's going on in each one.  
Naming each one is time-consuming, and having fixed workspaces for each task is too inflexible.  

# How
We use window class and instance names, titles, etc to form rules to identify applications.  
For example, we choose the `browser` glyph if the window class is any of "Firefox", "Google-chrome", or "qutebrowser".
```python
    def is_browser(app):
        return app.class_ in ("Firefox", "Google-chrome", "qutebrowser")
```

# Installation
* Clone this repo
* `cd <path-to-repo>`
* Install dependencies with `pip3 install -r requirements.txt`
* `cd src`
* Run with `python3 i3_app_list.py`
* To add custom names, simple rename the workspace (with `i3-msg 'rename workspace to "custom name"'`)
    - use a keybind and get input through `i3-input`, `dmenu`, `rofi` or equivalent
        - example: `i3-msg "rename workspace to \"$(echo | dmenu)\""`
    - to remove the custom name, repeat the above with whitespace as custom name
        - `i3-msg 'rename workspace to " "'`
    - one small caveat: the custom name cannot:
        1. be equal to `<num>`
        2. start with `<num><sep>`  
        (where `<num>` is the workspace number and `<sep>` is the separator  
            \[`parts.separator` in [settings.yaml](src/settings.yaml)\])

# Support
The list of supported applications is always growing, mostly as I start using something new.  
Currently supported applications:
* download managers
    * uget
* browsers
    * firefox
    * google chrome
    * qutebrowser
    * tor
* pdf viewers
    * okular
    * zathura
    * foxit
* virtual machines
    * virtual box
    * vmware
* media players
    * vlc
    * mplayer
* wireshark
* terminals
    * gnome terminal
    * urxvt
    * xterm
    * st
* file browsers
    * nautilus
* image viewers
    * pinta
    * pqiv
    * feh
    * eog
* fontforge
* office applications
    * libreoffice
* text editors
    * gvim
    * gedit
* android studio
* skype
* ida
* steam
* burp suite
* gephi  
* zeal
  
If something you use is not on this list (which is very probable), see [extending](#extending).

# Extending
Adding support for new applications is extremely straightforward. 
Most cases are extremely simple, and you can do it without any knowledge of python.  
Steps: (for application `example`)
* Run `python3 i3_app_list.py -l`
    * This prints a list of all running applications, each with their name, class, and instance.
    * Locate the ones for `example` - say, `example_name`, `example_class`, and `example_instance`
* Add a function in [app_definition.py](src/app_definition.py) under the class `AppDefinition`.
```python
        def is_example(app):
            return app.class_ == "example_class"  # simplest, most common case
```
* Add a glyph in [settings.yaml](src/settings.yaml)
```yaml
        glyphs:
            example: Ex
```

# Customization
Settings are listed in [settings.yaml](src/settings.yaml).  
Each glyph is a unicode string, so using Nerdfonts or similar allows for a lot of options.  
Glyphs can be customized for each application.  
In addition, you can choose colors and separators.  
