'''
Auto discover classes derived from given base class
'''
import sys
import imp
import inspect


def discover_classes_in_module(mod, baseclass):
    """Return tuple of classes defined in given module that are derived from given
    base class"""
    classtypes = [m[1] for m in inspect.getmembers(mod, inspect.isclass)]
    return tuple(filter(lambda ct: ct != baseclass and issubclass(ct, baseclass), classtypes))


def discover_classes(modpath, baseclass):
    """Return tuple of classes defined in given package/module that are derived from given
    base class. Path is complete dotted package/module path."""
    searchdirs = sys.path
    modpaths = modpath.split(".")
    path = []
    while modpaths:
        modname = modpaths.pop(0)
        fp, pathname, description = imp.find_module(modname, searchdirs)
        try:
            path += [modname]
            m = imp.load_module(".".join(path), fp, pathname, description)
            if description[-1] == imp.PKG_DIRECTORY:
                searchdirs = m.__path__
        finally:
            if fp: fp.close()
    return discover_classes_in_module(m, baseclass)
