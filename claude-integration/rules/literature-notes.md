# Literature Notes Rule

> Auto-triggered for files in reading notes directories.

## Note Card Format (v2)

All reading notes should follow this structure:

```markdown
---
title: "Article/Paper Title"
source: "Journal/Website Name"
author: "Author Name"
date: YYYY-MM-DD
tags: [tag1, tag2]
content_type: academic | industry | policy | opinion
---

# Title

## Core Argument
[One paragraph summary]

## Key Insights
1. [Insight 1]
2. [Insight 2]

## Quotable Passages
> "Quote" — Author

## Research Connections
- Relates to: [existing work]
```

## Rules

- Always include YAML frontmatter with at minimum: title, source, date, tags
- Tags should be lowercase, hyphenated for multi-word
- Content type must be one of: academic, industry, policy, opinion
- Quotable passages must be exact quotes with attribution
- Research connections should reference existing notes/papers by title
