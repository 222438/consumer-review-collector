# Review of the 50-Row Raw Sample

The reviewed sample is `docs/sample_50.csv`, the first 50 rows of the raw generated file. These examples show the intended defects and the proposed handling rules.

| Issue | Example record | Raw example | Proposed rule |
|---|---|---|---|
| Currency and price-format variation | BT-0033, BT-0035 | `￥299`, `RMB 399` | Parse currency text and output a decimal with two places |
| Impossible or out-of-range price | BT-0003, BT-0006 | `￥-19`, `99999` | Reject the row because price is a required analysis field |
| Missing required value | BT-0025, BT-0027, BT-0029 | blank price, product name, or date | Drop the row and record the reason |
| Rating outside its scale | BT-0007, BT-0037 | `70分`, `5.8` | Keep the row but blank the invalid optional rating |
| Date-format variation | BT-0011 | `2026年3月8日` | Parse recognized date formats and standardize as YYYY-MM-DD |
| Brand alias or typo | BT-0013, BT-0041 | `N0va Pulse`, `NOVA-PULSE` | Map known aliases to the canonical fictional brand |
| Count format variation | BT-0015, BT-0017, BT-0045 | `1,234`, `1.2k`, `4,321` | Remove separators and convert k to an integer count |
| Negative optional interaction count | BT-0019, BT-0043 | `-12`, `-2` | Blank the invalid optional metric |
| Other numeric outliers | BT-0021, BT-0023, BT-0039 | battery `99`, score `70`, experience score `0` | Blank invalid optional metrics using dictionary bounds |
| Non-numeric count | BT-0031 | `一二三` | Leave the optional count blank because it cannot be parsed reliably |

At least five defect classes are present in this sample. The examples are simulated on purpose; they are not observations about real consumers or products.
