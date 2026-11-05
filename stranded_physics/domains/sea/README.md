T1 constant sea temperature and immersion proxy

`Sea(time, temperature_c)` writes the constant `sea.temperature` series without
reading other domains. Temperature outside −5 to 40 °C raises `InterfaceError`.
The two scalar functions use a lognormal CDF, zero at zero exposure, with a
temperature-dependent median and optional lifebelt multiplier.

All curve parameters are labelled assumptions in `params.toml`. No published
0 °C distribution is in hand. The 20-minute freezing median is a round choice
within the task brief's swim-failure range; it is not a hypothermia timescale or
a fit to Titanic. Cold shock is not resolved separately. Titanic's −2 °C and
the −1.9 °C seawater freezing reference are from memory.

Both sea gates PASS; all 10 sea tests pass. See `verdicts.json` for input hashes
and [the shared handoff](../ship/REPORT.md) for all gate values, assumptions,
source limits and commands.
