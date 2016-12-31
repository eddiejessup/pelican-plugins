"""
Notebook Tag
------------
This is a liquid-style tag to include a static html rendering of an IPython
notebook in a blog post.

Syntax
------
{% notebook filename.ipynb [ cells[start:end] language[language] ]%}

The file should be specified relative to the ``notebooks`` subdirectory of the
content directory.  Optionally, this subdirectory can be specified in the
config file:

    NOTEBOOK_DIR = 'notebooks'

The cells[start:end] statement is optional, and can be used to specify which
block of cells from the notebook to include.
"""
import re
import os
from os.path import dirname, realpath, join
from functools import partial
from copy import deepcopy
import subprocess

from nbconvert.filters.highlight import _pygments_highlight
from nbconvert.exporters import HTMLExporter
from nbconvert.preprocessors import Preprocessor
from traitlets.config import Config
from traitlets import Integer
import nbformat
from pygments.formatters import HtmlFormatter

from .mdx_liquid_tags import LiquidTags


this_file_dir_path = dirname(realpath(__file__))
# Some styles that will be added to the header.
CSS_INCLUDE = open(join(this_file_dir_path, 'css_include.css')).read()
# Some code that will be added to the header.
JS_INCLUDE = open(join(this_file_dir_path, 'js_include.html')).read()

WRAPPER_ID = 'nb-wrapper'

CSS_WRAPPER = """
<style type="text/css">
{0}
</style>
"""


# Create a custom preprocessor
class SliceIndex(Integer):

    """An integer trait that accepts None"""
    default_value = None

    def validate(self, obj, value):
        if value is None:
            return value
        else:
            return super(SliceIndex, self).validate(obj, value)


class SubCell(Preprocessor):

    """A transformer to select a slice of the cells of a notebook"""
    start = SliceIndex(0, config=True,
                       help="first cell of notebook to be converted")
    end = SliceIndex(None, config=True,
                     help="last cell of notebook to be converted")

    def preprocess(self, nb, resources):
        nbc = deepcopy(nb)
        nbc.cells = nbc.cells[self.start:self.end]
        return nbc, resources


# Custom highlighter:
# Instead of using class='highlight', use class='highlight-ipynb'
def custom_highlighter(source, language='ipython', metadata=None):
    formatter = HtmlFormatter(cssclass='highlight-ipynb')
    if not language:
        language = 'ipython'
    output = _pygments_highlight(source, formatter, language)
    return output.replace('<pre>', '<pre class="ipynb">')


# Below is the pelican plugin code.
SYNTAX = "{% notebook /path/to/notebook.ipynb [ cells[start:end] ] [ language[language] ] %}"
FORMAT = re.compile(r"""^(\s+)?(?P<src>\S+)(\s+)?((cells\[)(?P<start>-?[0-9]*):(?P<end>-?[0-9]*)(\]))?(\s+)?((language\[)(?P<language>-?[a-z0-9\+\-]*)(\]))?(\s+)?$""")


@LiquidTags.register('notebook')
def notebook(preprocessor, tag, markup):
    match = FORMAT.search(markup)
    if match:
        argdict = match.groupdict()
        src = argdict['src']
        start = argdict['start']
        end = argdict['end']
        language = argdict['language']
    else:
        raise ValueError("Error processing input, "
                         "expected syntax: {0}".format(SYNTAX))

    if start:
        start = int(start)
    else:
        start = 0

    if end:
        end = int(end)
    else:
        end = None

    language_applied_highlighter = partial(
        custom_highlighter, language=language)

    nb_dir = preprocessor.configs.getConfig('NOTEBOOK_DIR')
    nb_path = join('content', nb_dir, src)

    if not os.path.exists(nb_path):
        raise ValueError("File {0} could not be found".format(nb_path))

    # Create the custom notebook converter
    c = Config({'CSSHTMLHeaderTransformer':
                {'enabled': True, 'highlight_class': '.highlight-ipynb'},
                'SubCell':
                    {'enabled': True, 'start': start, 'end': end}})

    exporter = HTMLExporter(config=c,
                            template_path=[this_file_dir_path],
                            template_file='pelican_basic',
                            filters={
                                'highlight2html': language_applied_highlighter
                            },
                            preprocessors=[SubCell])

    # Read and parse the notebook.
    with open(nb_path) as f:
        nb_text = f.read()
        nb_json = nbformat.reads(nb_text, as_version=4)

    # Render the notebook into HTML.
    (body, resources) = exporter.from_notebook_node(nb_json)

    # Combine all the CSS styles into one string.
    resource_css = '\n'.join(resources['inlining']['css'] + [CSS_INCLUDE])
    # Wrap CSS into LESS syntax which says that all styles should be scoped to
    # apply within a particular 'div' element, which will surround the notebook
    # body. This is to stop the styling affecting the overall theme.
    css_as_less = 'div#' + WRAPPER_ID + ' { ' + resource_css + ' }'
    # Use the LESS compiler to compile the LESS into equivalent CSS.
    # Basically it prefixes all the existing selectors with 'div#foo [...]'.

    def run(args):
        return subprocess.run(args, stdout=subprocess.PIPE, input=css_as_less,
                              universal_newlines=True)
    less_args = ["lessc", "-", "--clean-css"]
    process = run(less_args)
    # If this doesn't work, try without clean-css plugin.
    if process.returncode != 0:
        less_args.pop()
        process = run(less_args)
    if process.returncode != 0 or not process.stdout:
        raise Exception('Failed to process notebook CSS. Is less installed?'
                        'Specifically, can you run "lessc --version"?')
    scoped_css = CSS_WRAPPER.format(process.stdout)

    augmented_body = '\n'.join([scoped_css, body, JS_INCLUDE])
    # Stash special characters so that they won't be transformed
    # by subsequent processes.
    stashed_body = preprocessor.configs.htmlStash.store(augmented_body,
                                                        safe=True)
    return stashed_body

# Allow notebook to be a Pelican plugin.
from .liquid_tags import register
