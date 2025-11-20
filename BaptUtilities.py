import os
import FreeCAD as App

def get_module_path():
    '''
    Returns the current module path.
    Determines where this file is running from, so works regardless of whether
    the module is installed in the app's module directory or the user's app data folder.
    (The second overrides the first.)
    '''
    return os.path.dirname(__file__)

def getResourcesPath():
    '''
    Returns the resources path.
    '''
    return os.path.join(get_module_path(), "resources")

def getIconPath(icon: str):
    '''
    Returns the icon path.
    @param icon - icon file name
    '''
    return os.path.join(getResourcesPath(), "icons", icon)

def getPostProPath(postPro: str):
    '''
    Returns the post-processing path.
    @param postPro - post-processing file name
    '''
    return os.path.join(get_module_path(), "PostPro", postPro)

def getExamplesPath():
    '''
    Returns the examples path.
    '''
    return os.path.join(App.getUserConfigDir(), "Mod","Bapt","examples")

def getDefaultToolsDbPath():
    """Retourne le chemin par défaut de la base de données d'outils."""
    return os.path.join(App.getUserAppDataDir(), "Bapt", "tools.db")

def find_cam_project(o):
    """Remonte les parents (InList) jusqu'à trouver le CamProject."""

    visited = set()
    queue = list(o.InList)

    while queue:
        parent = queue.pop(0)
        if parent in visited:
            continue
        visited.add(parent)

        proxy = getattr(parent, "Proxy", None)

        if proxy is not None and hasattr(proxy, "Type") and proxy.Type == "CamProject":
            return parent
        if hasattr(parent, "InList"):   
            queue.extend(parent.InList)
    return None