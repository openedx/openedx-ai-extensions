0004 Expose AI Extensions as an XBlock Service
###############################################

Status
******
**Accepted**


Context
*******

The ``openedx-ai-extensions`` framework provides a rich set of abstractions for
AI-powered educational workflows:

* **Orchestrators** (``BaseOrchestrator``, ``SessionBasedOrchestrator``, …) —
  coordinate full AI workflows with session management and async Celery execution.
* **``AIWorkflowScope.execute()``** — the single entry-point that resolves the
  best-matching scope for a given course/location and delegates to the configured
  orchestrator.
* **``AIWorkflowSession``** — persists conversation state across requests.
* **Processors** (``LLMProcessor``, ``OpenEdXProcessor``, …) — lower-level
  abstractions for LLM calls and content extraction.

XBlock developers who want to leverage this infrastructure (e.g. to generate
AI hints, summaries, or tutoring dialogs inside an XBlock) currently have no
clean integration path.  Their options today are:

1. **Import the Django app directly** — violates XBlock's isolation model,
   creates a hard Django dependency, and breaks portability to the XBlock SDK
   test runner.
2. **Duplicate LLM call logic** — loses provider configuration and all future
   framework improvements.
3. **Call the REST API over HTTP** — unnecessary same-process network round
   trip and requires auth-token management inside the XBlock.

The XBlock specification defines a **services** mechanism precisely to solve
this class of problem.  An XBlock declares the services it needs with
``@XBlock.needs('service_name')`` or ``@XBlock.wants('service_name')`` and the
platform runtime injects them via ``self.runtime.service(self, 'service_name')``.
This pattern is already used for ``i18n``, ``user``, ``submissions`` (ORA2), and
others.

**The Extensibility Gap**

While edx-platform natively supports injecting services into the XBlock runtime
(e.g. in ``LmsModuleSystem`` and ``StudioModuleSystem``), it currently lacks a
dynamic hook or entry-point system (like ``openedx_filters``) to allow
independent plugins to register new services during runtime instantiation.
Native services are hardcoded into the platform's core dictionaries.  This
forces external plugins to find alternative ways to inject their services into
the XBlock lifecycle without modifying edx-platform core.


Decision
********

We introduce a new module ``openedx_ai_extensions.xblock_service`` that exposes
the AI Extensions framework to XBlocks through the standard XBlock services
mechanism under the name ``"ai_extensions"``.

**Service class — ``AIExtensionsXBlockService``**

A thin façade instantiated by the runtime with the current user and
course/location context.  The initial implementation exposes a single
stateless method:

.. code-block:: python

    def call_llm(
        self,
        prompt: str,
        context: str = None,
        user_input: str = None,
        extra_params: dict = None,
    ) -> dict:
        """
        Single, stateless LLM call via LLMProcessor.
        Returns: {response, tokens_used, model_used, status}
        On failure: {status: "error", error: "..."}
        """

This covers the most common XBlock use-case (one-off generation such as hints,
summaries, or feedback) without requiring session management or a configured
``AIWorkflowScope``.

**Service registration**

Because Open edX does not provide a dynamic registration API for XBlock runtime
services, we inject our service at the base runtime level to ensure availability
across the LMS, CMS, and XBlock SDK Workbench.

We apply a controlled monkey-patch to ``xblock.runtime.Runtime.service``,
executed exactly once during Django startup inside
``OpenedxAIExtensionsConfig.ready()``:

.. code-block:: python

    # openedx_ai_extensions/xblock_service/mixin.py
    def patch_runtime():
        import xblock.runtime as xblock_runtime
        original_service = xblock_runtime.Runtime.service

        def _patched_service(runtime_self, block, service_name):
            if service_name == "ai_extensions":
                return _build_service(runtime_self, block)
            return original_service(runtime_self, block, service_name)

        xblock_runtime.Runtime.service = _patched_service

The patch is idempotent and non-breaking: only the ``"ai_extensions"`` name is
intercepted; all other service names are forwarded to the original method.
``_build_service`` constructs an ``AIExtensionsXBlockService`` from the runtime
context (user, course_id, location_id) and returns ``None`` on any error,
honouring the ``@XBlock.wants`` contract.

The ``xblock_service`` package also exports:

.. code-block:: python

    SERVICE_NAME = "ai_extensions"

    def get_service_class():
        from .service import AIExtensionsXBlockService
        return AIExtensionsXBlockService


**Why this approach?**

