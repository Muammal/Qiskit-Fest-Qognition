# 002: Add storm wind to what a person can notice

**Type:** additive. `Percept` gains `wind_m_s`, defaulting to 0, so existing scenarios behave as before.
**Why:** a storm-only scenario needs a way for someone to notice a storm, and `recent_events` already has a `storm` event in the frozen contract.

**Status:** made before the T-001 review, so it needs the owner's sign-off with the rest of the interfaces.
