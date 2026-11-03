---
name: brand-voice
description: Create and review evidence-led consumer content briefs using the brand voice rules below.
---

# Brand Voice Skill

Use this skill when a module turns consumer evidence and competitor observations into a content strategy or draft. Return language that is clear, calm, specific, and useful. Treat evidence limits as part of the brief.

## Inputs

Accept these fields from a calling module:

- `brand_name`
- `target_audience`
- `content_objective`
- `channel`
- `consumer_evidence`: source, sample size, finding, and evidence IDs or excerpts
- `competitor_evidence`: source, comparison scope, and evidence IDs
- `approved_claims`: claims supported by product records or a named test
- `prohibited_claims`: claims that are unverified or outside the approved scope
- `success_indicators`: measurable test outcomes

If category-aligned consumer evidence or approved product claims are missing, return a research brief with that gap stated plainly. Do not fill the gap with plausible-sounding claims.

## Voice

- Lead with the audience's concrete decision or use case.
- Use plain, conversational Chinese. Prefer short active sentences and specific nouns.
- Explain a feature through a test condition, comparison, or practical consequence.
- State what the evidence covers and what it cannot establish.
- Use a modest invitation as the call to action; avoid pressure and false urgency.
- Keep claims proportional to the evidence and preserve units, denominators, and test conditions.

Common useful words include `实测`, `条件`, `适合`, `比较`, `说明`, `证据`, and `场景`. These words are not a substitute for evidence.

Avoid unsupported superlatives and absolutes such as `全网第一`, `行业领先`, `顶级`, `彻底降噪`, `零延迟`, `百分百有效`, and `人人适合`. Do not imply medical, safety, or guaranteed outcomes without approved substantiation.

## Output Contract

Return:

1. A one-sentence audience insight with its evidence boundary.
2. The content objective and channel.
3. Three headline options and one short body draft.
4. One call to action.
5. An evidence ledger linking each factual claim to an approved source.
6. The success indicators and the experiment design.
7. A quality-check result listing unsupported claims, missing evidence, and required edits.

## Examples

Positive:

> 续航数字要和测试音量、连接方式一起看。我们会把测试条件和结果放在同一页，方便你按自己的通勤时长比较。

Why it passes: it names the decision, tells the reader what context will be shown, and does not invent a product result.

Negative:

> 全网续航第一，彻底解决通勤焦虑，闭眼买就对了！

Why it fails: it makes an unsubstantiated ranking and guarantee, uses pressure language, and gives no test conditions or evidence.

## Quality Checks

- Every factual product statement has an approved claim and a traceable evidence reference.
- A source sample from another product category is labeled as a proxy, never as proof of target-category demand.
- A missing topic is labeled `not observed`; it is not silently converted to zero interest.
- A competitor product gap is not presented as a consumer need unless aligned user evidence supports it.
- Every brief names the audience, content direction, evidence, and a measurable success indicator.
- The final copy contains no prohibited claim, unsupported superlative, or mismatch between a number and its denominator.
