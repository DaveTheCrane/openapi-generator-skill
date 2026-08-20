---
inclusion: always
---

# Skill Bridge for Spec Workflow

During requirements, design, and task list creation phases, you MUST scan for relevant skills and incorporate their guidance.

## Process

1. List all SKILL.md files in both:
   - `.kiro/skills/` (workspace-level skills)
   - `~/.kiro/skills/` (global-level skills)

2. Read the YAML frontmatter of each SKILL.md file found.

3. Check for the `metadata.phase` key in the frontmatter. If it exists, its value is a comma-separated list that may contain: `requirements`, `design`, and/or `tasklist`.

4. Apply the skill based on the current phase:
   - **Requirements phase**: Include skills where `metadata.phase` contains `requirements`
   - **Design phase**: Include skills where `metadata.phase` contains `design`
   - **Task list phase**: Include skills where `metadata.phase` contains `tasklist`

5. If a skill's frontmatter does NOT have a `metadata.phase` key, use the skill's `description` field and `When to Use` section to determine relevance to the current work. Include it if it is clearly applicable.

6. When a skill is determined to be relevant, read its full content and follow its instructions as constraints on the output being generated.

## Example Frontmatter with Phase

```yaml
---
name: my-skill
description: Generates code from OpenAPI specs
metadata:
  phase: "design, tasklist"
---
```

This skill would be incorporated during design and task list creation, but not during requirements gathering.