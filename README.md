# Clear Sky School Meals → Skylight

Unofficial Nutrislice-to-iCalendar feed. Each school day is one all-day event with breakfast and lunch menu items in its description.

## Publish using GitHub Pages

1. Create a **public** GitHub repository and upload `build.py`, `.github/workflows/update.yml`, and this README, preserving their paths.
2. In the repository's **Actions** tab, enable workflows and run **Update Clear Sky menus** manually. Check the run logs and inspect `docs/clear-sky-meals.ics` for real menu items.
3. In **Settings → Pages**, select **Deploy from a branch**, `main`, `/docs`, then Save.
4. Once Pages is active, the feed URL will be `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/clear-sky-meals.ics`.
5. In Skylight, open **My Skylight → Synced Calendars → Sync new calendar → Calendar URL**, and paste that feed URL.

The workflow attempts to refresh daily. Skylight's own polling interval determines when changes appear.

## Important

The Nutrislice API URL and school slug are inferred from the public menu URL and community API documentation. **They have not been live-tested.** The first workflow run will establish whether the endpoint and parser work for Clear Sky. Do not subscribe until the generated calendar contains verified menu items. The script deliberately fails instead of publishing an empty feed when the menu cannot be retrieved.

Some schools publish only partial menus or change food-item data structure. If the initial run fails or yields incomplete results, the endpoint or parser needs adjustment. This is not affiliated with Nutrislice or Douglas County School District.
