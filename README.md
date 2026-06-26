# TOG Patch Monitor (cloud, free)

Runs the Tower of God patch check on **GitHub Actions** every 5 minutes — no PC
needed. When the bundle folder changes, it grabs the manifest and pings Discord.

## What it does each run
1. Polls `cdn_config` for app versions 3.11.00 → 3.20.00.
2. Compares the newest bundle folder to `state/last_folder.txt`.
3. On a new folder: downloads `bundles.zip` (the manifest), counts bundles,
   posts a Discord alert, and commits the new folder name to `state/`.
4. Also alerts if the server raises the minimum app version (forced-update signal).

You then **full-dump from your PC whenever you see the alert** — the `.ab` files
stay on the CDN, so there's no rush; only the manifest is time-sensitive (it gets
purged on the *next* patch), and the workflow already saves it as an artifact.

## Setup (5 minutes, one time)

1. **Create a Discord webhook**
   Discord → your server → a channel → Edit Channel → Integrations → Webhooks →
   New Webhook → Copy Webhook URL.

2. **Create a GitHub repo** (make it **Public** — public repos get *unlimited*
   Actions minutes; a private repo would burn through the 2000-min/month free cap
   at this frequency).

3. **Push these files** to the repo root:
   ```
   monitor_ci.py
   state/last_folder.txt
   .github/workflows/monitor.yml
   .gitignore
   ```

4. **Add the webhook as a secret**
   Repo → Settings → Secrets and variables → Actions → New repository secret →
   Name: `DISCORD_WEBHOOK`  Value: (paste the webhook URL).

5. **Enable Actions** (Actions tab → enable workflows if prompted).
   Open the workflow → "Run workflow" once to test — you should see it run, and on
   the first run it just sets the baseline (no alert).

That's it. From then on it checks every ~5 min on GitHub's servers. When a real
patch lands you get a Discord ping with the folder name + bundle count, and the
manifest is saved as an artifact on that workflow run.

## Notes
- GitHub cron is best-effort (can lag a few minutes under load) — fine for this.
- Scheduled workflows pause after ~60 days of **no repo activity**; the
  commit-on-change keeps it alive, but if there are no patches for that long, just
  push any commit (or hit "Run workflow") to wake it.
- To change the alert frequency, edit the `cron` line in `monitor.yml`.
- When you bump to a new app version, update `CUR_VER` in `monitor_ci.py` so the
  forced-update alert stays accurate.
