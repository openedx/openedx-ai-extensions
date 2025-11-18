0002 Dynamic workflow configuration
###################################

Status
******
**Provisional**

Context
*******
One of the initials goals of this project is to enable experimentation with AI
in education. To support this goal, we need administrators to modify runtime configurations after deployment without requiring new builds.

Decision
********
The basic AI enhanced UI experiences from the repository will be configurable
by a backend API. This creates a small delay in loading of the experience as the
frontend component must first call an extra API before it is visibly rendered.


Rejected Alternatives
*********************
**Configuring the frontend components during build:**
- **Pros:** Faster load times
- **Cons:** Significantly reduced flexibility for administrators and authors to
enable, disable, or configure experiences.

Backend defined configurations allows platform admins to easily show or hide
workflows in different contexts (course, unit, location).

References
**********
- https://github.com/openedx/openedx-ai-extensions/pull/27
