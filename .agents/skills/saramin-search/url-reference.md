# Saramin (사람인) HTML Reference

Base URL: `https://www.saramin.co.kr`

## Search

```
GET /zf_user/search?searchword={q}&recruitPage={page}&recruitSort=relation&searchType=search&company_type[]={scale}
```

`--company-type` mapping: `major`→`scale001`, `enterprise-1000`→`scale002`, `mid`→`scale003`, `sme`→`scale004`, `startup`→`scale005`, `foreign`→`foreign`, `public`→`public`, `kospi`→`kospi`, `kosdaq`→`kosdaq`.

Parsing anchors in the HTML response:
- Job ID: `rec_idx="(\d+)"`
- Title: `href="/zf_user/jobs/relay/view...rec_idx={id}..."><span>...</span>`
- Company: `<strong class="corp_name"><a>...</a>`
- Location/conditions: `<div class="job_condition">...</div>`
- Posted date: `<span class="job_day">등록일 ...</span>`

Detail URL: `/zf_user/jobs/view?rec_idx={id}`

## Detail

Parsing anchors:
- Title: `<h1 class="tit_job">...</h1>`
- Company: `<a class="company">...</a>`
- Description: `<div class="user_content">...</div>`

## Notes

- robots.txt disallows some AI crawlers; use low volume for personal job search only.
- `--jobage` is not supported (no stable public date filter in search URL).
