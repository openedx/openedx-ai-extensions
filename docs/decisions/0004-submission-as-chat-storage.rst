
0004 Use Open edX Submission Service for Persistent Chat History
#################################################################

**Accepted** *2026-03-26*

Context
*******

This AI framework enables conversational interactions between learners and AI assistants. To maintain continuity and provide context for AI models, we require a storage solution for user and AI messages that is:

* **Persistent & Immutable:** For audit trails and conversation replay.
* **Context-Aware:** Linked to specific course blocks and user sessions.
* **Performant:** Able to perform well at large scale, even for conversations that become long.

Decision
********

We will use the existing **Open edX Submission model** from `edx-submissions`_ via the `submission API`_. 

1. **Default Implementation:** Use the Submission library as the primary backend for the MVP to leverage existing database schemas and security protocols.

The Submission model requires:

    - student_item_dict
    - answer

We will use the student_item_dict to store the relation to the user and scope by setting:

    - student_id -> the user_id.
    - course_id -> the course_id associated with the session, included as part of the submission lookup scope.
    - item_type -> "openedx_ai_extensions_chat", a constant used to separate these records from other submissions in the platform.
    - item_id -> the ai_workflow_session_id so that we can query all the turns for an individual session in bulk.

Each conversation turn is stored as a new Submission record for the same ``student_item``. The ``attempt_number`` field is intentionally omitted from the ``create_submission`` call so that the Submissions API auto-increments it, producing a naturally ordered sequence of attempts (1, 2, 3…) that represents the conversation history.

The answer will contain a JSON-serialized list of messages for that turn: the user message, the assistant message, and optional system messages. No internal metadata is embedded in the answer payload — chronological ordering is implicit in ``attempt_number``.

2. **Abstraction:** Implement the storage logic behind a **Processor Pattern**. This ensures the AI framework remains decoupled from the specific storage implementation.
3. **Future-Proofing:** This abstraction allows us to swap the Submission service for a specialized vector database or a dedicated SQL model in later phases without refactoring the core AI logic.


Consequences
************

* **Size Constraints:** Submissions are limited to 100KB. As a rough reference only, this may correspond to around 90k characters when most content is plain ASCII, with a more conservative working estimate around 50k characters once multi-byte characters and JSON overhead are considered. Longer messages or conversations will require input limits or truncation strategies. If limits become a concern, a future migration path is to store each message individually as its own submission rather than grouping a full conversation turn (prompt + response) into one record.
* **Query Limitations:** Data is stored as JSON strings; we cannot perform complex relational queries or database-level indexing on specific message attributes.
* **Performance:** Retrieving large volumes of submissions per session may impact latency as history grows.
* **Retrieval:** Long conversations should be retrieved in limited batches and reconstructed incrementally as older messages are requested. This is future optimization work.

Rejected Alternatives
*********************

* **Custom Django Models:** Rejected for the MVP phase to minimize infrastructure overhead. We are prioritizing user-facing features over custom database optimization.

References
***********

* `edx-submissions`_

.. _edx-submissions: https://github.com/openedx/edx-submissions
.. _submission API: https://github.com/openedx/edx-submissions/blob/master/submissions/api.py
