# Sim files and the community gallery

A sim file (`.qsim`) carries one scenario, with its seed, to any copy of Qognition. All sims are models, not predictions, and not advice for a real emergency.

## Make one

Choose **Build your own scenario** from the first screen, then:

1. Pick a starting point. Each one plays straight away.
2. Change what you like. Click the map to place things. The checklist shows what is missing, and one click adds it. **Undo** or `Ctrl+Z` steps back.
3. Press **Play this scenario** to try it.
4. Press **Share**, add your name and a line about it, and choose **Save .qsim file**.

**Advanced** shows the id, dates, timezone and ship parts.

## Open one

- Drop a `.qsim` file on the app's window, at any screen.
- In the builder: **Open**, then paste a link, or choose **Community**.
- From a terminal: `python main.py --open my_sim.qsim`, or with an `https://` link.
- Without a window: `python main.py --open my_sim.qsim --report` runs it and writes the Excel and CSV report.

The same file and seed give the same world on any copy of the same version.

## Publish one

**Share > Publish online** saves your file and opens this repository's upload page on GitHub in your browser. Nothing is uploaded by the app. You need a free GitHub account. If you don't have write access, GitHub turns your upload into a pull request.

Each pull request runs `python tools/publish_sim.py check`. Once it is merged to `main`, the sim appears under **Community** in everyone's app and on the [gallery page](../community/README.md). A maintainer adds an already-reviewed file with:

```bash
python tools/publish_sim.py add my_sim.qsim
```

## What "runs anywhere" means

A fresh copy of the repository doesn't hold the raw data, which is a separate 230 MB download. Sims built on made-up land with hand-set weather need nothing else, and the builder's starting points are made that way. The Share screen says which kind you have. A sim using recorded land, recorded weather or weather windows needs:

```bash
python tools/fetch_artifacts.py
```

The three gallery sims were run on a clean checkout with no data pack.

## Safety

Sim files come from strangers, so `stranded_physics/entities/simfile.py` treats them as untrusted:

- **Data only.** A file is JSON around scenario text. Nothing in it is run as code, and it can't name a file on your computer.
- **Limits.** 256 KB, 64 entities, 500 people, 240 hours.
- **Checked like a hand-written scenario.** Every value goes through the same rules as the builder. Anything unknown is refused.
- **Text.** Control and direction-changing characters are refused.
- **Evidence.** A sim can't use a shipped scenario's id, because results belong to that id.
- **Links.** `https` only, to public addresses, with each redirect checked, and a size limit.
- **The hash** catches damage in transit. It doesn't say who made a file or whether it is any good.

Nobody validates community sims. The app says so when you open one, and the report records it.

## Limits

- Ship scenarios can't be shared yet, because they only run from the command line.
- The map is always the 20 km grid the engine uses. A made-up island sits inside it.
- People need Python and this repository to run the app. There is no installer yet.
