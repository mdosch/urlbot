# -*- coding: utf-8 -*-
from enum import Enum
import config
from rate_limit import RATE_GLOBAL


class ptypes(Enum):
    PARSE = 1
    COMMAND = 2
    MUC_ONLINE = 3


plugin_storage = {ptype: [] for ptype in ptypes}


def pluginfunction(name, desc, plugin_type, ratelimit_class=RATE_GLOBAL, enabled=True):
    """A decorator to make a plugin out of a function
    :param enabled:
    :param ratelimit_class:
    :param plugin_type:
    :param desc:
    :param name:
    """

    def decorate(f):
        f.is_plugin = True
        f.is_enabled = enabled
        f.plugin_name = name
        f.plugin_desc = desc
        f.plugin_type = plugin_type
        f.ratelimit_class = ratelimit_class

        plugin_storage[plugin_type].append(f)

        return f

    return decorate


# def plugin_alias(name):
#    """A decorator to add an alias to a plugin function"""
#
#    def decorate(f):
#        plugin_storage[f.plugin_type].append(f)
#        return f
#
#    return decorate


def plugin_enabled_get(urlbot_plugin):
    plugin_section = config.runtimeconf_deepget('plugins.{}'.format(urlbot_plugin.plugin_name))
    if plugin_section and "enabled" in plugin_section:
        return plugin_section.as_bool("enabled")
    else:
        return urlbot_plugin.is_enabled


@config.config_locked
def plugin_enabled_set(plugin, enabled):
    if plugin.plugin_name not in config.runtime_config_store['plugins']:
        config.runtime_config_store['plugins'][plugin.plugin_name] = {}

    config.runtime_config_store['plugins'][plugin.plugin_name]['enabled'] = enabled
    config.runtimeconf_persist()
