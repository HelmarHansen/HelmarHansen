# Setup

This package is your profile repo. It only uses the Python standard library, nothing to install.

## 1. Create the repo

1. On GitHub, create a **public repo named exactly like your username** (e.g. `myname/myname`).
2. Copy the whole content of this folder into it (including the hidden `.github` folder).
3. Delete this file (`SETUP.md`) afterwards.

## 2. Configure

Everything personal lives in `profile.config.json`:

| Field | Meaning |
| --- | --- |
| `github_user` | Your GitHub username (required) |
| `name` | Drawn as a constellation of stars. Letters A–Z; short names look best |
| `tagline` | One line below the name. Empty = none |
| `config_lines` | Up to 3 lines (`key` and `value`) under the tagline |
| `accent` | Neon color (hex) |
| `lang` | `en` or `de` |
| `projects.count` | How many billboards in total (filled up with your most recently pushed repos) |
| `projects.pinned` | Repos that are always shown |
| `projects.exclude` | Repos that never appear |

## 3. Try it locally (optional)

```bash
python tools/profile/fetch.py --demo   # sample data, no network needed
python tools/profile/render.py         # draws assets/console/*.svg
python tools/profile/readme.py         # inserts the images into README.md
```

## 4. Update automatically

1. Push everything to the repo.
2. Open the **Actions** tab and enable workflows if GitHub asks.
3. Run the workflow once by hand via *Run workflow*. After that it runs daily.

Optional for private contributions: add a secret `PROFILE_TOKEN` under *Settings → Secrets and variables → Actions*, using a **fine-grained token** with read access. Without it, public data is used.

## Notes

- Everything in `README.md` outside `<!-- console:start -->` / `<!-- console:end -->` stays editable by hand.
- If fetching fails, the previous data stays; the profile is never emptied.
- GitHub caches images for a few minutes.
- With "reduce motion" enabled, animations are off.
- The pixel letters are based on Tiny5 (SIL OFL 1.1), see `tools/profile/OFL-Tiny5.txt`.
