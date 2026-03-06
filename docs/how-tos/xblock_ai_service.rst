Use AI Extensions Inside an XBlock
###################################

This guide shows how to add LLM-powered interactions to an XBlock using the
``"ai_extensions"`` service provided by ``openedx-ai-extensions``.

Prerequisites
*************

* ``openedx-ai-extensions`` is installed and enabled in your Open edX
  instance (LMS and/or CMS).
* Your XBlock package is installed and listed in ``INSTALLED_APPS`` or
  discovered via entry-points.
* An LLM provider is configured in the ``openedx-ai-extensions`` settings
  (e.g. an OpenAI API key).


Step 1 — Declare the service dependency
*****************************************

Use ``@XBlock.wants`` on your XBlock class.  ``wants`` (not ``needs``) means
the XBlock degrades gracefully when the service is absent — for example, in
the XBlock SDK workbench or in a test environment.

.. code-block:: python

    from xblock.core import XBlock

    @XBlock.wants("ai_extensions")
    class MyXBlock(XBlock):
        ...


Step 2 — Add XBlock fields
***************************

Use ``Scope.content`` for author-configurable settings (editable in Studio)
and ``Scope.user_state`` for per-learner data.

.. code-block:: python

    from xblock.fields import Scope, String

    @XBlock.wants("ai_extensions")
    class MyXBlock(XBlock):

        system_prompt = String(
            display_name="System prompt",
            default="You are a helpful teaching assistant. Answer concisely.",
            scope=Scope.content,
            help="Instruction sent to the LLM before every student question.",
        )

        last_response = String(
            default="",
            scope=Scope.user_state,
            help="The most recent AI response shown to this learner.",
        )


Step 3 — Check service availability in the view
*************************************************

Retrieve the service in ``student_view`` to decide whether to show the AI
input or a fallback message.  Pass ``ai_available`` to the template as a
flag.

.. code-block:: python

    def student_view(self, context=None):
        ai_available = self.runtime.service(self, "ai_extensions") is not None

        html = self.resource_string("html/myxblock.html")
        frag = Fragment(html.format(
            self=self,
            ai_available=str(ai_available).lower(),   # "true" / "false"
        ))
        frag.add_css(self.resource_string("css/myxblock.css"))
        frag.add_javascript(self.resource_string("js/src/myxblock.js"))
        frag.initialize_js("MyXBlock")
        return frag


Step 4 — Call the LLM in a JSON handler
*****************************************

Add a ``@XBlock.json_handler`` that retrieves the service and calls
``call_llm``.  Always check that the service is not ``None`` before using it.

.. code-block:: python

    @XBlock.json_handler
    def ask_ai(self, data, suffix=""):
        """
        Expects: {"question": "<learner text>"}
        Returns: {"status": "success", "response": "<LLM text>"}
              or {"status": "error",   "error":    "<message>"}
        """
        question = (data.get("question") or "").strip()
        if not question:
            return {"status": "error", "error": "Please enter a question."}

        ai = self.runtime.service(self, "ai_extensions")
        if ai is None:
            return {
                "status": "error",
                "error": "The AI service is not available in this environment.",
            }

        result = ai.call_llm(
            prompt=self.system_prompt,   # system / instruction prompt
            user_input=question,         # learner's input
        )

        if result.get("status") == "error":
            return result

        self.last_response = result.get("response", "")
        return {"status": "success", "response": self.last_response}

``call_llm`` signature:

.. code-block:: python

    def call_llm(
        self,
        prompt: str,              # system / instruction prompt
        context: str = None,      # optional extra context (e.g. transcript)
        user_input: str = None,   # learner's input text
        extra_params: dict = None # extra LiteLLM params (model, temperature…)
    ) -> dict


Step 5 — HTML template
************************

Use the ``ai_available`` flag to show or hide the AI widget.

.. code-block:: html

    <div class="myxblock">
      {%- if ai_available == "true" %}
      <div class="ai-area">
        <textarea id="ai-question" placeholder="Ask a question…"></textarea>
        <button id="ask-btn">Ask AI</button>
        <div id="ai-response"></div>
        <div id="ai-error"  class="error"></div>
      </div>
      {%- else %}
      <p class="ai-unavailable">AI assistance is not available here.</p>
      {%- endif %}
    </div>

.. note::

   The ``html.format(self=self, ai_available=…)`` pattern in Step 3 passes
   ``ai_available`` as a plain string (``"true"`` / ``"false"``), not as a
   Jinja variable.  Adjust the template accordingly.


Step 6 — JavaScript handler
*****************************

Call the handler via the standard XBlock AJAX helper and update the DOM with
the response.

.. code-block:: javascript

    function AIXBlock(runtime, element, config) {
      var handlerUrl = runtime.handlerUrl(element, "ask_ai");

      document.getElementById("ask-btn").addEventListener("click", function () {
        var question = document.getElementById("ai-question").value.trim();
        if (!question) return;

        document.getElementById("ai-response").textContent = "Thinking…";
        document.getElementById("ai-error").textContent    = "";

        fetch(handlerUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "success") {
              document.getElementById("ai-response").textContent = data.response;
            } else {
              document.getElementById("ai-error").textContent = data.error;
              document.getElementById("ai-response").textContent = "";
            }
          });
      });
    }
