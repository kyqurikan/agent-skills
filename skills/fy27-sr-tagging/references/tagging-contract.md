# FY27 SR tagging contract

## Observed source

`Sales Team FY27/Tag and SRs.md` contains a Markdown table beneath the `## SRs` heading. The required columns are:

| Column | Expected value | Role |
| --- | --- | --- |
| `Company Name` | `#Customer_...` | Exact company identity |
| `SR Number` | `#SR` plus digits | Tag to add |
| `OppID` | `#` plus the table's uppercase alphanumeric ID | Tag to add |
| `CPR` | `#CPR_...` | Exact owner corroboration |
| `Status` | Free text | Informational only |

Rows with blank SR Number or OppID are intentionally non-actionable. Status does not override that rule and does not otherwise filter complete rows.

## Observed note formats

Sales Team FY27 notes may use an inline tag-only line at the top of the Markdown body:

```markdown
#7-15-26 #FY27 #Q1 #Customer_Acme #CPR_AdaLovelace
```

After tagging, the line becomes:

```markdown
#7-15-26 #FY27 #Q1 #Customer_Acme #CPR_AdaLovelace #SR0001234567 #A1B2C3
```

They may instead use a top-level YAML block list:

```yaml
---
tags:
  - FY27
  - Q1
  - CPR_AdaLovelace
  - Customer_Acme
---
```

After tagging, insert the values into that same list:

```yaml
  - Customer_Acme
  - SR0001234567
  - A1B2C3
```

Also support a one-line YAML list such as:

```yaml
tags: [FY27, Customer_Acme, CPR_AdaLovelace]
```

Prefer a valid top-level YAML `tags` list when present. Fall back to the first non-empty body line only when the frontmatter has no `tags` property. Skip duplicate keys, scalar `tags` properties, nested structures, or malformed lists rather than rewriting YAML speculatively.

## Exact-match policy

Normalize only the storage representation: YAML list values may omit the leading `#`, while inline body tags and source-table values include it. Add the leading `#` internally for comparison, then match the customer and CPR values case-sensitively. This prevents a similarly named company or a reassigned customer from receiving another record's identifiers.

The two existing tags are independent evidence:

1. Company Name identifies the customer.
2. CPR identifies the associated sales owner.
3. Their exact pair selects the SR record.

A filename, folder owner, summary, transcript mention, or partial tag is not equivalent evidence.

## Conflict policy

Skip rather than guess when:

- the same `(Company Name, CPR)` key has contradictory complete rows;
- a note matches more than one complete table row;
- a note's table-known Company Name has a different CPR;
- a note already contains another `#SR` tag;
- a note already contains another six-character uppercase alphanumeric OppID-like tag;
- the source row is missing either output tag.
- a YAML `tags` property is duplicated, malformed, nested, or scalar rather than a block/inline list.

Correct the evidence, preview again, and only then write.
