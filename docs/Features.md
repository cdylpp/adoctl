# Feature

**Definition**
A *feature* describes a large solution, functionality, or deliverable, that provides direct value to its customers, or towards the parented Key Result. Features intended to be completed in a single planning increment. As mentioned, features sit below [Key Results](/Black-Lagoon-ADO-Guide/Work-Items/Key-Results) in the work item hierarchy, as they break larger projects into smaller sub-components.

Ideally, features should be planned for two sprints. However, features can fall within the range of two sprints to one quarter. Features should not extend beyond a quarter nor be shorter than two sprints. Otherwise, consider creating either an Key Result or a User story, respectively.

## Metadata

### Required

- **Title**: Concise, action orientated title. Keep it simple; de-duplicate data.
- **Area Paths**: select the area path relative for the Epic. Area paths are broken down in the following scheme.
  - `Black Lagoon\[Team]\[FunctionalArea]\[ProductName]` 
- **Iteration**: If it is clear which iteration this will be planned for, place it in that specific iteration (e.g., `Black Lagoon\[Team]\[FY-XX]`). Otherwise, place it in the respective team backlog i.e., `Black Lagoon\[Team]`.
- **Dependencies**: Tag any associated dependencies using the format: `dependency:N#`, where `#` is the N-code number. 
- **Description**: _As a [persona], I need [capability] so that [outcome]_
- **Link**: Create a _parent_ link back to the key result. **Do not** nest features within features; reconsider decomposing your work differently.
- **Owner**: Features should be assigned to the product owner, unless features are taken by a single individual end-to-end.
- **Definition Of Done**: Articulate the definition for success relative to this feature.
- **Release Plan**: Tag with `NOW`/`NEAR`/`FAR` dependent on month of execution. Use the following map for tagging:
  
  >QX month 1 $\mapsto$ `NOW`
  >QX month 2 $\mapsto$ `NEAR`
  >QX month 3 $\mapsto$ `FAR`

# Examples

In this example, the iteration should be set to the `Black Lagoon\Digital Transformation` since this is the team that will execute this feature.

![image.png](/.attachments/image-f46355c0-b7eb-4c70-b206-8493eae2e03d.png)
