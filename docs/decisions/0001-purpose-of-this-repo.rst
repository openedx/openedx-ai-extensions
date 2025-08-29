0001 Purpose of This Repo
#########################

Status
******
**Provisional**

Context
*******
At the Open edX Conference in Paris 2025, the concept of AI-powered extensible workflows was presented, demonstrating the potential for integrating artificial intelligence capabilities into educational technology pipelines.

Currently, the Open edX ecosystem lacks a dedicated space for experimenting with AI workflow capabilities outside of the core platform. This creates challenges for rapid prototyping, testing new AI integrations, and developing proof-of-concept implementations.

Decision
********
We will create a repository dedicated to experimenting with AI-powered pipeline generation and extensible workflows that utilize artificial intelligence within their core functions. This repository will serve as the starting point of what could ultimately become a robust SDK for future experimentation.


Rejected Alternatives
*********************
**Building AI extensibility directly into the edX Platform repository:**
- **Pros:** Direct integration with the context of the lms and cms systems
- **Cons:** Much slower PR merge times, forces all developers to use the same codebase, slower development cycles

The plugin approach is preferred because it's faster to develop, maintains extensibility, and using events and filters makes it easier to maintain as the platform evolves. The decision to integrate into the default dependencies of the core can be made later.


References
**********
- Canva presentation from Open edX Conference Paris 2025 https://www.canva.com/design/DAGqjcS2mT4/nTHQIDIeZ89wqsBvh9GWKA/view
