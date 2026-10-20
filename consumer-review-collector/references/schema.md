# Review CSV schema

The analysis script requires these columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `brand` | yes | Brand or seller label; use `unknown` when the source does not expose one. |
| `product` | yes | Product or listing label; use `unknown` when unavailable. |
| `rating` | yes | Integer 1–5. An empty value means missing; a non-empty value outside 1–5 is invalid. |
| `review` | yes | Review text. Empty text is retained as an empty string and reported. |
| `review_id` | no | Stable source identifier when exposed. |
| `reviewer` | no | Public display name, if exposed. Avoid collecting private data. |
| `review_date` | no | Published date as shown by the source. |
| `source_url` | no | Page URL or local fixture path. |

Analysis definitions:

- Average uses valid integer ratings only.
- Positive means rating 4–5; problem means rating 1–2.
- Issue labels are multi-label. A low-rating review can count once under each matching issue, but repeated keywords in one review do not increase its count.
- Missing ratings remain in the total row count and are excluded from rating denominators.
- Invalid non-empty ratings stop analysis with an explicit error.
