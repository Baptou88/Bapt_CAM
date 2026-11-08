def getProperty(obj, prop):
    """getProperty(obj, prop) ... answer obj's property defined by its canonical name."""
    o, attr, name = _getProperty(obj, prop)
    return attr


def _getProperty(obj, prop):
    o = obj
    attr = obj
    name = None
    for name in prop.split("."):
        o = attr
        if not hasattr(o, name):
            break
        attr = getattr(o, name)

    if o == attr:
        # Path.Log.debug(translate("PathGui", "%s has no property %s (%s)") % (obj.Label, prop, name))
        return (None, None, None)

    # Path.Log.debug("found property %s of %s (%s: %s)" % (prop, obj.Label, name, attr))
    # App.Console.PrintMessage(f'found property {prop} of {obj.Label} ({name}: {attr})\n')
    return (o, attr, name)
