# JobKorea (잡코리아) HTML Reference

Base URL: `https://www.jobkorea.co.kr`

## Search

```
GET /Search/?stext={q}&Page_No={page}&tab={tab}
```

Optional `tab` (with `--company-type`): `major` (대기업), `SME` (중견·중소), `foreign`, `MME` (공기업·공사). Search also embeds list badges such as `믿고보는 대기업` / `탄탄한 중견기업` used for client-side filtering when the URL filter is inconclusive.

Parsing anchors (Next.js rendered HTML):
- Job ID: `GI_Read/(\d+)`
- Title: `truncate font-semibold...">TITLE</span>` within card window
- Company: `text-gray700 text-typo-b2-16">COMPANY</span>`
- Location: `basicemoji-place2` chip → `text-typo-b4-14">LOCATION</span>`

Detail URL: `/Recruit/GI_Read/{id}`

## Detail

Primary source: `<script type="application/ld+json">` JobPosting block (title, description, datePosted, validThrough, hiringOrganization, jobLocation).

Fallback: `og:title`, `og:description` meta tags.

Full HTML descriptions are hosted on signed S3 URLs embedded in the page; the CLI uses schema.org JSON-LD for stability.

## Notes

- Search results do not expose posting dates in the list HTML (date is `null` in search output).
- `--jobage` is not supported on the public search URL used here.
