# Risks


**Definition**
A _risk_ is any identified uncertainty that could negatively impact delivery timelines, product quality, stakeholder alignment, or resource availability if not actively monitored or mitigated.

Within the ADO context, risks should only be tagged if they refer to future potential problems, not an active issue. Tagging should occur at backlog refinement or sprint review checkpoints, making it visible for portfolio-level dashboards. Fields should be lightweight and reviewable in under 30 seconds per risk.

## Fields

- Work Item Type: `Risk`

**Required**
- **Title**: short, descriptive title for the risk.
- **Risk Status**: 
  - Assessing: actively investigating a risk to determine its potential impact, likelihood, and priority.
  - Monitoring: a risk that has a response plan in place and is being actively tracked. This is for risks you are keeping an eye on.
  - Mitigated: Use this status once actions to reduce the risk's impact or likelihood have been successfully completed and confirmed to be effective.
  - Identified: for a newly discovered risks that has been logged but has not yet been analyzed. This is the initial state for all new risks. 
  - Closed: use when a risk is no longer relevant. This applies if the project is finished, the threat has passed, or the issue is fully resolved.
- **Risk summary**: short descriptor for roll-up visibility.
- **Next review date**: keeps all risks on the radar.
- **Owner**: who is accountable for monitoring.
- **Links**: proper linking is crucial for understanding a risk's impact.
    -   **Parent Link:** every risk must have a **parent** link to the **Key Result** it could affect.
    -   **Successor Link:** Any work item (like a Feature or User Story) that is blocked or will be impacted if the risk materializes must be linked as a **successor**.

### Optional

-   **Risk category**: Allows PMs to cluster risk types.
-   **Likelihood**: A quick signal for review cadence. A value between 0 and 1. A value of 1 indicates this will happen with certainty, whereas a value of 0 indicates this risk will never happen.

## Examples

![image.png](/.attachments/image-560fd554-ac6f-4ef6-93cb-563e696b382f.png)

## WIT Contract