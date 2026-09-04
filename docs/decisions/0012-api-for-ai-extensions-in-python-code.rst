0012 API for AI extensions in python code
#########################################

Status
******
**Provisional**

Context
*******

Several parts of the Open edX ecosystem already want to reach for AI: the AI
coach, ``xblock-ai-evaluation``, ORA-style grading, and the badges plugin, with
more to come in the forum, in courseware, and in other plugins. Today each of
them wires its own provider call, prompt handling, storage, and error shapes.
The handful of existing "AI XBlocks" that attempt this are written on frontier
models and with time they are left behind. In terms of flexibility they in the
best cases allow users to modify the prompt, nothing beyond it.

This is a new phase for ``openedx-ai-extensions``. The project's first phase
built *new* AI surfaces and integrations for the platform (see :doc:`0001-purpose-of-this-repo`).
This phase is about **connecting the capabilities the framework already provides
into existing platform code**, reaching the forum, XBlocks, and other plugins,
rather than adding more new surfaces of its own.

Two distinct questions have emerged, and conflating them muddies both:

- **What** AI capability we expose to consumers, and the goals behind that
  surface.
- **How** that capability reaches consumers in code, and the goals behind that
  mechanism.

The second question is a direct continuation of :doc:`0005-xblock-ai-service-registration`,
which surveyed ways to expose an ``"ai_extensions"`` XBlock runtime service,
found that every viable option required upstream platform changes, and deferred
the decision to a community discussion, now underway at
`Plugin-provided XBlock runtime services <https://discuss.openedx.org/t/plugin-provided-xblock-runtime-services/18682>`_.
This ADR records the goals for **both** questions so subsequent design and review
can be measured against them, and so the community conversation has a concrete
position to react to. It deliberately treats them as two separate decisions.

We expose an API at all because the alternative is the status quo: every
consumer re-implementing the same provider calls, prompt plumbing, storage, and
analytics, with no shared place for an operator to govern which model runs, with
which prompt, or whether AI runs at all. A single surface lets us give consumers
real AI capability without each reinventing it, put the operator in control, and
move the ecosystem past the prompt-only AI XBlocks toward something extensible.

Decision
********

We will define and maintain a single public Python API, the ``api.py`` module,
as the supported surface for AI capabilities, and we will deliver it through a
light/heavy package split plus a low-coupling extension point. The specifics are
recorded below as two separate decisions.

Decision A: The API surface
============================

The ``api.py`` module is the one supported entry point. It exposes:

- a single **principal call** to run an AI profile and get back a typed result,
  with an explicit, separate call for asynchronous execution;
- a typed **result envelope** carrying status, payload, metadata, and session
  reference;
- a small set of plain, serializable **value objects** describing *where* and
  *for whom* a call happens;
- a **profile** concept, with good defaults declared in code and operator
  overrides applied from the database;
- a side-effect-free **pre-check** to ask "is this usable here?" without running
  anything;
- **streamlined session access** so consumers can read and write conversation
  state without handling storage internals;
- the **orchestrator and processor base classes** as the sanctioned way to add
  behavior.

The engine (the LLM router and its processor stack), the persistence backend,
and the scope-resolution internals are deliberately **not** part of this surface.

We commit to the following goals for that surface:

A1. **One stable, supported surface.** Consumers depend on ``api.py`` and
nothing else, so internals stay free to change without a coordinated migration
for every plugin that uses AI.

A2. **Predictable, typed, schema-shaped results.** Callers never receive raw,
unstatused LLM text or have to shape-sniff a dict. Every result states what
happened, and the easy path ("just give me the text") stays easy. A consumer can
hand a schema and get a response guaranteed to match it; knowing the shape
they will get back is a first-class ergonomic (streaming is the one case that
needs its own treatment). Failure modes such as not configured or not installed are
acceptable as long as they are predictable and documented, so downstream code
can plan for them rather than be surprised by an exception.

A3. **Operator authority is structural.** The operator running the platform,
not the developer writing the consumer, has final say over model and provider,
prompt, and whether AI runs at all in a given scope. This is a concrete upgrade
over the status quo, where the existing AI XBlocks expose little to no control
beyond the prompt. Developers ship good defaults; operators override them.

A4. **Reach beyond XBlocks.** The inputs a caller passes are plain,
serializable, and free of any XBlock or ORM shape, so the same API works from a
web request, a Celery task, or a block.

A5. **Evolve the existing framework, don't rewrite it.** The surface sits *on
top of* the machinery that already exists. Profiles, scope resolution,
orchestrators, sessions and storing ai responses. It adds the minimum net-new.
A side effect we accept: the internals of the existing REST API may need reworking
to match what this surface exposes.

A6. **Make writing orchestrators and processors easy.** Much of what consumers
want may be achievable through a prompt alone, but when it is not, writing a
custom orchestrator or processor is a first-class, well-supported path, not a
fight with the framework.

A7. **Define-and-call ergonomics.** A developer can declare a profile in code
and run it immediately, with operator overrides applied transparently if they
exist.

