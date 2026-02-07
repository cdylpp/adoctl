# Blocker

**Definition**
A *blocker* is an issue that cannot be resolved or overcome at the level in which the issue was discovered. It impedes, or substantially diverts, forward progress of a project, process, or business-related task.

Although it is natural to take the path of least resistance, blockers should be identified immediately with a description, impact, mitigation plan, an owner, and an estimated time of completion (or ETA).

Blockers will be identified at the work item level by adding the `blocker` tag. Additionally, metadata about the blocker should be attached within the discussion section with an `@blocker` mention. This allows efficient parsing of metadata.

## Metadata

**Work Item Type**: `Blocker`

### Required
Blocker metadata should be placed within the **Discussion** section of the blocked work item prefaced with `@blocker`. It is required to contain the following data:
- **Description**: briefly explain the issue and any errors.
- **Impact**: describe what cannot be done; who it effects; what product cannot be complete.
- **Mitigation**: what are the actions taken to reduce risk.
- **Owner**: the individual/group responsible for tracking the blocker.
- **ETA**: estimated time to of resolution.
- **Links**: Proper linking is crucial for understanding a risk's impact.
    -   **Parent Link:** Every risk must have a **parent** link to the **Key Result** it could affect.
    -   **Successor Link:** Any work item (like a Feature or User Story) that is blocked or will be impacted if the risk materializes must be linked as a **successor**.

# Examples 
![image.png](/.attachments/image-8492976b-ce72-44d5-aeb7-0bd0eb2a5dd9.png)
___
