# Every Rep Has a Spotter

*In the gym, a spotter doesn't lift the weight for you. They watch the bar, know when to step
in, and decide when a set is done. That's how I use an AI coding agent: it moves a lot of
weight, and I decide what gets lifted.*

Overloader is built with an AI coding agent (Claude Code) as a tool. This log records the calls
I made: where I set direction, steered, corrected or overruled the agent, set its limits, or
weighed a trade-off myself. The code shows *what* was built; this shows the engineering
judgment behind it.

Newest first. Each entry: the situation, what I decided, and why.

---

## How I work with the agent

Carried over from [Setups.Bike](https://github.com/GrantHolcombe/setups.bike):

- **No secrets in chat.** Passwords, keys and connection strings never pass through the
  conversation. I put them in `backend/.env` or the provider's console myself.
- **I approve every deploy and every delete.**
- **Local first.** Changes are checked on localhost before anything ships.
- **Docs stay current.** Roadmap, database notes and the style guide change in the same commit as
  the code, and the work is tracked on a private GitHub Project board.

---

## 2026-11-26: Stack, scope and where it runs

**Situation:** Starting a new portfolio project: a lifting log that makes progressive overload
easy to track.

**Decision:**
- **Scope for v1:** email sign-in, a searchable list of common gym equipment, quick logging of
  weight, reps and sets, the last entry always visible, and a chart of every log per exercise.
- **Stack:** Vue on the front end, Python FastAPI with Postgres on Neon on the back end. Both are
  deliberately different from Setups.Bike (React, Node Lambdas) to show range.
- **Sign-in:** by email, like Setups.Bike's one-time code, so there are no passwords to store
  or leak.
- **Where it runs:** a PWA on localhost first, the frontend headed for S3, and the API's host
  left open until I've compared options, rather than committing to one up front.
- **Visibility:** a public repo for the portfolio, with a private project board so the plan and
  backlog stay mine.

**Why:** A small, finished, well-tested app shows more than a large unfinished one. Deferring
the API host keeps the code portable (plain ASGI app, any Postgres URL) while I weigh cost and
cold-start trade-offs.
