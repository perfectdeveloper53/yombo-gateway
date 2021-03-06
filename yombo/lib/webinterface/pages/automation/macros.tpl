{% macro display_trigger_device(rule) %}
{%- set device_id = rule.data['trigger']['device_machine_label'] %}
{%- set device = _devices[device_id] %}
<strong>Trigger type:</strong> Device<br>
<strong>Monitored device:</strong>
{{ device.full_label}}<br>
{%- endmacro %}

{% macro display_trigger_scene(rule) %}
<strong>Trigger type:</strong> Scene<br>
<strong>Monitored scene:</strong> {{rule.data['trigger']['name']}}<br>
<strong>Scene action:</strong> {{rule.data['trigger']['actions']}}<br>
{%- endmacro %}

{% macro display_trigger_state(rule) %}
<strong>Trigger type:</strong> State<br>
<strong>Monitored state name:</strong>
{{rule.data['trigger']['name']}}<br>
<strong>Monitored state value:</strong>
{{rule.data['trigger']['value']}}<br>
<strong>Monitored state value type:</strong>
{{rule.data['trigger']['value_type']}}<br>
<strong>Monitored state gateway source:</strong>
{{_gateways[rule.data['trigger']['gateway_id']].label}}<br>
{%- endmacro %}

{% macro display_trigger_template(rule) %}
<strong>Trigger type:</strong> Template<br>
{{rule.data['trigger']['template']}}<br>
{%- endmacro %}


{% macro display_action_device(rule, action_id, action) %}
<tr class="highlight-device">
<td>
  <strong>Device:</strong>
  {% set device = _devices.get(action['device_machine_label']) -%}
  {% set command = _commands[action['command_machine_label']] -%}
  {{device.full_label}}<br>
  <strong>Command:</strong>
  {{command.label}}<br>
</td>
<td> {{action['weight']}} </td>
<td>
  <strong>Inputs:</strong><br>
  {%- set available_commands = device.available_commands() -%}
  {%- set inputs = available_commands[command.command_id]['inputs'] -%}
  {% if action['inputs']|length == 0 %}No inputs
  {%- else -%}
  {%- for input_id, value in action['inputs'].items() -%}
  <i>{{ inputs[input_id]['label'] }}:</i> {{value}} <br>
  {%- endfor -%}
  {%- endif -%}
</td>
<td>
{% set links = _automation.action_types['device'] %}
{{edit_action_link(links, rule.rule_id, action_id)}}
{{delete_action_link(links, rule.rule_id, action_id)}}
{{up_action_link(links, rule.rule_id, action_id)}}
{{down_action_link(links, rule.rule_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_action_pause(rule, action_id, action) %}
<tr class="highlight-pause">
<td> <strong>Pause</strong></td>
<td> {{action['weight']}} </td>
<td>
  <strong>Duration:</strong><br> {{action['duration']}} seconds<br>
</td>
<td>
{% set links = _automation.action_types['pause'] %}
{{edit_action_link(links, rule.rule_id, action_id)}}
{{delete_action_link(links, rule.rule_id, action_id)}}
{{up_action_link(links, rule.rule_id, action_id)}}
{{down_action_link(links, rule.rule_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_action_scene(rule, action_id, action) %}
<tr class="highlight-scene">
<td> <strong>Scene:</strong> {{_scenes[action['scene_machine_label']].label}}</td>
<td> {{action['weight']}} </td>
<td>
  <strong>Action:</strong><br> {{action['scene_action']}}<br>
</td>
<td>
{% set links = _automation.action_types['scene'] %}
{{edit_action_link(links, rule.rule_id, action_id)}}
{{delete_action_link(links, rule.rule_id, action_id)}}
{{up_action_link(links, rule.rule_id, action_id)}}
{{down_action_link(links, rule.rule_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_action_state(rule, action_id, action) %}
<tr class="highlight-state">
<td> <strong>State:</strong> {{action['name']}}</td>
<td> {{action['weight']}} </td>
<td>
  <strong>Set Value:</strong><br> {{action['value']}}<br>
</td>
<td>
{% set links = _automation.action_types['state'] %}
{{edit_action_link(links, rule.rule_id, action_id)}}
{{delete_action_link(links, rule.rule_id, action_id)}}
{{up_action_link(links, rule.rule_id, action_id)}}
{{down_action_link(links, rule.rule_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_action_template(rule, action_id, action) %}
{% set links = _automation.action_types['state'] %}
<tr class="highlight-template">
<td> <strong>Template</strong></td>
<td> {{action['weight']}} </td>
<td>
  <strong>Description:</strong><br> {{action['description']}}<br>
</td>
<td>
{% set links = _automation.action_types['template'] %}
{{edit_action_link(links, rule.rule_id, action_id)}}
{{delete_action_link(links, rule.rule_id, action_id)}}
{{up_action_link(links, rule.rule_id, action_id)}}
{{down_action_link(links, rule.rule_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro filter_url(url, rule_id, action_id) %}
{{url|replace("{rule_id}", rule_id)|replace('{action_id}', action_id)}}
{%- endmacro %}

{% macro edit_action_link(links, rule_id, action_id) %}
<a href="{{filter_url(links['edit_url'],rule_id,action_id)}}" title="Edit action"><i class="fas fa-pencil-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro delete_action_link(links, rule_id, action_id) %}
<a href="{{filter_url(links['delete_url'],rule_id,action_id)}}" title="Delete action"><i class="fas fa-trash-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro up_action_link(links, rule_id, action_id) %}
<a href="{{filter_url(links['up_url'],rule_id,action_id)}}" title="Move up"><i class="fas fa-arrow-up fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro down_action_link(links, rule_id, action_id) %}
<a href="{{filter_url(links['down_url'],rule_id,action_id)}}" title="Move down"><i class="fas fa-arrow-down fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}
