# Codex Execution Plans for this repository

This file defines the rules for an execution plan, called an ExecPlan. An ExecPlan is a single Markdown document that a coding agent can follow to deliver a working feature or environment change. Treat the reader as a complete beginner to this repository: they have only the current working tree and the ExecPlan file. They have no memory of previous chats.

## How to use ExecPlans

When authoring an ExecPlan, read this whole file first. When implementing an ExecPlan, keep the ExecPlan up to date as a living document. Do not ask the user for routine next steps. Resolve reasonable ambiguities in the plan, document the decision, and proceed. Ask the user only for information that cannot be safely inferred and blocks progress.

When implementing, update the `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections whenever there is meaningful progress, a change in design, an unexpected discovery, or a completed milestone.

## Non-negotiable requirements

Every ExecPlan must be self-contained. Include all required context, assumptions, commands, paths, expected outputs, and acceptance tests. Do not rely on the user remembering earlier conversations.

Every ExecPlan must produce demonstrably working behavior, not just files that compile. For this project, working behavior means something observable in QGIS, in the bridge HTTP API, in Mission Planner/SITL, or in automated tests.

Every term of art must be defined in plain language the first time it appears. For example, define MAVLink as the message protocol used by ArduPilot ground stations and vehicles; define SITL as Software-In-The-Loop simulation; define CRS as coordinate reference system.

All commands must include the intended working directory. Scripts must be idempotent where practical: running a setup script twice should not corrupt the environment or reinstall tools unnecessarily.

All safety-relevant MAVLink commands must be gated by checks for fresh heartbeat and known target system/component. QGIS v1 must not implement arming, disarming, parameter writes, joystick control, or RC override.

## Required ExecPlan sections

Each ExecPlan must contain these sections, in this order:

1. `Purpose / Big Picture` — what the user will be able to do after the work and how to see it working.
2. `Progress` — checkbox list with timestamps; keep it current.
3. `Surprises & Discoveries` — unexpected findings with short evidence.
4. `Decision Log` — decisions, rationale, date/author.
5. `Outcomes & Retrospective` — results, gaps, lessons learned.
6. `Context and Orientation` — current repo state, target architecture, definitions, important external facts already embedded in the plan.
7. `Plan of Work` — prose description of the sequence of edits/additions.
8. `Concrete Steps` — exact commands, working directories, and expected short outputs.
9. `Validation and Acceptance` — how to prove the feature works, including tests and manual SITL/QGIS checks.
10. `Idempotence and Recovery` — how to rerun, retry, clean, or roll back.
11. `Artifacts and Notes` — important generated files, logs, links, or follow-up notes.

## Formatting rules

When writing an ExecPlan to a standalone `.md` file, do not wrap the whole file in triple backticks. Use normal Markdown headings and lists. Avoid nested fenced code blocks if the plan itself will be pasted into a fenced block; use indented command blocks when needed.

Narrative sections should be prose-first. Tables are allowed when they clarify ports, files, or mode numbers. Checklists are mandatory only in `Progress`.

## Milestones

Break work into independently verifiable milestones. Each milestone should add one user-visible or test-visible capability. For this project, good milestones are:

- Environment check and installer scripts.
- MAVLink bridge receives SITL telemetry and exposes JSON status.
- QGIS plugin displays a live boat marker with heading.
- QGIS click tool transforms clicked/project CRS coordinates to WGS84.
- QGIS mode buttons send safe MAVLink mode commands.
- QGIS guided-target command sends a WGS84 target to Rover/Boat SITL.
- Documentation and packaging.

## Evidence examples

Include concise expected outputs, for example:

    PS C:\work\qgis-arduboat> .\scripts\run_bridge.ps1
    Bridge listening on http://127.0.0.1:8765
    MAVLink connected: system=1 component=1 mode=MANUAL

    PS C:\work\qgis-arduboat> Invoke-RestMethod http://127.0.0.1:8765/api/status
    connected mode    lat       lon       heading_deg
    -------- ----    ---       ---       -----------
    True      MANUAL  48.2082   16.3738   91.2