* **Universal coverage** — patching the base ``Runtime`` class is the only
  plugin-safe approach that works across all Open edX runtime variants
  (``ModuleSystem``, ``XBlockRuntime``, ``WorkbenchRuntime``) simultaneously.
* **Idempotent & non-destructive** — the patch is strictly scoped to intercept
  only the ``"ai_extensions"`` key; all other service requests fall back
  immediately to the original ``xblock.runtime.Runtime.service`` method,
  ensuring zero disruption to native platform services.
* **Plugin isolation** — allows ``openedx-ai-extensions`` to remain a pure
  Open edX App Plugin without requiring forks or upstream core modifications
  to edx-platform.

**XBlock usage example**

.. code-block:: python

    from xblock.core import XBlock
    from xblock.fields import String, Scope

    @XBlock.wants("ai_extensions")   # wants = graceful degradation when absent
    class AITutorXBlock(XBlock):

        system_prompt = String(scope=Scope.content, default="You are a helpful tutor.")

        @XBlock.json_handler
        def ask_ai(self, data, suffix=""):
            ai = self.runtime.service(self, "ai_extensions")
            if ai is None:
                return {"error": "AI service not available in this environment"}

            return ai.call_llm(
                prompt=self.system_prompt,
                user_input=data.get("question", ""),
            )

Consequences
************

* XBlock developers get a **clean, zero-import API** to LLM capabilities
  without depending on any ``openedx_ai_extensions`` symbol directly.
* XBlocks using ``@XBlock.wants`` degrade gracefully when the service is absent
  (e.g. in the XBlock SDK test runner), keeping them portable.
* The service carries ``user``, ``course_id``, and ``location_id`` context
  extracted automatically from the runtime — the XBlock provides only
  ``prompt`` and ``user_input``.
* Streaming responses are not supported in the synchronous ``call_llm`` path.
* The following scope-level methods are **not yet implemented** and are
  deferred to a future iteration:

  * ``execute_workflow(ui_slot_selector_id, user_input, action)`` — resolves an
    ``AIWorkflowScope`` for the block's course/location and runs the full
    orchestrator pipeline, including session management.
  * ``get_workflow_status(ui_slot_selector_id)`` — polls the status of an async
    Celery-backed workflow started with ``action="run_async"``.
  * ``clear_workflow_session(ui_slot_selector_id)`` — deletes the
    ``AIWorkflowSession`` for the current user and scope.

  These methods will be added to ``AIExtensionsXBlockService`` without breaking
  existing XBlocks that already use ``call_llm``.


Rejected Alternatives
*********************

**HTTP calls to the existing REST API (``/openedx-ai-extensions/api/v1/workflows/``)**

* **Pros:** Zero coupling at the Python level.
* **Cons:** Unnecessary same-process round trip; requires the XBlock to manage
  auth tokens; cannot reuse the server-side request context.

**Direct Django app import inside the XBlock**

* **Pros:** Full access to every internal API.
* **Cons:** Breaks XBlock portability and isolation; creates a hard dependency
  on the Django app being installed; incompatible with the XBlock SDK test
  runner.

**Django signals as a request/response bus**

* **Pros:** Fully decoupled.
* **Cons:** No clean synchronous return-value mechanism; difficult to handle
  errors; poor developer experience.


**Upstream PR to edx-platform to register the service natively**

* **Pros:** Architecturally pure; eliminates the need for monkey-patching.
* **Cons:** Couples the release cycle of this framework to Open edX named
  releases. It requires modifying ``lms/djangoapps/lms_xblock/runtime.py``
  and its CMS equivalent, delaying availability of the AI service for
  instances running older but supported versions of Open edX.  The patching
  approach keeps the plugin independently installable and
  backwards-compatible.

References
**********

* XBlock services documentation — https://docs.openedx.org/projects/xblock/en/latest/xblock-tutorial/overview/introduction.html
* XBlock repository — https://github.com/openedx/XBlock
* ORA2 service usage example — https://github.com/openedx/edx-ora2/blob/eef8b0f3e0b7a38915543f925dd92e99830093c0/openassessment/xblock/apis/ora_config_api.py#L120
* ``LLMProcessor`` — ``openedx_ai_extensions/processors/``
* ``patch_runtime()`` — ``openedx_ai_extensions/xblock_service/mixin.py``
* ``AIExtensionsXBlockService`` — ``openedx_ai_extensions/xblock_service/service.py``
