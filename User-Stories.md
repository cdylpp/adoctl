# User Story

**Definition**

A *user story* is a project requirement stated in one sentence. Under the work item hierarchy, a user story falls under a [feature](/Black-Lagoon-ADO-Guide/Work-Items/Features) and can be completed within days (typically completed within a single sprint). User stories are further broken down into *tasks*.

## Metadata

### Required
- **Title**: Clear, meaningful title that containing the action to be completed.
- **Description**: 
  >As a [`persona`], I need [`capability`], so that [`outcome`].
- **Owner**: Individual responsible for completing the user story.
- **Acceptance Criteria**: Specific action to be completed; definition of done for the user story. Format using given / when / then.
- **Story Points**: estimation of effort/complexity, this estimate should consider the difficulty of the work and **not** the time associated with it. Check the section [below](#Story-Pointing) for more
- **Link**: ensure the user story is linked to a parent feature. The parent should aggregate to the key result.


## Story Pointing
Story pointing involves assigning a numerical value based on the effort involved for a particular user story. For this, we use the Fibonacci series: $0, 1, 1, 2, 3, 5, 8$ (we often omit $0$, $1$). More generally, 

$$F_{n} = F_{n-1} + F_{n-2}.$$

Here is a map from t-shirt sizes of work to Fibonacci numbers. The lower (upper) bound is 1 (8).

>1 $\mapsto$ small 
>2 $\mapsto$ medium
>3 $\mapsto$ large
>5 $\mapsto$ XL
>8 $\mapsto$ XXL 

Story points are fundamental to tracking burndown, capacity, and completion rate.

## Example

![image.png](/.attachments/image-77e7539d-5b9c-4f63-ad7a-a6e3fc7042d9.png)