# Security

## Reporting a problem

Please report security problems privately, through **Security > Report a vulnerability** on this repository's GitHub page. Don't open a public issue. We aim to reply within a week.

The most useful reports are `.qsim` files, gallery entries or links that get past the checks in [`stranded_physics/entities/simfile.py`](stranded_physics/entities/simfile.py), or that crash the app or hang it.

## What we treat as untrusted

Sim files, gallery lists and links can all come from strangers. The rules they must pass are in [docs/SIM_FILES.md](docs/SIM_FILES.md). The app never runs anything from a sim file as code.

The rest of the project is research software. It is meant to run on your own computer, and isn't built to be exposed as a network service.

## Not for real emergencies

Qognition is a research model. Don't use it to plan or make decisions in a real emergency.