A8. **A durable record and analytics for free.** Consumers get their AI
interactions persisted without writing storage code, and without the result type
being entangled with how storage happens. The same default wires in xAPI, so
analytics and the Aspects platform light up out of the box.

A9. **Long-term supportability by design.** The surface adopts standard
longevity practices like explicit public exports, shipped type information, enforced
module boundaries, and staged deprecation.

Decision B: The delivery mechanism
===================================

How the API reaches consumers in code is a separate decision from what it
exposes. We commit to the following goals; the concrete mechanism is designed
against them and refined with the community discussion.

B1. **A natural, low-coupling extension point.** Consumers reach the API without
importing framework internals or coupling to its release cycle. For XBlocks,
the leading candidate is an ``"ai_extensions"`` runtime service (the subject of
:doc:`0005-xblock-ai-service-registration`); the same seam should generalize to
the forum, courseware, and other plugins next. Whichever mechanism is chosen,
what it hands back is the ``api.py`` surface itself, not a bespoke, per-service
shape: the seam is a way to *reach* the API, never a second contract to
maintain alongside it.

B2. **The heavy weight is optional, via a library split.** The definitions and
the contract live in a light package that is always safe to depend on, separate
from the package that carries the LLM router and its unavoidable weight. An
install that does not use AI does not pay for it. The arguments:

- LLM routers are a costly dependency, with many megabytes of downloads and a
  large transitive tree.
- They release often; keeping them separable lets the AI package follow that
  cadence independently, faster than the release rhythm of edx-platform's own
  dependencies.
- For anyone not using AI, carrying the router makes no sense at all.
- Keeping the router separable is part of an ongoing effort to keep dependency
  hell out of the platform. This decision stays in line with that effort rather
  than solving it outright.

B3. **Testable against the contract, without the engine.** A consumer, and the
project itself, can test code against what the API is supposed to return, and
check versions for compatibility, without installing the router and the whole AI
stack. The light package carries enough of the contract (types, statuses, stubs)
to test against on its own.

Non-Goals
*********

For now, and recorded so the surface is not asked to grow into them prematurely:

- **Human-in-the-loop approval / grading review.** Deliberately out of scope;
  the result shape leaves room to add it later.
- **Cost / budget enforcement.** We report usage; we do not police spend yet.
- **Multiple interchangeable engines.** There is one engine; the API contract is
  "our ``api.py``," not a generic multi-vendor service specification, and there
  is no plugin-discovery mechanism for the engine.
- **Exposing the LLM / router layer.** Internal by intent, and central to
  Decision B's ability to keep the weight out of the light package.

Consequences
************

- Consumers gain a single, typed, supported way to run AI, and stop
  re-implementing provider calls, prompt plumbing, storage, and analytics.
- Operators gain structural control over model, prompt, and on/off state per
  scope, independent of the developer who wrote the consumer.
- An install that does not use AI can depend on the light package without pulling
  in the LLM router, and the AI package can track the router's fast release
  cadence on its own schedule.
- The internals of the existing REST API may need reworking to align with what
  the public surface exposes. This is normal evolution, accepted as a consequence.
- Operator authority can override developer intent. This is accepted, because
  operator control is the goal, not a side effect.
- Two open areas remain to be designed and are expected to return as follow-up
  decisions: a finer taxonomy of "unavailable" outcomes (config-disabled vs.
  no-engine vs. not-for-this-user vs. transient outage), and the concrete
  versioning and backwards-compatibility window that A9 commits to in principle.
- Whether to commit to the runtime-service delivery path now, or defer it until a
  second consumer justifies a pluggable service, is left to the community
  discussion referenced above; Decision B fixes the goals but not that timing.

Rejected Alternatives
*********************

**A single package carrying the router.** Simpler to release and reason about,
but it forces the LLM router's weight and release cadence onto every install,
including those that never use AI. Rejected in favor of the light/heavy split
(Decision B).

**A pluggable, multi-engine interface with plugin discovery.** Attractive as a
"vendor-neutral" contract, but there is exactly one engine, and a discovery
mechanism for it would add machinery and a broader contract surface with no
current consumer. Rejected; the engine stays a single internal implementation
detail behind one seam.

**Exposing the LLM / router (litellm) layer directly.** Would let advanced
consumers reach the router, but it would leak the heavy dependency into the
contract, defeat the light/heavy split, and tie the public surface to a
third-party chunk and response shape. Rejected; the engine is internal.

**Letting each consumer keep wiring its own provider calls and storage** (the
status quo). Requires no new API, but leaves every consumer duplicating prompt
handling, storage, error shapes, and analytics, with no shared point of operator
governance. Rejected as the very problem this ADR exists to solve.

References
**********

- :doc:`0001-purpose-of-this-repo`
- :doc:`0005-xblock-ai-service-registration`
- OEP-0019: Developer Documentation.
  https://docs.openedx.org/projects/openedx-proposals/en/latest/best-practices/oep-0019-bp-developer-documentation.html
- Community discussion, *Plugin-provided XBlock runtime services*.
  https://discuss.openedx.org/t/plugin-provided-xblock-runtime-services/18682
