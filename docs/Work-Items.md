# Black Lagoon ADO Work Items

Listed below is an overview of existing work item types as they pertain to Black Lagoon and our processes in ADO. Black Lagoon extends the default Agile process by adding special work item types like objectives, key results, and custom issue types.

## General Best Practices

- Keep it brief but informative
- Use [links](/Black-Lagoon-ADO-Guide/Work-Items/Linking) to maintain traceability between KRs, Features, User Stories, Tasks, etc.

## Work Item Hierarchy

`Epic` $\to$ `Feature` $\to$ `User Story` $\to$ `Task` / `Bug` / `Issue` / `Test Case`

## Summary of Work Item Types.

| **Work Item** | **Definition** | **Naming Conventions** | **Best Practices** | **Examples** |
| :--- | :--- | :--- | :--- | :--- |
| **Objective** | A high-level, aspirational goal for the team or organization. Objectives are qualitative and define a clear direction. | Title case, describing the desired outcome. | Should be ambitious and inspirational. Limit to 3-5 per quarter. Each Objective is broken down into Key Results. | `Improve New User Onboarding Experience`, `Increase Product Adoption` |
| **[Key Result](/Black-Lagoon-ADO-Guide/Work-Items/Key-Results)** | A measurable outcome that tracks progress towards an Objective. | State the measurable outcome clearly. | Should be quantitative and measurable. Defines success for the Objective. Each Objective should have 2-5 Key Results. | `Reduce time to value by 50%`, `Increase MAU by 15%` |
| **[Feature](/Black-Lagoon-ADO-Guide/Work-Items/Features)** | A service or component that delivers value and contributes to a Key Result. | Action-oriented title describing the functionality (e.g., Develop, Plan, Implement). | Should be achievable within a release or a few sprints. Each Feature supports one Key Result. | `Develop Self-Service Registration`, `Design In-App Tutorial` |
| **[User Story](/Black-Lagoon-ADO-Guide/Work-Items/User-Stories)** | A user-centered requirement that provides value to an end user, as part of a Feature. | Action-oriented title describing the user requirement (e.g., Develop, Plan, Design). | One story per _user function_. Small enough to complete within a single sprint. Must include _description_ and _acceptance criteria_. | `Implement user registration with work email` |
| **Task** | A technical or operational sub-step of a User Story. | A clear description of the action to be taken. | Linked to a User Story or Bug. Small enough to be estimated in hours. | `Validate Email Domain` |
| **[Blocker](/Black-Lagoon-ADO-Guide/Work-Items/Blockers)** | An obstacle that is actively preventing a team from making progress on a work item. | Start with 'Blocker:' followed by a clear description of the impediment. | Clearly state the impediment and its impact. Assign an owner and a due date for resolution. Escalate immediately. | `Blocker: API key from auth team is invalid` |
| **[Risk](/Black-Lagoon-ADO-Guide/Work-Items/Risks)** | A potential future event that, if it occurs, could negatively impact project objectives. | Start with 'Risk:' followed by a description of the potential issue. | Identify risks early. Assess probability and impact, and create a mitigation plan for high-priority risks. | `Risk: Planned design system update may delay frontend work` |
| **[Critical Business Decision](/Black-Lagoon-ADO-Guide/Work-Items/Critical-Business-Decisions)** | A pivotal choice that impacts the project's direction, scope, or alignment with business goals. | Start with 'CBD:' followed by the decision required. | Document the decision required, options, pros/cons, and stakeholders. Set a clear deadline and record the final rationale. | `CBD: Should we require credit card info for a free trial?` |