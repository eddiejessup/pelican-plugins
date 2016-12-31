from pelican import signals
from .mdx_liquid_tags import LiquidTags, LT_CONFIG


def addLiquidTags(gen):
    settings = gen.settings

    # Use the markdown configuration dict, the current method, if it exists.
    if 'MARKDOWN' in settings:
        markdown_conf = settings['MARKDOWN']
        # Get the extensions list, or make it if it does not exist.
        ext_list = markdown_conf.setdefault('extensions', [])
    # If user has set 'MD_EXTENSIONS', use that, even though it is deprecated.
    elif 'MD_EXTENSIONS' in settings:
        ext_list = settings['MD_EXTENSIONS']
    # Otherwise, make a configuration to add to.
    else:
        ext_list = []
        settings['MARKDOWN'] = {'extensions': ext_list}
    if LiquidTags not in ext_list:
        configs = LT_CONFIG.copy()
        for k in gen.settings:
            if k in configs:
                configs[k] = gen.settings[k]
        # Instantiate extension and append it to the current extensions.
        ext_list.append(LiquidTags(configs))


def register():
    signals.initialized.connect(addLiquidTags)
