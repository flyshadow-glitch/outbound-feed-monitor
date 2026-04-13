# Feed Type Reference — Template

This file is auto-populated during onboarding (Step 0D) by analyzing a sample feed report email.
It ships empty in the repo. Do not add client-specific data here — it is generated per-user.

---

## Structure

Each account will have 1–N emails per cadence run. Each email contains rows for one or more feed types.
The skill auto-detects feed types by grouping file name patterns and source table prefixes.

### Example (generated during onboarding)

```
## Email 1: Media (Non-PLD)

**Typical send time:** ~14:00 UTC Monday

### Expected Files & Source Tables

| File Pattern | Source Table | Notes |
|---|---|---|
| `<BRAND>_HCP_GA_AD_PERFORMANCE_REPORT_*` | `<client>_hcp_google_ads_performance` | Google Ads ad-level |
| `<BRAND>_HCP_GA_GEO_PERFORMANCE_REPORT_*` | `<client>_hcp_google_ads_geo_performance` | Google Ads geo |
| `<BRAND>_HCP_BING_AD_PERFORMANCE_REPORT_*` | `<client>_hcp_bing_ads_performance` | Bing ad-level |
| `<BRAND>_HCP_DCM_ACTIVITY_*` | `<client>_hcp_dcm` | DCM activity |
| `<ACCOUNT>_DAYPART_DATAPULL_DCM_*` | `<client>_hcp_dcm_daypart` | DCM daypart |

**Identify this email by:** presence of `_GA_`, `_BING_`, `_DCM_`, or `_DAYPART_` in file names.
```

### Typical feed type categories

| Category | Identifiers | Stream |
|---|---|---|
| Google Ads | `_GA_` in file names, `google_ads` in table names | Non-PLD |
| Bing Ads | `_BING_` in file names, `bing_ads` in table names | Non-PLD |
| DCM | `_DCM_` in file names, `dcm` in table names | Non-PLD |
| Standard PLD | `_PLD_` in file names (excluding vendor-specific), `standard_pld` in table names | PLD |
| Vendor PLD | `_<VENDOR>_PLD_` in file names, `<vendor>_pld` in table names | PLD |
| SEO (GSC) | `_GSC_` in file names, `gsc` in table names | Non-PLD |

---

## How to Detect a Missing Email

If Gmail returns fewer than the expected number of emails:
1. Check which feed type is missing by inspecting the file names of the emails that did arrive.
2. Some emails go to different distribution lists, which can cause separate delivery or delays.
3. If the check is run before the typical send time, one or more emails may not have arrived yet.
   Note the time and suggest re-running after the last expected email time.

---

## Publisher Breakdown (PLD emails)

PLD emails include a publisher breakdown after each file's row:
```
Publisher Counts:
<PUBLISHER NAME> Row Count: <N> Distinct NPI_NUMBER: <N>
```
Capture these counts in your summary — zero counts on a publisher that usually has data is a warning.
Skip publisher breakdown rows during classification (they are display-only, not data rows).
