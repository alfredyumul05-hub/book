# Staff Directory URL Research Notes

## Scope

- Batch: `CA-01`
- State: California
- District count: the first 50 California school districts from the user-provided list, in the same order.
- Research date: 2026-05-15.

## Method

1. Searched each district using staff-directory oriented queries, prioritizing official district/school domains over third-party people databases.
2. Opened likely staff pages and scanned page text for staff-directory indicators, visible names/roles, and visible `@domain` email addresses.
3. Skipped or marked pages as `not_verified_visible` when a current page with visible staff information could not be confirmed in this pass.
4. Did not generate individual staff email addresses. Where emails were not visible, the CSV records only that no verified pattern was observed.

## Status Definitions

- `visible_names_and_emails`: Staff names/roles and at least one email address were visible in the fetched page text.
- `visible_names_no_emails`: Staff names/roles were visible, but no email addresses were visible in the fetched page text.
- `not_verified_visible`: An official or plausible site was found, but a current visible staff directory could not be verified in the first pass.

## Batch Output

The CSV output is `research/staff_directory_urls_ca_batch_01.csv`.

## Batch Summary

- 50 California districts researched.
- 43 rows have visible staff names/roles confirmed or strongly indicated.
- 11 rows have visible staff names/roles plus at least one visible email address detected by page-text scan.
- 7 rows are marked for follow-up verification because the first-pass search did not confirm a current visible staff directory.

## Follow-Up Needed

- Texas and Arizona batches require the corresponding district lists or permission to choose 50 priority districts per state independently.
- Rows marked `not_verified_visible` should be revisited manually before using them as completed directory sources.

## Continuation: CA-02

- Batch: `CA-02`
- Scope: California priority rows 51-100 from the user's supplied list, continuing immediately after `ARISE High District` and ending with `Blake Elementary School District`.
- Output file: `research/staff_directory_urls_ca_batch_02.csv`
- Methodology update: continued the same official-source-first workflow used in CA-01. For this pass, I prioritized official district pages and search result snippets that exposed staff-directory content. When a full staff directory was not confirmed quickly, I recorded the best official site or CDE administrator-contact fallback and marked the row `not_verified_visible`, `visible_admin_contacts_only`, or another limited status rather than overstating visibility.
- Email-pattern handling: I only recorded a pattern when an official or directory source explicitly exposed one, such as Atascadero's county directory stating `firstlast@atasusd.org`. I did not generate individual staff emails from unverified patterns.
- CA-02 quick counts from validation:
  - Total rows: 50
  - Rows with `names_visible=yes`: 26
  - Rows with `emails_visible=yes`: 17
  - Rows still requiring follow-up verification: 23

## Next California continuation point

- The next batch should begin at priority row 101: `Blochman Union Elementary School District`.
