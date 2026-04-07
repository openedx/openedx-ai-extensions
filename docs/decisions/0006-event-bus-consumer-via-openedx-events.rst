0006 Event Bus Consumer Integration via openedx-events
#######################################################

Status
******

**Provisional**


Context
*******

``openedx-ai-extensions`` exposes AI orchestration workflows that can be triggered
by different elements of the UI and also from pluggable extensions. Work is underway
to make it trigger from xblocks. Up to now, triggering an orchestration run required
a direct Python API call—coupling the calling code to the internal structure of this
package.

We want a decoupled, standards-compliant mechanism so that:

* Any plugin or service can request an AI orchestration run without importing internal
  modules of ``openedx-ai-extensions``.
* The same handler can be invoked both **in-process** (direct Django signal, same LMS/CMS
  worker) and **cross-service** (via the Open edX Event Bus, e.g. Redis Streams).
* The integration follows the `openedx-events
  <https://github.com/openedx/openedx-events>`_ contract so it is consistent with the
  rest of the platform event infrastructure.


Decision
********

``openedx-ai-extensions`` owns and publishes an ``OpenEdxPublicSignal`` that any
consumer can fire to trigger an AI orchestration run.

.. note::

   The signal is defined in this repository as a pragmatic starting point.
   The **long-term intent** is to move ``AI_ORCHESTRATION_REQUESTED`` (and its
   accompanying data class) to the `openedx-events
   <https://github.com/openedx/openedx-events>`_ repository, so that any package
   wishing to *send* the event does not need to take a dependency on
   ``openedx-ai-extensions`` itself.  Until that migration happens, callers must
   import from ``openedx_ai_extensions.events``.

Signal definition
-----------------

A new ``events`` sub-package is introduced inside ``openedx_ai_extensions``:

.. code-block:: text

    openedx_ai_extensions/
    ├── events/
    │   ├── __init__.py
    │   ├── data.py      ← attr data-class for the event payload
    │   └── signals.py   ← OpenEdxPublicSignal declaration

**Data class** (``events/data.py``):

.. code-block:: python

    @attr.s(frozen=True)
    class AIOrchestrationRequestData:
        user_id             = attr.ib(type=int)
        course_id           = attr.ib(type=str,  default=None)
        location_id         = attr.ib(type=str,  default=None)
        ui_slot_selector_id = attr.ib(type=str,  default=None)
        user_input          = attr.ib(type=dict, factory=attr.Factory(dict))
        action              = attr.ib(type=str,  default="run")

**Signal** (``events/signals.py``):

.. code-block:: python

    AI_ORCHESTRATION_REQUESTED = OpenEdxPublicSignal(
        event_type="org.openedx.ai_extensions.orchestration.requested.v1",
        data={"ai_orchestration_request": AIOrchestrationRequestData},
    )

How a caller fires the event
----------------------------

Any application that wants to trigger an AI orchestration run imports only the
public signal and data class—no internal ``openedx-ai-extensions`` modules:

.. code-block:: python

    from openedx_ai_extensions.events.signals import AI_ORCHESTRATION_REQUESTED
    from openedx_ai_extensions.events.data import AIOrchestrationRequestData

    AI_ORCHESTRATION_REQUESTED.send_event(
        ai_orchestration_request=AIOrchestrationRequestData(
            course_id="course-v1:edunext+01+2025",
            ui_slot_selector_id="BADGES_GENERATOR_VIA_EVENT_BUS",
            user_id=4,
        )
    )

Signal receiver
---------------

A new ``receivers.py`` module inside ``openedx_ai_extensions`` subscribes to the
signal using Django's ``@receiver`` decorator.  The receiver follows the same
context-scoping process used elsewhere in the package: it builds a context dict
from the event payload, passes it to ``AIWorkflowScope.get_profile()`` to resolve
the matching workflow profile, and then calls ``execute()`` on the result:

