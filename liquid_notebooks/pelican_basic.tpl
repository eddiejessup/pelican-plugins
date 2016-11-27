{%- extends 'basic.tpl' -%}

{% block body %}

<div id="nb-wrapper">
{{ super() }}
</div>
{%- endblock body %}


{% block in_prompt -%}
{%- endblock in_prompt %}

{% block stream_stdout -%}
{%- endblock stream_stdout %}

{% block stream_stderr -%}
{%- endblock stream_stderr %}

{% block output %}
<div class="output_area">
{{ super() }}
</div>
{% endblock output %}
