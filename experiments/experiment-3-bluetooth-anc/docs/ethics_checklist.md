# Ethics Checklist

| Check | Result | Rationale |
|---|---|---|
| Clearly label simulated data | PASS | Every report and CSV workflow describes the data as fictional/synthetic. |
| Claim real market provenance | PASS | No claim of scraping, survey, purchase or platform access is made. |
| Include personal information | PASS | There are no names, contacts, user IDs, or free-text personal reviews. |
| Preserve raw data | PASS | `data/raw/raw_data.csv` is retained and the generator refuses overwrite. |
| Make transformations auditable | PASS | `docs/cleaning_log.csv`, `docs/sample_10.csv`, and the cleaning script record decisions. |
| Explain limitations | PASS | Results cannot estimate real market share, consumer sentiment or platform behavior. |
| Human review of AI output | PASS | Rules, injected defects, range checks and reproducibility checks were inspected before submission. |

The data must not be presented as a real market survey or used for commercial decisions without independently collected and ethically reviewed evidence.
