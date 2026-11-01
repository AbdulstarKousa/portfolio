# FinCopilot project walkthrough

Edit `html/fincopilot.html` directly. It reuses `styles/site.css`, with walkthrough rules in `styles/fincopilot.css`. Project cards in `index.html` and `projects.html` and the sitemap point to this page. This is a screenshot walkthrough, not an interactive finance app.

## Public examples

Every household record, balance, transaction description, income and expense schedule, allocation rule, position and purchase marker in the screenshots is synthetic. The capture does not copy bank data, secrets, account reports or portfolio caches from the finance repository. It creates seeded fixtures and replaces household configuration before importing the application. The example pairs an IWDA.AS core holding with a HEAL.AS tactical position. Position sizes, purchase dates and allocations are fictional; execution prices match public closes on those dates. Public market histories and FX rates are downloaded separately using yfinance; no market prices are fabricated. `fincopilot-capture.json` records their dates and the fixture seed.

Briefing and conversation text are scripted, labelled examples. No AI provider is called during capture, and these screenshots are not evidence of AI answer quality.

Screenshots live only in `images/fincopilot/`. Do not restore the earlier personal-account images from Git's index or history. When preparing a commit, include the replacements and check the staged image versions too.

## Reproduce

Run `scripts/capture_fincopilot.py --source PATH_TO_FINANCE_REPO` using the finance repository's Python environment, with Playwright and Chrome available. The app copy and generated files stay in ignored `.cache/fincopilot/`; the source repository is read-only. The script refuses to initialise over an existing data directory. An interrupted capture can be resumed without `--source`; this recreates seeded fixture files and reuses only the public-price download.

Captures are written to `.cache/fincopilot/captures/` for review before copying to the public image directory. Review shows a completed salary cycle; Forecast and Plan show the upcoming month. Inspect every capture and update HTML image dimensions when replacing it.

The two Tactical views use their own source captures and a footer captured from the actual Tactical tab. The chat example keeps a little empty space after the answer and includes the real message composer and all four question suggestions. Its two `.demo-crop` regions remove excess empty space without altering the source PNG.

## Presentation

Keep the article modern, minimal and personal. Explain the problem, the system's design and what the author is learning. Keep deterministic calculations distinct from AI interpretation, and avoid implying product-launch plans or measured user outcomes.

The social preview source is `images/fincopilot-cover.svg`; render it at 1200 by 630 to update `images/fincopilot-cover.png`. It contains no household figures.

Capture checks reconcile the completed review cycle to one salary and net savings, require a computed restaurant-frequency finding, verify core and tactical positions, and compare each purchase marker against the plotted public closing price. Daily history is valued from the same fictional lots and public prices to populate the Overview portfolio sparkline and drawdown. Only unused top-level disclosures are hidden; category and habit drill-down rows stay visible.

The capture copy labels the allocation tab Plan while keeping internal decision callback IDs intact. Use `--tab Tactical --tab Plan` for a focused recapture. Investment-detail crops include padding above Ticker Pick so the heading stays fully visible.
