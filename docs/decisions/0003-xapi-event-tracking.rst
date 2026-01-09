0002 Dynamic workflow configuration
###################################

Status
******
**Provisional**


Context
*******

The Open edX AI Extensions plugin introduces AI-powered workflows (summarization, chat, question generation). To support learning analytics and institutional visibility, these interactions must be tracked in a way compatible with Open edX Aspects, which consumes xAPI events via event-routing-backends (ERB).

Different AI workflows exhibit different interaction patterns (one-shot vs. conversational), which require distinct analytics semantics.

Decision
********

AI workflow executions will emit xAPI-compliant events using the Open edX platform’s existing eventtracking and event-routing-backends infrastructure.

* Events are emitted via `eventtracking.tracker.emit()` and transformed to xAPI by ERB when Aspects is installed.
* Direct dependencies on `eventtracking` and `event-routing-backends` are used (no `edxapp_wrapper` abstraction).
* Three xAPI verbs are used to reflect workflow patterns:

  * **completed** for one-shot workflows
  * **initialized** for the start of conversational workflows
  * **interacted** for subsequent conversational turns
* A custom Open edX–namespaced activity type is introduced:

  * `https://w3id.org/xapi/openedx/activity/ai-workflow`
* Workflow metadata (action, location, etc.) is attached via Open edX–namespaced xAPI extensions.
* Events are dynamically allowlisted in ERB via plugin settings.

Consequences
************

* AI workflow usage becomes visible in Aspects alongside other learning events.
* Analytics can distinguish between discrete and conversational AI interactions.
* Events are standards-based (xAPI) and compatible with external analytics tools.
* In environments without Aspects, events are emitted but not transformed to xAPI unless the operators install and configure event-routing-backends themselves.

Rejected Alternatives
*********************

**Single generic workflow event**

* **Pros:** Simpler implementation
* **Cons:** Loses semantic meaning and complicates analytics

**Using edxapp_wrapper**

* **Pros:** Consistency with legacy patterns
* **Cons:** Unnecessary abstraction for external packages

### References

---

* [https://github.com/openedx/event-routing-backends](https://github.com/openedx/event-routing-backends)
* [https://docs.openedx.org/projects/openedx-aspects/en/latest/](https://docs.openedx.org/projects/openedx-aspects/en/latest/)
* [https://github.com/open-craft/openedx-completion-aggregator/pull/205](https://github.com/open-craft/openedx-completion-aggregator/pull/205)
