# Abdul Kousa portfolio — stage 5

This package combines the previously drafted home, About, Master's thesis and IMDb pages with newly redesigned Project 2, 4 and 5 pages. It also extracts the shared CSS into one stylesheet.

## Install into existing GitHub repository

1. Create a new branch from the branch containing your latest website changes (preferably `homepage-refresh`, or from `main` if previous changes were merged).
2. Back up your existing pages. Do **not** delete the existing `images/` folder, `favicon.ico`, `CNAME`, `notebooks/`, or other assets.
3. Copy these relative paths into the root of `AbdulstarKousa/portfolio`:

```
index.html
about_me.html
html/project1.html
html/project2.html
html/project3.html
html/project4.html
html/project5.html
styles/site.css
```

4. Keep the original images and other project assets. This package intentionally does not include those unchanged files.
5. Preview and check all links and images before merging.

## Note

- `styles/site.css` contains design rules for all seven pages. Change design tokens (colors, spacing) there instead of editing each HTML page.
- Navigation uses `../` for project pages inside `html/`. Keep this folder structure.
- Original shortened URLs were retained on project1/project4 pages; manually verify redirects.
- The historical repo for Project 2 is linked directly.
- This is an HTML/CSS update, not an automatic deployment to GitHub Pages.
- No new historical performance metric was invented.
