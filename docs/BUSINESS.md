# Business case (one slide)

**Pain.** Each Fab or Asset Store listing means re-typing facts from the repo, writing marketing copy,
and resizing screenshots to 4–6 exact image specs per store. Sellers report this takes hours per
listing, and the result varies in quality. Listings also drift from the truth (claimed platforms,
modules or engine versions) and attract support tickets and refund requests.

**Audience.** Solo developers and small studios selling UE plugins on Fab and Unity packages on the
Asset Store, plus studios that ship internal plugin catalogues.

**Measured so far (from this repo's evals, not estimates):**
- Extraction on 10 real public plugin repos: **100% field accuracy** (`evals/results.md`). The
  facts a seller would otherwise copy by hand arrive pre-filled, each with its source file.
- Offline pipeline (extract → images for all slots → copy → zip) runs in under 2 s on the sample plugin
  (`storelistingkit selftest`).
- To measure next, with the protocol below: Claude generation time per store via `evals/run_evals.py
  --generate`, and the manual baseline.

**Time-saving protocol (for the demo).** Three people each produce one Fab listing by hand from a repo
plus screenshots (stopwatch), then one with the tool. Report the median of each. A listing "counts" only
when it passes the tool's validator, so both sides meet the same bar.

**Path to revenue.**
- Free: the offline template and single listings with your own API key.
- Paid: batch mode for catalogues (many plugins, many versions), team presets for tone and terms,
  and re-export when store specs change.
- Studio: internal deployment with house style guides as skills.
