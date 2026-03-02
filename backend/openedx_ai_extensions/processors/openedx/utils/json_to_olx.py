"""
Utility for converting a problem definition dictionary into OLX (XML) format.
"""
from jinja2 import Template

olx_template = Template("""
  <problem display_name="{{ p.display_name }}">
    <div>{{ p.question_html }}</div>

    {% if p.problem_type in ['multiplechoiceresponse', 'choiceresponse'] %}
    <{{ p.problem_type }}>
        <{% if p.problem_type == 'multiplechoiceresponse' %}choicegroup{% else %}checkboxgroup{% endif %}>
            {% for choice in p.choices %}
            <choice correct="{{ 'true' if choice.is_correct else 'false' }}">
                <div>{{ choice.text }}</div>
                {% if choice.feedback %}
                <choicehint>
                    <div>{{ choice.feedback }}</div>
                </choicehint>
                {% endif %}
            </choice>
            {% endfor %}
        </{% if p.problem_type == 'multiplechoiceresponse' %}choicegroup{% else %}checkboxgroup{% endif %}>
    </{{ p.problem_type }}>

    {% elif p.problem_type == 'optionresponse' %}
    <optionresponse>
        <optioninput>
            {% for choice in p.choices %}
            <option correct="{{ 'true' if choice.is_correct else 'false' }}">
                {{ choice.text }}
                <optionhint>
                    <div>{{ choice.feedback }}</div>
                </optionhint>
            </option>
            {% endfor %}
        </optioninput>
    </optionresponse>

    {% elif p.problem_type == 'numericalresponse' %}
    <numericalresponse answer="{{ p.answer_value }}">
        {% if p.tolerance and p.tolerance != '<UNKNOWN>' %}
        <responseparam type="tolerance" default="{{ p.tolerance }}" />
        {% endif %}
        <formulaequationinput />
    </numericalresponse>

    {% elif p.problem_type == 'stringresponse' %}
    <stringresponse answer="{{ p.answer_value }}" type="ci">
        <label>{{ p.question_html }}</label>
        <textline size="20" />
    </stringresponse>
    {% endif %}

    <solution>
        <div class="detailed-solution">
            <p>Explanation</p>
            <p>{{ p.explanation }}</p>
        </div>
    </solution>

    {% if p.demand_hints %}
    <demandhint>
        {% for hint in p.demand_hints %}
        <hint>
            <div>{{ hint }}</div>
        </hint>
        {% endfor %}
    </demandhint>
    {% endif %}
  </problem>
  """)


def json_to_olx(problem_dict):
    # Render the template with the dictionary
    rendered = olx_template.render(p=problem_dict)
    return {"category": "problem", "data": rendered}
