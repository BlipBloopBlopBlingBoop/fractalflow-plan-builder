# Project patterns

The usual shape, the work that gets forgotten and the typical risks for common kinds of project. Use these to check a draft, not to replace what the person tells you. They are general patterns: every duration and lead time still comes from the person, their documents, or a labelled estimate.

For every type, ask about the waits. The time spent waiting on other people decides more finish dates than the time spent working.

## Construction, fit-out and renovation

**Shape:** brief and budget, design, permits, procurement, site preparation and demolition, structure, services rough-in, inspections, close-in and finishes, fixtures and fittings, final inspections, snagging, handover.

**Usually forgotten:**
- The permit: preparing the application, the review itself, answering comments, resubmission.
- Long-lead items ordered late: windows, cabinetry, switchgear, lifts, specialist equipment. Order as soon as the design fixes them, not when the site is ready for them.
- Inspections as hold points, with the wait for the inspector.
- Curing and drying time.
- Utility connections and the provider's lead time.
- Snagging, the fixes it produces, and the re-inspection.
- Handover: manuals, warranties, training, final accounts.

**Sequence notes:** rough-in services before closing walls; inspections before covering work; wet trades before finishes; one trade per area at a time unless the space allows more.

**Risks:** permit delays, hidden conditions found on opening up, weather, late deliveries, a trade unavailable when needed, design changes after work starts.

## Software and IT delivery

**Shape:** discovery and requirements, design, build in increments, integration, testing, security and compliance review, user acceptance, training, cutover, early-life support.

**Usually forgotten:**
- Environments and access: accounts, test data, firewall changes, licences.
- Data migration: mapping, trial runs, reconciliation, the final run.
- Test and fix cycles. Plan at least two rounds of acceptance testing with fixing time between.
- Security review, penetration testing and the fixes.
- Change approval boards and their meeting dates.
- Freeze periods when nothing may be released.
- Training, support handover, documentation.
- Cutover rehearsal and a rollback plan.
- Decommissioning the old system.

**Sequence notes:** plan the build as increments that each end in something testable. Integration belongs throughout, not at the end. Cutover is often a weekend: use a calendar-day task with a start-no-earlier-than date.

**Risks:** unclear requirements, dependence on another team's interface, key people split across projects, data quality, late discovery in testing, vendor delivery.

## Hardware and physical products

**Shape:** requirements, concept, detailed design, prototypes in rounds (build, test, learn, revise), certification and compliance testing, tooling, pilot run, production ramp, launch.

**Usually forgotten:**
- Each prototype round is a loop: build, test, analyse, change. Plan the number of rounds, not one pass.
- Tooling and component lead times, often the longest items in the plan.
- Certification: booking the lab, the test itself, failures and retests.
- Packaging, labelling, manuals, regulatory marks.
- Supplier qualification and first-article inspection.
- Logistics: shipping time, customs, distribution.

**Risks:** a failed test forcing a redesign, component shortages, tooling changes, supplier quality, certification retests.

## Events, openings and launches

**Shape:** the date is fixed, so plan backward from it: concept and budget, venue and date, suppliers and contracts, programme and content, promotion and registration, logistics, rehearsal, the day, close-out.

**How to plan:** end the preparation on a readiness milestone with a deadline the day before the event. Pin the event itself with `MSO` if the plan continues past it into close-out. `check` then shows the chain of work leading into the event with its float, and `--finish-by` finds the latest safe start. Anything with negative float is already late.

**Usually forgotten:**
- Deposit and contract deadlines, cancellation cut-offs.
- Permits, insurance, licences.
- Print and production deadlines, which are earlier than people expect.
- Speaker or performer confirmations and their materials.
- Rehearsal and a technical run-through.
- Teardown, returns, final payments, thank-yous, the review.

**Risks:** a key supplier or speaker dropping out, low registration, weather, a venue problem.

## Regulated and quality-gated work

Submissions, audits, validations, accreditations: work that ends with an outside body's decision, or that must pass formal quality gates.

**Shape:** plan and gap assessment, drafting, internal review and quality check, approval and sign-off, submission, the body's review, questions and responses, decision. For validations: plan, install and check, test in operation, report, release.

**Usually forgotten:**
- The document cycle: draft, review, comment resolution, quality check, approval. Each document goes round it, often more than once.
- Signatories being unavailable.
- Formatting, publishing and submission mechanics.
- The body's clock, in calendar days, and the time to answer its questions.
- Training people before they use a new procedure or system.
- Change control for anything altered after approval.

**Important:** timelines set by a regulator or standard change, and they often sit on the driving path. Take them from the person's documents or the body's current published guidance. If you use a general figure, mark it clearly as an assumption to confirm. Do not present a remembered figure as the rule.

**Risks:** review questions that need new work, a missing signatory, late data, findings that force rework, changes in the rules.

## Research and grant-funded projects

**Shape:** start-up (agreements, ethics or other approvals, hiring, purchasing), the work in phases or work packages, analysis, write-up, reporting to the funder, publication or handover.

**Usually forgotten:**
- Approvals before any work can start, and their review cycles.
- Hiring: advertising, interviews, notice periods, onboarding.
- Equipment purchasing rules and delivery.
- Reporting deadlines to the funder: use deadlines.
- Time to write, review with co-authors, and revise.
- Term dates, teaching loads, holidays when key people are away.

**Risks:** a hire arriving late, an approval taking longer than hoped, an experiment that has to be repeated, access to samples, data or sites.

## Moves and business change

**Shape:** decide and commit, design the new arrangement, prepare (space, systems, suppliers), communicate and train, switch over, settle in, close out the old arrangement.

**Usually forgotten:**
- Notice periods on the old arrangement, and their deadlines.
- Network and telecoms lead times, usually the longest wait.
- Address changes, insurance, access and security.
- Staff consultation and communication.
- Packing, labelling, moving, unpacking: often a weekend, in calendar days.
- Clearing and handing back the old site.

**Risks:** the new space not ready, connectivity late, a supplier missing the move date, disruption on day one.

## Campaigns and content

**Shape:** brief and goals, strategy and message, creative development, review and approval rounds, production, channel setup, launch, running the campaign, measurement and wrap-up.

**Usually forgotten:**
- Approval rounds, including legal and brand review.
- Booking deadlines for media and print.
- Asset versions for each channel.
- Tracking and reporting setup before launch.
- The time the campaign actually runs, as a calendar-day task.

**Risks:** late approvals, changes of message after production starts, a supplier missing a booking deadline.

## Choosing a supplier

**Shape:** requirements, market scan, request for proposals, supplier questions, proposals, evaluation, demonstrations and references, negotiation, contract, kick-off.

**Usually forgotten:** the internal approval to buy, the time suppliers need to respond (calendar days), legal and security review of the contract, the supplier's own start-up lead time.

**Risks:** too few responses, a protracted negotiation, a late change in requirements.