.. code-block:: python

    @receiver(AI_ORCHESTRATION_REQUESTED)
    def handle_ai_orchestration_requested(sender, ai_orchestration_request, **kwargs):
        user = User.objects.get(id=ai_orchestration_request.user_id)
        context = {
            "course_id": ai_orchestration_request.course_id,
            "location_id": ai_orchestration_request.location_id,
            "ui_slot_selector_id": ai_orchestration_request.ui_slot_selector_id,
        }

        workflow = AIWorkflowScope.get_profile(**context)
        workflow.execute(
            user_input=ai_orchestration_request.user_input,
            action=ai_orchestration_request.action,
            user=user,
            running_context=context,
        )

The receiver is registered by importing ``openedx_ai_extensions.receivers`` inside
``OpenedxAIExtensionsConfig.ready()``:

.. code-block:: python

    def ready(self):
        import openedx_ai_extensions.receivers  # noqa: F401

Event Bus consumer configuration
---------------------------------

The event bus consumer settings are **not active by default**.  To enable them,
set the following flag in your environment (e.g. in ``lms.env.yml`` or a Tutor
plugin):

.. code-block:: python

    AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER = True

When that flag is present and ``True``, ``plugin_settings`` injects the necessary
configuration so that the Open edX platform's event bus worker picks up the signal
automatically:

.. code-block:: python

    settings.EVENT_BUS_CONSUMER = "edx_event_bus_redis.RedisEventConsumer"
    settings.EVENT_BUS_CONSUMER_CONFIG = {
        "org.openedx.ai_extensions.orchestration.requested.v1": {
            "ai-orchestration-requests": {
                "group_id": "ai-extensions-orchestrator",
                "enabled": True,
            }
        }
    }

Dependency
----------

``openedx-events`` is added as an explicit dependency in ``requirements/base.in``
(it was previously an implicit transitive dependency through ``event-tracking``).

Files changed
*************

The following files are introduced or modified as part of this decision (shipped in a
separate implementation PR):

+--------------------------------------------------------------+----------------------------------------------+
| File                                                         | Change                                       |
+==============================================================+==============================================+
| ``backend/openedx_ai_extensions/events/data.py``             | New – ``AIOrchestrationRequestData`` attr    |
|                                                              | data-class                                   |
+--------------------------------------------------------------+----------------------------------------------+
| ``backend/openedx_ai_extensions/events/signals.py``          | New – ``AI_ORCHESTRATION_REQUESTED`` signal  |
+--------------------------------------------------------------+----------------------------------------------+
| ``backend/openedx_ai_extensions/receivers.py``               | New – ``handle_ai_orchestration_requested``  |
|                                                              | Django receiver                              |
+--------------------------------------------------------------+----------------------------------------------+
| ``backend/openedx_ai_extensions/settings/common.py``         | Modified – add ``EVENT_BUS_CONSUMER`` and    |
|                                                              | ``EVENT_BUS_CONSUMER_CONFIG`` settings       |
+--------------------------------------------------------------+----------------------------------------------+

Consequences
************

* Any plugin in the same Django process (e.g. ``openedx-ai-badges``) can trigger AI
  orchestration with a single ``send_event()`` call without coupling itself to internal
  APIs.
* The same receiver is transparently invoked when the event arrives over the Redis
  event bus, enabling cross-service triggering without any additional code.
* ``openedx-ai-extensions`` is the **current owner** of the signal definition and the
  **sole consumer**; other packages only need to import the public ``events`` subpackage.
  Once the signal is migrated to ``openedx-events``, callers will no longer need a
  dependency on ``openedx-ai-extensions`` to fire the event—only this package (as the
  consumer/orchestrator) will retain that dependency.
* The chosen event type ``org.openedx.ai_extensions.orchestration.requested.v1``
  follows the Open edX event naming convention and is versioned from the start.
* Operators who do not need cross-service triggering can leave
  ``EVENT_BUS_CONSUMER_CONFIG`` disabled; in-process signals work without any
  message broker.

References
**********

* `openedx-events documentation <https://docs.openedx.org/projects/openedx-events/>`_
* `openedx-events signal-defining how-to
  <https://docs.openedx.org/projects/openedx-events/en/latest/how-tos/using-events.html>`_
* `edx-event-bus-redis <https://github.com/openedx/event-bus-redis>`_
* `OEP-41 – Asynchronous Server Event Message Format
  <https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0041-arch-async-server-event-messaging.html>`_
