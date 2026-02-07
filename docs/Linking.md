# How to Link Work Items

## Why Linking Matters

Properly linking work items is fundamental to our team's operational success. It is the primary mechanism for the **decomposition of work**, allowing us to break down large, ambitious goals into manageable, executable pieces.

Beyond simple task management, this practice provides crucial **causal relationship mapping**. It creates a living, interconnected map of our work, enabling every team member to see how their individual tasks contribute to broader objectives and how different initiatives are intertwined. This visibility is key for identifying dependencies, understanding scope, and ensuring alignment across the team.

---

## The Work Item Hierarchy

All work items exist within a strict hierarchy. This hierarchy is enforced exclusively through **parent-child relationships**. The flow of work decomposition is as follows:

`Objective -> Key Results -> Feature -> User Story -> Task`

### Core Rules of the Hierarchy

1. **One Parent, Many Children:** Every work item can have **only one parent**. This is critical for maintaining a clear and unambiguous line of accountability and reporting. A work item can, however, have many children (e.g., a Feature can have multiple User Stories).
2. **No Same-Level Nesting:** A work item cannot be the child of another work item at the same level. For example, a Feature cannot have another Feature as its parent.
3. **Map Back to Key Results:** All work items below the Key Result level (Features, User Stories, Tasks) must be part of a chain that maps back to a parent Key Result. This ensures that all development effort is directly contributing to a measurable outcome.

---

## Linking Risks, Blockers, and Critical Business Decisions (CBDs)

Risks, Blockers, and CBDs are treated as special "impediment" work items and have a unique linking structure to capture both context and dependency. They use two distinct types of links.

### 1. Parent-Child Relationship (Context)

Every Risk, Blocker, or CBD **must have a parent**. The parent should be the primary work item from which the impediment originates. This link is essential for context and for grouping all related impediments under their corresponding Feature or User Story.

**Example:** 
>A risk concerning a third-party API is discovered while working on the `Implement user registration with work email` User Story. That User Story becomes the **parent** of the Risk work item.

### 2. Successor/Predecessor Relationship (Dependency)

This relationship type is **reserved exclusively for Risks, Blockers, and CBDs**. It is used to indicate a direct dependency where one work item cannot begin or be completed until the impediment is resolved.

**Example** (Continuing from above):
>The `Implement user registration with work email` User Story cannot be completed until the API risk has been mitigated. In this case, the User Story is made the **successor** of the Risk.

### Why Both Links Are Important

Using both linking methods provides a complete picture:

* The **parent** link tells us *where* the issue came from, allowing us to group all impediments by the features or stories they affect.
* The **successor** link tells us *what is downstream*, informing the team of the direct impact and what work is currently stopped pending resolution.