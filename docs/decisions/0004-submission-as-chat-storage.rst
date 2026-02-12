
0004 Use Open edX Submission Service for Persistent Chat History
#################################################################

**Draft** *2026-02-12*

Context
*******

This AI framework enables conversational interactions between learners and AI assistants. To maintain continuity and provide context for AI models, we require a storage solution that is:

* **Persistent & Immutable:** For audit trails and conversation replay.
* **Context-Aware:** Linked to specific course blocks and user sessions.
* **Performant:** Supporting lazy loading of historical messages.

Decision
********

We will use the existing **Open edX Submission model** from `edx-submissions`_ via the ``SubmissionProcessor``. 

1. **Default Implementation:** Use the Submission service as the primary backend for the MVP to leverage existing database schemas and security protocols.
2. **Abstraction:** Implement the storage logic behind a **Processor Pattern**. This ensures the AI framework remains decoupled from the specific storage implementation.
3. **Future-Proofing:** This abstraction allows us to swap the Submission service for a specialized vector database or a dedicated SQL model in later phases without refactoring the core AI logic.

Consequences
************

* **Size Constraints:** Submissions are limited at 100KB. Long conversations will require a chunking strategy.
* **Query Limitations:** Data is stored as JSON strings; we cannot perform complex relational queries or database-level indexing on specific message attributes.
* **Performance:** Retrieving large volumes of submissions per session may impact latency as history grows. Lazy loading must be enforced.

Rejected Alternatives
*********************

* **Custom Django Models:** Rejected for the MVP phase to minimize infrastructure overhead. We are prioritizing user-facing features over custom database optimization.

References
***********

* `edx-submissions`_

.. _edx-submissions: https://github.com/openedx/edx-submissions
