# GitHub references

These public repositories were inspected as implementation references. They are not runtime dependencies of this skill.

| Repository | Pinned commit | What was reused conceptually | Boundary |
| --- | --- | --- | --- |
| [kaymen99/Yelp-scraper](https://github.com/kaymen99/Yelp-scraper) | `1a76293e04d638c30b02698d8e3d6d135c6446e1` | A small Flask/Selenium workflow that collects public business/review data and exports CSV. | Selenium and site-specific selectors are not required by this standard-library implementation. |
| [jatinaryan1107/amazon-review-scraper](https://github.com/jatinaryan1107/amazon-review-scraper) | `86a346890d577df83ce39f622c7c2b99a5a76a20` | Separation of collection, durable review records, offline analysis, and explicit coverage limits. | The project is larger and Amazon-specific; this skill does not copy its browser automation or account/session handling. |

The references were obtained with `git ls-remote` and shallow clones on 2026-10-20. Keep the pinned commit when citing behavior so a later repository change does not alter the provenance record.
