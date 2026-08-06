# Research — context engineering for Claude 5-gen + prompting Fable 5 (#574)

**Status:** COMPLETE
**Agent:** research delegate for #574 (node-granularity grill)
**Date:** 2026-08-06

## Sources

**Assigned (both PRIMARY, Anthropic-owned, read in full):**

1. <https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models>
   — `claude.com` blog. Fetched 2026-08-06. **Published July 24, 2026** (stated twice: fetch
   metadata `Published: 2026-07-24`, in-page `Date / July 24, 2026`). Byline: *"This article was
   written by Thariq Shihipar, member of technical staff, Anthropic."*
2. <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5>
   — `platform.claude.com` developer docs. Fetched 2026-08-06. **No date visible** (control-armed
   below).

**Followed because the assigned pages explicitly defer to them** (the brief authorised following
sub-pages that carry the substance — each of these carries an answer the assigned pages punt on):

3. <https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5>
   — source 2 defers *"API parameter changes… adaptive thinking only"* here. **This is the page
   that settles Q4.**
4. <https://platform.claude.com/docs/en/build-with-claude/effort> — source 2 defers the effort
   control here. Carries the full effort-level table.
5. <https://claude.com/blog/claude-models-explained-choosing-the-best-model-for-your-use-case>
   — **Published July 24, 2026**, sibling post linked from source 1. **This is the page that
   settles the maintainer's ruling, and it reverses my initial reading of source 2.**

### Fetch-method note (a durable harness fact worth keeping)

`WebFetch` was tried first on source 1 and **refused**: *"I can't reproduce the entire article
verbatim as requested. That would constitute reproducing substantial copyrighted material from
Anthropic's blog."* It returned a 5-line summary instead. Every verbatim quote below therefore
comes from `mcp__plugin_exa_exa__web_fetch_exa` (raw markdown, no intermediary model).
**`WebFetch` cannot be relied on for verbatim vendor-doc quotes** — it paraphrases or refuses, and
a paraphrase is not evidence under this repo's standard.

---

## ⚠️ Correction notice — read this before the sections below

Two things in my first draft of this report were wrong, and both are corrected in place:

1. **I initially concluded the vendor does NOT endorse "Fable plans, cheaper models execute."**
   That was based on sources 1–2 only, and it is **wrong**. Source 5 endorses exactly that pattern
   by name — the **advisor strategy** — with a measured result. The maintainer's ruling is
   **vendor-supported**, not merely cost-driven. Details in §3.
2. **My first-draft control-arm table published estimated hit counts read off the page rather than
   measured.** Seven of fifteen were wrong (e.g. I wrote `system prompt` → 6 in source 1; the real
   count is 14). Every count below is now `grep -oiE` over the fetched body text saved to disk. The
   *directions* were all correct; the *numbers* were not. This is the exact "an inherited/unmeasured
   number is not a measurement" trap in `probes-need-a-control-arm.md` rule 6, and I walked into it.

---

## 1. The new rules of context engineering for Claude 5 generation models

### Framing (verbatim)

> We removed over 80% of Claude Code's system prompt for more advanced models. How to apply the
> lessons we learned to your own context engineering in Claude Code and with your own agents.

> But when you send a message to Claude, the prompt is only a small part of the context it gets.
> Much of your context is assembled from your system prompt, Skills, CLAUDE.md files, memory, and
> other sources. We call this context engineering, and it makes a big impact on the results you
> generate when using Claude Code or in building your own agents.

> Unlike a prompt, context is used generally across many requests, so it cannot be as specific.
> How do you build these general prompts and guidance for Claude, especially when you don't know
> what a user's prompt might be?

> We removed over 80% of Claude Code's system prompt for models like Claude Opus 5 and Claude
> Fable 5 with no measurable loss on our coding evaluations.

> We've put these best practices in `claude doctor;` use the command /doctor in Claude Code to
> rightsize your skills, and CLAUDE.md files.

### Verbatim rules

#### Section: "Unhobbling Claude"

> Overall, we found that we were overconstraining Claude Code, both through our system prompt and
> in our CLAUDE.md files and skills.

> For example, when we read transcripts of our own internal usage of Claude Code, we see several
> conflicting messages in a single request like "leave documentation as appropriate," or "DO NOT
> add comments" as our system prompt, skills, and user requests clash with each other.

> Generally, Claude can interpret the user's intent to get to the right answer, but Claude must
> think more carefully about these overlapping and conflicting messages before deciding what to do.

> And while these constraints were once needed to avoid worst case scenarios, we have since found
> we can delete many of them and let the model use surrounding context and judgement instead.

> Additionally, Claude Code now has many more tools. Claude used to rely on CLAUDE.md as a source
> of memory, information, and guidance. Now we have memory, artifacts, and skills, which Claude can
> use to create new ways of loading and sharing context across sessions.

#### Section: "Then and now"

> There were a number of previous context engineering best practices that had become myths.
> Including:.

**Then: Give Claude rules → Now: Let Claude use judgement**

> When we first rolled out Claude Code, we needed to be sure that Claude avoided worst case
> scenarios, such as deleting files. This meant we would give particularly strong guidance that
> might not always be true, For example, in the system prompt we used to say:

> In code: default to writing no comments. Never write multi-paragraph docstrings or multi-line
> comment blocks — one short line max. Don't create planning, decision, or analysis documents
> unless the user asks for them — work from conversation context, not intermediate files.

> But for a certain subset of prompts, this guidance would be wrong. In the case of documentation,
> the user may have their own preferences, or specific parts of very complex code might need
> multi-line comment blocks.

> Still, without these guardrails for older models, the comments Claude wrote would be incorrect in
> many cases and we had to accept this tradeoff. But newer models have better judgement and can
> handle these decisions well without explicit rules.

> In the new system prompt we say: Write code that reads like the surrounding code: match its
> comment density, naming, and idiom.

**Then: Give Claude examples → Now: Design interfaces**

> The number one rule for tool usage was to give Claude examples on how to use them. With our
> newest models, we've found that giving examples actually constrains them to a certain exploration
> space.

> Instead of using examples, think more about the design of your tools, scripts and files- what
> parameters does Claude have and how can they be more expressive?

> For example, in the Todo tool example, just listing status as an enumeration between pending,
> in_progress, and completed, hints to Claude about how to use it. The instruction on keeping one
> item in_progress helps define our requested behavior.

**Then: Put it all upfront → Now: Use progressive disclosure**

> Because Claude Code was focused on coding, our system prompt included detailed information on how
> to do code review and verification. These were not always needed, but when they were, it was
> crucial information.

> Since then, Claude Code has gotten very competent at using progressive disclosure- loading the
> right context at the right times. For example, we moved verification and code review into their
> own skills that Claude Code could selectively call.

> But progressive disclosure is not just for skills, we also use it for tools. Some of our tools
> are 'deferred loading,' which means the agent must search for their full definitions using
> ToolSearch before using them. This allows us to have more tools (such as our Task tools) that
> don't take up context until they're needed.

> The same can be applied to your own CLAUDE.md and Skill.md files. A common myth is that you want
> to make these a central repository for every known practice that you might run into, because
> Claude would not find it otherwise. Instead, consider having a tree of files that can be loaded
> at the right time.

**Then: Repeat yourself → Now: Simple tool descriptions**

> Earlier Claude models could sometimes need repeated instructions or be more likely to listen to
> instructions at the end of their context window than at the start. This meant our system prompt
> would sometimes have references to tools in the main system prompt as well as instructions in the
> tool description.

> We found we could delete these repeat examples and put instructions on how to use tools in the
> tool descriptions rather than the system prompt.

**Then: Memory in CLAUDE.md files → Now: Auto-memory**

> We used to encourage users to save things to Claude's memory, by using the # hotkey to write to
> their CLAUDE.md automatically. Instead, Claude now automatically saves memories that are relevant
> to the work and to you.

**Then: Simple specs → Now: Rich references**

> In plan mode, Claude Code has heavily relied on markdown files with plans. Storing these files as
> plans helped Claude refer to them when needed. Another similar best practice was to store specs
> in the codebase for Claude to refer to while working across longer projects.

> But we've found that Claude can handle increasingly more complicated references. Instead of
> simple markdown files, Claude can reference HTML artifacts created by our new artifacts feature.

> You may also give Claude references in the form of code. A spec may also be a detailed test
> suite, or a function in a different codebase that Claude might port.

> Rubrics are another form of references. Rubrics allow Claude to try and verify your taste in a
> particular field (e.g. what does a good API design look like) by using dynamic workflows and
> spinning up verifier agents with those rubrics.

#### Section: "Applying this to your context" — the four layers

**System Prompt:**

> A system prompt is heavily tied to the product context. It tells Claude what product it's
> operating in and what it's doing. For Claude Code, you will likely never modify this, but if you
> are building your own agent harness, this is where you should spend a lot of time.

**CLAUDE.md:**

> Keep your CLAUDE.md lightweight and briefly describe what your repo is for, but spend most of the
> tokens on gotchas inside of the codebase. For example, you may organize your code to keep types
> in one monolithic file and nowhere else. Avoid stating 'the obvious' things Claude should know by
> looking at your file system or your repo.

> Use progressive disclosure heavily, for example if you have several unique instructions on how to
> verify your work, create a verification skill and reference it from your CLAUDE.md.

**Skills:**

> Think of skills as lightweight guides to let Claude find information when needed. Avoid making
> them overconstrained, except in highly important areas.

> For long skills, try and use progressive disclosure as much as possible- divide it into many
> files and split them out.

> It's best when skills encode particular opinions, knowledge, or best practices that are
> particular to you, your team, or product.

**References:**

> You can @ mention files to include them as references. References allow Claude to refer to
> in-depth information about the current plan.

> This might be in specs files, mockups, or even entire codebases. Generally you should prefer
> files that are in code as it provides clear, high-fidelity instructions to Claude in a language
> it knows very well. For example, a HTML mockup of a design will generally produce better results
> than a description of the design or a screenshot.

#### Section: "Try simplifying"

> Across your system prompt, skills, and CLAUDE.md files, you may need to simplify just like we
> did. We rolled out a new command called `claude doctor,` which will help you do this
> automatically as well. For more details on prompting more advanced models specifically, check out
> our Fable field guide.

### What it means for a per-stage agent brief

**Inference, labelled as such.** The article is about *context* — the general, cross-request layer.
A per-stage DAG brief straddles the categories: rendered per node (prompt-like), but templated
across tickets (context-like), so it inherits the generality problem the article opens with
(*"Unlike a prompt, context is used generally across many requests, so it cannot be as specific"*).
Mapping the rules onto brief design:

1. **The article gives no intra-prompt ordering guidance.** Its structural claim is about *layers*,
   not sequence. The only ordering statement is a **retired** one: earlier models were *"more
   likely to listen to instructions at the end of their context window than at the start"* —
   presented as the obsolete reason repetition was needed. **Inference:** recency-positioning tricks
   are no longer load-bearing; order the brief for legibility.
2. **Tool-usage instructions belong in tool descriptions, not the brief.** *"put instructions on
   how to use tools in the tool descriptions rather than the system prompt."*
3. **No examples in the brief.** *"giving examples actually constrains them to a certain
   exploration space."* This bites hardest on the `research` stage, whose value is breadth.
4. **The brief should be a pointer tree, not a payload.** *"consider having a tree of files that
   can be loaded at the right time."*
5. **The role definition is the high-leverage surface.** *"if you are building your own agent
   harness, this is where you should spend a lot of time."* The DAG is an agent harness; the
   rendered brief should carry only the ticket-specific delta.
6. **Conflicting instructions carry a real cost.** *"Claude must think more carefully about these
   overlapping and conflicting messages before deciding what to do."* A brief restating rules
   already in `AGENTS.md` is not neutral — it is a tax.

---

## 2. Prompting Claude Fable 5

Page self-description: *"Behavioral differences and prompting patterns for Claude Fable 5 and
Claude Mythos 5, covering effort, instruction following, long runs, memory, and scaffolding
changes."* It covers **both Fable 5 and Mythos 5**.

### Verbatim rules

#### Opening positioning

> Claude Fable 5 takes on problems that were previously too complex, long-running, or ambiguous for
> prior models, and is particularly effective at end-to-end work that takes a person hours, days,
> or weeks to complete. The teams seeing the best outcomes apply Claude Fable 5 to their hardest
> unsolved problems; testing it only on simpler workloads tends to undersell its capability range.
> It also performs reliably on more straightforward tasks.

> Claude Fable 5 has several behavioral differences from Claude Opus 4.8 that may require prompt or
> scaffolding updates. Capability improvements at this level are also a good prompt to re-evaluate
> which instructions, tools, and guardrails are still needed.

API callout:

> For API parameter changes specific to Claude Fable 5 and Claude Mythos 5 (adaptive thinking only,
> summarized-only thinking output, no extended thinking budgets, the `refusal` stop reason and
> fallback handling), see Introducing Claude Fable 5 and Claude Mythos 5.

Safety callout:

> Claude Fable 5 runs safety classifiers that target offensive cybersecurity techniques (such as
> building exploits, malware, or attack tooling), biology and life sciences content (such as lab
> methods or molecular mechanisms), and extraction of the model's summarized thinking. Benign
> cybersecurity work and beneficial life sciences tasks may also trigger these safeguards.

#### Section: "Capability improvements"

> Compared with Claude Opus 4.8, Claude Fable 5 shows improvement in:
>
> * **Long-horizon autonomy.** Claude Fable 5 sustains productive output over extended periods,
>   completing multiday, goal-directed runs with strong instruction retention across long, complex
>   tasks.
> * **First-shot correctness on complex, well-specified problems.** Early testers reported
>   single-pass implementations of systems that previously took days of iteration.
> * **Vision.** Claude Fable 5 interprets dense technical images, web applications, and detailed
>   screenshots with substantially higher accuracy, often while using fewer output tokens, and is
>   trained to use bash and crop tools to handle flipped, blurry, or noisy images.
> * **Enterprise workflows.** Claude Fable 5 follows instructions, stays in scope, and produces
>   professional-grade output on financial analysis, spreadsheets, slides, and documents.
> * **Code review and debugging.** Bug-finding recall (outside the cybersecurity domains the safety
>   classifiers cover) is noticeably higher than Claude Opus 4.8, including search across codebases
>   and repository history.
> * **Navigating ambiguity.** Claude Fable 5 performs well when given complex, multithreaded
>   requests and asked to determine next steps.
> * **Delegation and collaboration.** Claude Fable 5 is significantly more dependable at
>   dispatching and sustaining parallel subagents, and reliably manages ongoing communication with
>   long-running subagents and peer agents.

> Beyond these specific improvements, Claude Fable 5 is generally more capable than prior models on
> almost all tasks.

#### Section: "Longer turns by default"

> Individual requests on hard tasks can run for many minutes at higher effort settings, especially
> when the task requires gathering context, building, and self-verifying, and autonomous runs can
> extend for hours. This is one of the largest shifts teams encounter when adjusting to Claude
> Fable 5. Adjust client timeouts, streaming, and user-facing progress indicators before migrating,
> and consider restructuring harnesses to check on runs asynchronously, for example through
> scheduled jobs, rather than blocking.

Snippet — "To keep Claude Fable 5 from overplanning when a task is ambiguous":

> When you have enough information to act, act. Do not re-derive facts already established in the
> conversation, re-litigate a decision the user has already made, or narrate options you will not
> pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an
> exhaustive survey. This does not apply to thinking blocks.

#### Section: "Consider all effort levels"

> Effort is the primary control for the trade-off between intelligence, latency, and cost on Claude
> Fable 5. Use `high` as the default for most tasks, with `xhigh` for the most capability-sensitive
> workloads and `medium` or `low` for routine work. Lower effort settings on Claude Fable 5 still
> perform well and often exceed `xhigh` performance on prior models. Reduce effort if a task
> completes but takes longer than necessary, or if you want a quicker, more interactive working
> style.

> On routine work at higher effort, Claude Fable 5 can gather context and deliberate beyond what
> the task needs. At the same time, higher effort often produces excellent verification behavior,
> sophisticated reasoning, and the most rigorous output.

Snippet — "To prevent unrequested tidying or refactoring at higher effort":

> Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix
> doesn't need surrounding cleanup and a one-shot operation usually doesn't need a helper. Don't
> design for hypothetical future requirements: do the simplest thing that works well. Avoid
> premature abstraction and half-finished implementations. Don't add error handling, fallbacks, or
> validation for scenarios that cannot happen. Trust internal code and framework guarantees. Only
> validate at system boundaries (user input, external APIs). Don't use feature flags or
> backwards-compatibility shims when you can just change the code.

#### Section: "Strong instruction following"

> Instruction-following is improved enough that you can steer most behaviors with a brief
> instruction rather than enumerating each behavior by name. For example, when un-steered, Claude
> Fable 5 can elaborate beyond what the task needs, especially at higher effort settings: surveying
> options it won't pursue, explaining root causes at length, producing heavily-structured PR
> descriptions, or writing comments that narrate what the next line does. A short brevity
> instruction is as effective as listing each pattern:

> Lead with the outcome. Your first sentence after finishing should answer "what happened" or "what
> did you find": the thing the user would ask for if they said "just give me the TLDR." Supporting
> detail and reasoning come after. Being readable and being concise are different things, and
> readability matters more.
>
> The way to keep output short is to be selective about what you include (drop details that don't
> change what the reader would do next), not to compress the writing into fragments, abbreviations,
> arrow chains like A → B → fails, or jargon.

> The same applies to checkpoint behavior in long-running workflows. To have Claude Fable 5 stop
> only where it genuinely needs you, there is no need to enumerate every case:

> Pause for the user only when the work genuinely requires them: a destructive or irreversible
> action, a real scope change, or input that only they can provide. If you hit one of these, ask
> and end the turn, rather than ending on a promise.

#### Section: "Ground progress claims during long runs"

> On long autonomous runs, instruct Claude Fable 5 to audit progress against actual tool results.
> In Anthropic's testing, this nearly eliminated fabricated status reports even on tasks designed
> to elicit them:

> Before reporting progress, audit each claim against a tool result from this session. Only report
> work you can point to evidence for; if something is not yet verified, say so explicitly. Report
> outcomes faithfully: if tests fail, say so with the output; if a step was skipped, say that; when
> something is done and verified, state it plainly without hedging.

#### Section: "State the boundaries"

> Claude Fable 5 can occasionally take unrequested actions (drafting an email when none was asked
> for, creating defensive git-branch backups). Define explicit constraints on what Claude Fable 5
> should and should not do:

> When the user is describing a problem, asking a question, or thinking out loud rather than
> requesting a change, the deliverable is your assessment. Report your findings and stop. Don't
> apply a fix until they ask for one. Before running a command that changes system state (restarts,
> deletes, config edits), check that the evidence actually supports that specific action. A signal
> that pattern-matches to a known failure may have a different cause.

#### Section: "Parallel subagents" — LOAD-BEARING

> Claude Fable 5 dispatches parallel subagents more readily than prior models. Use subagents
> frequently, provide explicit guidance about when delegation is appropriate, and prefer
> asynchronous communication between orchestrator and subagents over blocking until each subagent
> returns. Long-lived subagents that keep their context across subtasks save time and cost through
> cache reads and avoid bottlenecking on the slowest subagent.

> Delegate independent subtasks to subagents and keep working while they run. Intervene if a
> subagent goes off track or is missing relevant context.

#### Section: "Construct a memory system"

> Claude Fable 5 performs particularly well when it can record lessons from previous runs and
> reference them. Provide a place to write notes, as simple as a Markdown file:

> Store one lesson per file with a one-line summary at the top. Record corrections and confirmed
> approaches alike, including why they mattered. Don't save what the repo or chat history already
> records; update an existing note rather than creating a duplicate; delete notes that turn out to
> be wrong.

#### Section: "Rare cases of early stopping"

> Deep into a long session, Claude Fable 5 can occasionally end a turn with a text-only statement
> of intent ("I'll now run X") without issuing the corresponding tool call, or pause to ask
> permission when it already has enough to proceed. A "continue" or "go ahead and do it end to end"
> suffices. […] For autonomous pipelines, add a system reminder:

> You are operating autonomously. The user is not watching in real time and cannot answer questions
> mid-task, so asking "Want me to…?" or "Shall I…?" will block the work. For reversible actions
> that follow from the original request, proceed without asking. Offering follow-ups after the task
> is done is fine; asking permission after already discussing with the user before doing the work
> is not. Before ending your turn, check your last paragraph. If it is a plan, an analysis, a
> question, a list of next steps, or a promise about work you have not done ("I'll…", "let me know
> when…"), do that work now with tool calls. End your turn only when the task is complete or you
> are blocked on input only the user can provide.

#### Section: "Rare cases of context-budget concern" — LOAD-BEARING

> In very long sessions, Claude Fable 5 can occasionally suggest a new session, offer to summarize
> and hand off, or trim its own work. This is most often triggered when the harness shows a
> remaining-token countdown to the model. Avoid surfacing explicit context-budget counts where
> possible. If the harness must show them, a reassurance helps:

> You have ample context remaining. Do not stop, summarize, or suggest a new session on account of
> context limits. Continue the work.

#### Section: "Give the reason, not only the request" — LOAD-BEARING FOR BRIEF DESIGN

> Claude Fable 5 tends to perform better when it understands the intent behind a request: context
> lets it connect the task to relevant information rather than inferring intent on its own. Provide
> context about why you're asking, especially for long-running agents drawing on multiple
> workstreams:

> I'm working on [the larger task] for [who it's for]. They need [what the output enables]. With
> that in mind: [request].

#### Section: "Readability when communicating with the user"

> Terse shorthand is fine between tool calls (that's you thinking out loud, and brevity there is
> good). Your final summary is different: it's for a reader who didn't see any of that.
>
> If you've been working for a while without the user watching (overnight, across many tool calls,
> since they last spoke), your final message is their first look at any of it. Write it as a
> re-grounding, not a continuation of your working thread: the outcome first, then the one or two
> things you need from them, each explained as if new. The vocabulary you built up while working is
> yours, not theirs; leave it behind unless you re-introduce it.
>
> When you write the summary at the end, drop the working shorthand. Write complete sentences.
> Spell out terms. Don't use arrow chains, hyphen-stacked compounds, or labels you made up earlier.
> When you mention files, commits, flags, or other identifiers, give each one its own plain-language
> clause. Open with the outcome: one sentence on what happened or what you found. Then the
> supporting detail. If you have to choose between short and clear, choose clear.

#### Section: "Create a send-to-user tool" — LOAD-BEARING FOR THE DAG'S DELIVERY PROBLEM

> When running long, asynchronous agents, give the agent a way to surface a message the user must
> see exactly as written, without ending its turn […] The tool's input is the message to display;
> when Claude calls it, render the input directly in your UI and return a simple acknowledgement as
> the tool result. **Tool inputs are never summarized, so the content arrives intact.**

> Add this tool whenever your UX depends on delivering content or direct user interactions verbatim
> mid-task. For agents that only narrate routine progress, the model's own summaries are typically
> adequate. **Defining the tool is not sufficient on its own; without an instruction in the system
> prompt, Claude Fable 5 rarely calls it.** Pair the tool with elicitation language such as:

> Between tool calls, when you have content the user must read verbatim (a partial deliverable, a
> direct answer to their question), call the send_to_user tool with that content. Use send_to_user
> only for user-facing content, not for narration or reasoning.

#### Section: "Recommended scaffolding changes"

> * **Start at the top of your difficulty range.** Pick a task harder than what you'd assign to
>   prior models, and have Claude Fable 5 scope it, ask clarifying questions, and execute.
> * **Make self-verification explicit in long-run prompts.** Separate, fresh-context verifier
>   subagents tend to outperform self-critique. For long-running tasks, instruct: `Establish a
>   method for checking your own work at an interval of [X] as you build. Run this every [X
>   interval], verifying your work with subagents against the specification.`
> * **Refactor existing prompts and skills.** Skills developed for prior models are often too
>   prescriptive for Claude Fable 5 and can degrade output quality. Review and consider removing
>   older instructions if default performance is better.
> * **Don't instruct Claude to reproduce its reasoning in the response.** Prompts, skills, or
>   harness instructions that tell the model to echo, transcribe, or explain its internal reasoning
>   as response text can trigger the `reasoning_extraction` refusal category on Claude Fable 5,
>   causing elevated fallbacks to Claude Opus 4.8.
> * **Create a send-to-user tool.** For long, asynchronous agents, a client-side tool delivers
>   messages to the user verbatim without ending the turn.

### Does the vendor position Fable as orchestrator, worker, or both?

**On sources 1–2 alone: BOTH, leaning WORKER.** On the full evidence including source 5: **the
vendor positions Fable as capable of both, and separately endorses using it as an ADVISOR over
cheaper workers as a cost strategy.** Both halves matter, so here is the evidence separated.

**Fable as WORKER / end-to-end executor** (source 2):

- *"is particularly effective at end-to-end work that takes a person hours, days, or weeks to
  complete"*
- *"The teams seeing the best outcomes apply Claude Fable 5 to their hardest unsolved problems;
  testing it only on simpler workloads tends to undersell its capability range."*
- *"First-shot correctness on complex, well-specified problems. Early testers reported single-pass
  implementations of systems that previously took days of iteration."* — an **implement**-stage claim.
- *"Code review and debugging. Bug-finding recall … is noticeably higher than Claude Opus 4.8"* — a
  **review**-stage claim, stated as a comparative advantage over Opus.
- *"Start at the top of your difficulty range. Pick a task harder than what you'd assign to prior
  models, and have Claude Fable 5 scope it, ask clarifying questions, and execute."*
- *"It also performs reliably on more straightforward tasks."*

**Fable as ORCHESTRATOR** (source 2):

- *"Delegation and collaboration. Claude Fable 5 is significantly more dependable at dispatching
  and sustaining parallel subagents, and reliably manages ongoing communication with long-running
  subagents and peer agents."*
- *"Claude Fable 5 dispatches parallel subagents more readily than prior models. Use subagents
  frequently…"*
- *"Navigating ambiguity. Claude Fable 5 performs well when given complex, multithreaded requests
  and asked to determine next steps."*

**The reading of source 2 in isolation (inference):** its framing is *"Fable is better at
everything, and orchestrating is among the things it is better at."* The orchestration language is
a **capability** claim, not a **role restriction**; source 2 never says "use Fable to plan and a
cheaper model to execute." **This is what I initially reported, and taken alone it is accurate —
but it is not the whole vendor position.** See §3.

---

## 3. The advisor strategy — the vendor DOES endorse the maintainer's ruling (source 5)

This is the single most decision-relevant finding, and it is **not** in either assigned source.
From *"Claude models explained: choosing the best model for your use case"* (July 24, 2026),
section **"Combining models' strengths with the advisor strategy"**, verbatim:

> The advisor strategy allows faster, lower-cost worker models to call more intelligent models to
> check their plan and evaluate their work, leading to improved performance.

> This method, where the executor model is coached only when needed, improves performance by a
> substantial amount. For example, on SWE-bench Pro Sonnet 5 with a Fable 5 advisor is within 10%
> of Fable 5's score at 63% of the price of using Fable 5 for the whole task.

**This is the maintainer's ruling, named and measured by the vendor.** "Fable is reserved for
planning / advising" is precisely *"worker models call more intelligent models to check their plan
and evaluate their work."* The measured trade is **within 10% of quality at 63% of price**.

Note the *direction of control*, which differs from a naive DAG reading: in the advisor strategy the
**worker calls the advisor**, on demand — *"the executor model is coached only when needed"* — rather
than an expensive planner rendering briefs for every downstream node up front. **Inference:** a
design where Fable is consulted *on demand by a stage that is stuck or about to commit* extracts
more of the 63%-price benefit than one where Fable runs a fixed planning node on every ticket.

### Model-class positioning (source 5, section "The Claude model family"), verbatim

> **Mythos / Fable** — Mythos is Anthropic's most capable model class, with frontier capabilities
> across domains. This model class is especially capable at coding, long-running agent tasks, and
> solving problems AI has not reliably handled before.

> The Mythos class ships in two packages of the same underlying model. Claude Mythos is for trusted
> organizations handling dual-use cybersecurity and biology work while Claude Fable is packaged
> with additional safeguards that make the model safe for use by the general public.

> **Opus** — Opus is our powerful model class for reasoning-intensive enterprise tasks. […] The
> choice between Opus and Fable may not seem clear on the surface, as both excel at coding,
> long-running agents, and knowledge work. In real-world situations, larger models such as Fable
> tend to have more wisdom, creativity, and writing skills despite having similar benchmark scores
> to models such as Opus.

> The general rule of thumb is if your evals or internal testing show Opus struggling on some
> tasks, then Fable is the answer. If Opus already clears the quality bar, then its speed and price
> profile may make it the better choice.

> **Sonnet** — Sonnet is our versatile model class for everyday tasks. Sonnet provides a balance of
> performance, cost, and speed for the widest set of general purpose use cases, **including
> high-volume sub-agents in multi-agent orchestration setups.**

> **Haiku** — Haiku is our lowest cost and fastest model class. Haiku models are designed for
> high-frequency workloads where latency and cost matter.

**Sonnet is named by the vendor as the subagent class**, which directly supports the maintainer's
haiku/sonnet/opus stage mapping.

### The "start smart" default, and the cost-per-task argument (source 5), verbatim

> our default recommendation is to start with the most intelligent generally available model and
> use effort level to dial in performance and cost.

> Cost-per-task is often lower for more intelligent models, especially at lower effort levels, even
> if the price-per-token is higher. This is because more capable models often take fewer turns and
> less thinking time to get most tasks right. Starting with a smaller model can also make it harder
> to distinguish between model failures and setup failures.

> Of course, as use cases arise that are more latency or cost-sensitive, you can test lower tier
> models until you find your ideal fit.

> Higher-class models at higher efforts offer the best possible performance, and higher-class
> models at lower efforts can sometimes be more efficient than smaller models.

**This is a genuine tension with the ruling, and the maintainer should see it.** The vendor's
default is *start with the most capable model and turn effort DOWN*, not *start with a cheap model
per stage*. Two of its stated reasons bite on a DAG specifically: cheaper models *"take more turns"*
(a DAG node that loops more is a longer, not cheaper, node), and *"Starting with a smaller model
can also make it harder to distinguish between model failures and setup failures"* — which in a
brand-new DAG harness is exactly the debugging problem you do not want to add.

The vendor's model-selection questions, verbatim:

> How hard is this task? If it typically takes a lot of time, involves multiple steps, or is
> previously unsolved then a more capable model class is appropriate.

> What are the latency needs? If the model is involved in high-frequency customer facing workloads,
> then Sonnet is often the best choice.

> What are the unit economics? Higher volumes of production may be more appropriate for lower
> classes of models, particularly if evaluations show those tasks are completed satisfactorily.

And on how to decide, verbatim: *"There is no one-size-fits-all approach to AI model selection […]
the best way to select a model is to understand the basics of each model class and understand your
use case in-depth. That means building, maintaining, and deploying strong evaluations."* Also worth
noting for anyone tempted to cite the article's graphs: *"Curves are illustrative and not plotted
from benchmark data."*

---

## 4. Effort and thinking (sources 3 and 4) — Q4 settled

### Thinking cannot be disabled on Fable — CONFIRMED, verbatim

Source 3, section **"Adaptive thinking is always on"**:

> Claude Fable 5 and Claude Mythos 5 always have thinking enabled; passing
> `thinking: {"type": "disabled"}` is not supported. To reduce or otherwise control thinking depth,
> use the [effort](/docs/en/build-with-claude/effort) parameter.

Section **"Raw thinking content is never returned"**:

> The raw chain of thought is never returned on Claude Fable 5 and Claude Mythos 5. The
> `thinking.display` setting controls what thinking blocks contain instead:
> * `"summarized"` returns thinking blocks with a readable summary of the reasoning.
> * `"omitted"` (the default) returns thinking blocks with an empty `thinking` field.

**Note the correction this forces on the assigned source:** source 2 (the Fable prompting page)
contains **zero** occurrences of "disable" (measured, control below). The claim is real but it lives
on source 3, not source 2. Anyone citing the prompting page for it would be citing a page that does
not say it.

### Fable 5 specs and price (source 3), verbatim

> * **Context window and output:** a 1M token context window by default, and up to 128k output
>   tokens per request.
> * **Pricing:** $10 USD per million input tokens and $50 USD per million output tokens.

Availability: *"Claude Fable 5 and Claude Mythos 5 both become available on June 9, 2026"* — which
dates the Fable generation. Also: *"Claude Fable 5 and Claude Mythos 5 carry 30-day data retention
and are not available under zero data retention."*

### The full effort table (source 4), verbatim

> | Level | Description | Typical use case |
> | `max` | Absolute maximum capability with no constraints on token spending. | Tasks requiring the deepest possible reasoning and most thorough analysis |
> | `xhigh` | Extended capability for long-horizon work. | Long-running agentic and coding tasks (over 30 minutes) with token budgets in the millions |
> | `high` | High capability. Equivalent to not setting the parameter. | Complex reasoning, difficult coding problems, agentic tasks |
> | `medium` | Balanced approach with moderate token savings. | Agentic tasks that require a balance of speed, cost, and performance |
> | `low` | Most efficient. Significant token savings with some capability reduction. | **Simpler tasks that need the best speed and lowest costs, such as subagents** |

**There are FIVE levels, not the four named on the prompting page** — `max` exists and the
prompting page omits it. And **the vendor names subagents as the `low`-effort use case**, which is
directly applicable to the DAG's worker nodes.

Other load-bearing effort facts, verbatim:

> The effort parameter affects **all tokens** in the response, including: Text responses and
> explanations; Tool calls and function arguments; Thinking (when active).

> Effort is a behavioral signal, not a strict token budget. At lower effort levels, Claude will
> still think on sufficiently difficult problems, but it will think less than it would at higher
> effort levels for the same problem.

> Setting `effort` to `"high"` produces exactly the same behavior as omitting the `effort`
> parameter entirely.

Recommended for Fable specifically (source 4, "Recommended effort levels for Claude Fable 5"):

> Effort is the primary control for trading off intelligence, latency, and cost on Claude Fable 5.
> **Start with `high`, the default, for most tasks**, use `xhigh` for the most capability-sensitive
> workloads, and step down to `medium` or `low` for routine work. […] At `high` and `xhigh`, set a
> large `max_tokens`: it is a hard limit on total output, thinking plus response text.

**Effort under tool use** (matters for a tool-heavy DAG node), verbatim:

> Lower effort levels tend to: Combine multiple operations into fewer tool calls; Make fewer tool
> calls; Proceed directly to action without preamble; Use terse confirmation messages after
> completion.
> Higher effort levels may: Make more tool calls; Explain the plan before taking action; Provide
> detailed summaries of changes; Include more comprehensive code comments.

**⚠️ Effort invalidates prompt caching — directly relevant to node granularity**, verbatim:

> Because effort shapes the rendered prompt, changing it between requests does not preserve cached
> prefixes from earlier turns; if you rely on prompt caching across a long session, pick an effort
> level at the start and keep it constant.

> **Hold effort constant within cached conversations:** Changing the effort value between requests
> invalidates prompt caching, so vary effort across workloads rather than within a conversation
> that relies on cache hits.

**Inference:** if the DAG varies effort *per stage* inside one long-lived session, it destroys the
cache on every stage transition. Varying effort *across separate node processes* is the shape the
vendor endorses (*"vary effort across workloads"*) — which is an argument **for** the DAG's
process-per-stage design, and cuts against my earlier suggestion to merge stages into one
long-lived session. Both effects are real and they pull in opposite directions; see the revised
suggestion 1.

---

## Direct answers to the five questions

### Q1. Context engineering for Claude 5-gen: what changes? Brief structure/ordering, system vs user turn, tool results, long-horizon work

**What changed** (source 1), the six retired myths:

| Then | Now |
|---|---|
| Give Claude rules | Let Claude use judgement |
| Give Claude examples | Design interfaces |
| Put it all upfront | Use progressive disclosure |
| Repeat yourself | Simple tool descriptions |
| Memory in CLAUDE.md files | Auto-memory |
| Simple specs | Rich references |

Magnitude: *"We removed over 80% of Claude Code's system prompt … with no measurable loss on our
coding evaluations."*

**Brief structure and internal ordering — the sources are SILENT, and I must say so.** Source 1
gives a *layer* model (system prompt / CLAUDE.md / skills / references) with no guidance on ordering
within a single prompt. The only ordering statement is the *retired* recency claim (*"more likely
to listen to instructions at the end of their context window than at the start"*). The nearest
thing to a positive shape recommendation is source 2's **"Give the reason, not only the request"**
template: *"I'm working on [the larger task] for [who it's for]. They need [what the output
enables]. With that in mind: [request]."* — which does imply **why before what**.

**System vs user turn — ABSENT from all five sources.** Zero occurrences of "user turn" or "user
message" in either assigned source (control armed below). Source 1 treats the system prompt as a
*layer*; source 2 mentions "system prompt" only for the send-to-user elicitation, the
autonomous-pipeline reminder, and the migration audit. **No source tells you what to put in the
user turn versus the system prompt.** If the design needs that split justified, it cannot be
grounded here.

**Tool-result handling — nearly absent.** Source 1 says nothing about tool *results* (0 hits for
"tool result"); it addresses tool *definitions* and deferred loading. The relevant statements are:
source 2's *"Tool inputs are never summarized, so the content arrives intact"*; source 2's *"Before
reporting progress, audit each claim against a tool result from this session"*; source 4's *"the
effort parameter affects … Tool calls and function arguments"*; and source 3 listing *"Tool result
clearing through context editing"* as a supported feature.

**Long-horizon / multi-turn agentic work — the richest area:**
- *"consider restructuring harnesses to check on runs asynchronously, for example through scheduled
  jobs, rather than blocking"* (src 2).
- *"prefer asynchronous communication between orchestrator and subagents over blocking until each
  subagent returns"* (src 2).
- *"Before reporting progress, audit each claim against a tool result from this session"* — which
  Anthropic reports *"nearly eliminated fabricated status reports"* (src 2).
- *"Separate, fresh-context verifier subagents tend to outperform self-critique"* (src 2).
- The autonomous-pipeline reminder and the end-of-turn promise check (src 2).
- `xhigh` is defined for *"Long-running agentic and coding tasks (over 30 minutes) with token
  budgets in the millions"* (src 4).

### Q2. How much context to give an agent — does more help or hurt?

**No source states a token figure, a context-size recommendation, or a measured volume trade-off.**
Zero hits for context-size figures in either assigned source (control armed below). The 78–85k
question is **not directly answered by the vendor**. What the sources support:

**More context HURTS when it is prescriptive:**
- The 80% removal *"with no measurable loss"* — a direct measurement that most accumulated system
  prompt was worthless. (It says removal cost nothing; it does not say the content was harmful.)
- *"we found that we were overconstraining Claude Code, both through our system prompt and in our
  CLAUDE.md files and skills."*
- The conflict cost: *"Claude must think more carefully about these overlapping and conflicting
  messages before deciding what to do."* — the one explicit *cost* claim, and it is about
  **conflict**, not volume.
- *"giving examples actually constrains them to a certain exploration space"* — an active
  **narrowing** claim.
- *"Skills developed for prior models are often too prescriptive for Claude Fable 5 and **can
  degrade output quality**"* (src 2) — an explicit degradation claim.
- *"Avoid stating 'the obvious' things Claude should know by looking at your file system or your
  repo."*

**More context HELPS when it is intent or high-fidelity reference:**
- *"Claude Fable 5 tends to perform better when it understands the intent behind a request: context
  lets it connect the task to relevant information rather than inferring intent on its own. Provide
  context about why you're asking, especially for long-running agents drawing on multiple
  workstreams."*
- *"Claude can handle increasingly more complicated references"*, and *"you should prefer files that
  are in code as it provides clear, high-fidelity instructions."*
- Fable has a **1M token context window** (src 3) — so 78–85k is ~8% of the window, not a capacity
  problem.

**Synthesis (inference, mine).** The vendor draws the line at **kind, not volume**. Intent ("why")
and high-fidelity references (code, tests, specs) are endorsed with no volume caveat; prescriptive
rules, examples and restated obvious facts are what Anthropic deleted 80% of and what it says
*degrades* output. **78–85k is not condemned by size; it is condemned exactly to the extent it is
prescriptive.** That split is measurable in this repo and I would measure it before treating the
number as the problem.

**Two cost mechanics the vendor supplies that the raw token count hides:**
- *"Long-lived subagents that keep their context across subtasks save time and cost through cache
  reads"* (src 2) — a fresh process per node pays full price with zero cache reuse.
- *"Cost-per-task is often lower for more intelligent models, especially at lower effort levels,
  even if the price-per-token is higher […] more capable models often take fewer turns"* (src 5) —
  so per-node token count is the wrong cost metric; **cost per completed ticket** is the right one.

### Q3. Fable 5 — good at, bad at, prompting shape, orchestrator or worker

**Good at:** long-horizon autonomy; first-shot correctness on complex well-specified problems;
vision; enterprise workflows; code review and debugging; navigating ambiguity; delegation and
collaboration. Plus *"generally more capable than prior models on almost all tasks"*, and (src 5)
*"more wisdom, creativity, and writing skills"* than Opus at similar benchmark scores.

**Bad at / failure modes:** overplanning on ambiguous tasks; over-deliberation and unrequested
tidying at high effort on routine work; elaborating beyond need; unrequested actions (*"drafting an
email when none was asked for, creating defensive git-branch backups"*); early stopping (*"I'll now
run X"* with no tool call); context-budget anxiety when shown a token countdown; unreadable final
summaries; and **hard refusals** on offensive cyber, bio/life-sciences, and *reasoning extraction*
→ `stop_reason: "refusal"` with fallback to Opus 4.8.

**Prompting shape:** short and intent-bearing, not enumerative. *"Instruction-following is improved
enough that you can steer most behaviors with a brief instruction rather than enumerating each
behavior by name … A short brevity instruction is as effective as listing each pattern."* Give the
**reason**, not only the request. Never ask it to reproduce its reasoning.

**Orchestrator or worker:** **both, per source 2** — the capability list includes *"single-pass
implementations"* (worker) and *"dispatching and sustaining parallel subagents"* (orchestrator), and
it explicitly warns that *"testing it only on simpler workloads tends to undersell its capability
range."* **But source 5 independently endorses the advisor pattern** — *"faster, lower-cost worker
models … call more intelligent models to check their plan and evaluate their work"* — at *"within
10% of Fable 5's score at 63% of the price."* **So the vendor agrees with the maintainer's ruling,
and I was wrong to report otherwise from the assigned sources alone.**

### Q4. Effort levels and thinking

**Five levels:** `max`, `xhigh`, `high` (default), `medium`, `low` (src 4). The Fable prompting page
names only four — it omits `max`.

**For Fable:** *"Start with `high`, the default, for most tasks"*, `xhigh` for capability-sensitive
work, `medium`/`low` for routine. *"Lower effort settings on Claude Fable 5 still perform well and
often exceed `xhigh` performance on prior models."* *"Effort is the primary control for the
trade-off between intelligence, latency, and cost."*

**Thinking cannot be disabled on Fable — CONFIRMED** (src 3, not src 2): *"Claude Fable 5 and Claude
Mythos 5 always have thinking enabled; passing `thinking: {"type": "disabled"}` is not supported.
To reduce or otherwise control thinking depth, use the effort parameter."* Raw chain of thought is
never returned; `thinking.display` is `"summarized"` or `"omitted"` (default). Do **not** cite the
prompting page for this claim — it contains zero occurrences of "disable".

**Also:** effort is *"a behavioral signal, not a strict token budget"*; `high` ≡ omitting the
parameter; effort affects tool calls too; **changing effort invalidates prompt caching**.

### Q5. Multi-agent orchestration, delegation, cross-model handoff

1. *"Use subagents frequently, provide explicit guidance about when delegation is appropriate, and
   prefer asynchronous communication between orchestrator and subagents over blocking."*
2. *"Long-lived subagents that keep their context across subtasks save time and cost through cache
   reads and avoid bottlenecking on the slowest subagent."*
3. *"Delegate independent subtasks to subagents and keep working while they run. Intervene if a
   subagent goes off track or is missing relevant context."*
4. *"Separate, fresh-context verifier subagents tend to outperform self-critique."*
5. Rubric-driven verifiers (src 1): *"Rubrics allow Claude to try and verify your taste in a
   particular field … by using dynamic workflows and spinning up verifier agents with those
   rubrics."*
6. Harness shape: *"check on runs asynchronously, for example through scheduled jobs, rather than
   blocking."*
7. **Cross-MODEL handoff — the advisor strategy** (src 5): worker calls advisor on demand,
   *"the executor model is coached only when needed"*, measured at within 10% / 63% price.
8. **Sonnet is the named subagent class** (src 5): *"including high-volume sub-agents in
   multi-agent orchestration setups."* **`low` effort's named use case is subagents** (src 4).
9. **Failure-driven handoff:** refusal → *"configure server-side or client-side fallback to Claude
   Opus 4.8"*, with *"fallback credit refunds the prompt-cache cost of switching"* (src 3).

**Still absent even across all five sources:** any guidance on **cross-FAMILY** review (Claude vs
GPT vs Gemini). The design's adversarial cross-family review is **unaddressed** by the vendor —
neither endorsed nor refuted. The vendor justifies adversarial review on **context freshness**
(*"separate, fresh-context verifier subagents"*), not on model diversity.

---

## Control arms run

**Method (stated so the numbers are re-derivable, not inherited).** The fetched body text of both
assigned sources was written to disk, then counted with
`grep -oiE '<pattern>' <file> | wc -l` (occurrence counts, case-insensitive, not line counts).
Files: `…/scratchpad/574src/src1-context-engineering.md`,
`…/scratchpad/574src/src2-prompting-fable-5.md`.
**Caveat on the method:** the saved text is the article/doc body as returned by the fetcher; site
navigation, footer and "related posts" chrome are trimmed. Counts are therefore *body* counts. This
does not affect any absence conclusion (a term absent from the body and present only in a nav menu
would not be a substantive hit anyway).

| Probe | Source | Count | Control term | Control count | Discriminates? |
|---|---|---|---|---|---|
| `orchestrat[a-z]*` | src 1 | **0** | `context` | 19 | yes |
| `sub-?agent[s]?` | src 1 | **0** | `tool[s]?` | 14 | yes |
| `user (turn\|message)` | src 1 | **0** | `system prompt` | 14 | yes |
| `tool result[s]?` | src 1 | **0** | `tool[s]?` | 14 | yes |
| `haiku\|sonnet` | src 1 | **0** | `opus` | 1 | yes |
| `token[s]?` | src 1 | **1** (*"spend most of the tokens on gotchas"* — a budgeting metaphor, not a size figure) | `context` | 19 | yes |
| `context window` | src 1 | **1** (the *retired* recency claim only) | `progressive disclosure` | 5 | yes |
| date string | src 1 | **2** (`2026-07-24`, `July 24, 2026`) | — | — | probe finds dates when present |
| `orchestrator` | src 2 | **1** (*"between orchestrator and subagents"*) | `sub-?agent[s]?` | 14 | yes |
| `user (turn\|message)` | src 2 | **0** | `system prompt[s]?` | 2 | yes |
| `disabl[a-z]*` | src 2 | **0** | `thinking` | 12 | yes |
| `haiku\|sonnet` | src 2 | **0** | `opus` | 5 | yes |
| `cheaper\|routing\|rout(e\|ing)` | src 2 | **2** (both *"re-route declined requests"* / fallback — **not** model routing) | `cost[s]?` | 2 | yes |
| `context window\|[0-9]+[km] token` | src 2 | **0** | `context` | 12 | yes |
| `effort` | src 2 | 12 | — | — | (control for the thinking/disable probe) |
| date / "last updated" | src 2 | **0** | same regex on src 1 | 2 | **yes — the date probe demonstrably finds dates, so src 2's datelessness is a real negative** |

**Key negatives, each with its arm:**
- **"Does the vendor route work by model class?" → NO, not in the assigned sources.** `haiku|sonnet`
  → **0** in both, while `opus` → 1 and 5 respectively, so the probe can see model names. The
  model-class guidance lives on source 5, which the assigned pages link but do not contain.
- **"Does the Fable prompting page say thinking can't be disabled?" → NO.** `disabl*` → **0** in
  src 2, control `thinking` → 12. The claim is real but lives on source 3.
- **"Is there a context-size number?" → NO.** Size-figure regex → 0 in src 2, `context` → 12.
- **"Is there user-turn vs system-turn guidance?" → NO.** 0 in both, controls 14 and 2.

**Correction to my own first draft:** seven of the counts I published before measuring were wrong —
src 1 `context` (I wrote 14, actual 19), src 1 `system prompt` (6 → **14**), src 1 `tool` (12 → 14),
src 2 `orchestrator` (2 → **1**), src 2 `subagent` (9 → **14**), src 2 `effort` (8 → **12**), src 2
`thinking` (6 → **12**), src 2 `system prompt` (3 → 2), src 2 `cost` (3 → 2). Every *direction* held;
no conclusion changes. The numbers above are the measured ones.

---

## Suggestions — what I would change in the design given this

Ordered by evidentiary strength. Each labelled with what backs it.

1. **[STRONG, and it CUTS BOTH WAYS — the central node-granularity finding]** The two vendor cost
   mechanics point in **opposite** directions on node size, and #574 has to pick:
   - *For coarser, longer-lived nodes:* *"Long-lived subagents that keep their context across
     subtasks save time and cost through cache reads and avoid bottlenecking on the slowest
     subagent."* A fresh `claude --bg` per stage pays the full 78–85k with **zero cache reuse**.
   - *For finer, per-stage nodes:* *"changing [effort] between requests does not preserve cached
     prefixes … vary effort across workloads rather than within a conversation that relies on cache
     hits."* If you want per-stage effort (and you should — see 2), you **cannot** get it inside one
     cached session anyway, so the cache argument for merging stages is weaker than it looks.
   **My read:** keep the process-per-stage boundary where effort or model genuinely differs; merge
   stages that would run at the *same* model and effort, since only those can share a cache.

2. **[STRONG] Make EFFORT configurable per stage alongside the model — it is currently missing.**
   *"Effort is the primary control for the trade-off between intelligence, latency, and cost."* The
   design as described to me makes only the *model* configurable. The vendor's own cost lever is
   effort, and it maps cleanly onto the stages: `low`'s named use case is literally *"subagents"*;
   `xhigh` is defined for *"Long-running agentic and coding tasks (over 30 minutes)"*, which is the
   `implement` stage. Adding a per-stage effort field is a small change with the vendor's strongest
   endorsement behind it.

3. **[STRONG — vendor-measured] Add an ADVISOR hook, not just a planning node.** *"faster,
   lower-cost worker models … call more intelligent models to check their plan and evaluate their
   work"*, at *"within 10% of Fable 5's score at 63% of the price."* Note the control direction: the
   **worker calls the advisor on demand** — *"coached only when needed"*. A fixed Fable planning
   node on every ticket spends Fable tokens whether or not the stage needed help; an on-demand
   escalation spends them only where a node is stuck or about to commit. Given that Fable tokens
   are the maintainer's scarce resource, this is the shape that conserves them best.

4. **[STRONG] The stage-model mapping is vendor-supported — record which source backs it.** Sonnet:
   *"including high-volume sub-agents in multi-agent orchestration setups."* Haiku: *"high-frequency
   workloads where latency and cost matter."* Opus vs Fable: *"if your evals or internal testing
   show Opus struggling on some tasks, then Fable is the answer."* The ruling is sound; it is just
   grounded in source 5, **not** in either assigned page.

5. **[STRONG — a real tension to put in front of the maintainer] The vendor's DEFAULT is the
   opposite selection procedure.** *"our default recommendation is to start with the most
   intelligent generally available model and use effort level to dial in performance and cost"*, and
   *"Starting with a smaller model can also make it harder to distinguish between model failures and
   setup failures."* For a **brand-new DAG harness**, that second sentence is the sharp one:
   debugging a cheap model's failure and a harness bug at the same time is the expensive path.
   **Suggestion:** bring the DAG up with capable models at low effort, then step the model class
   down per stage once each stage is *known* to work. The configurability the maintainer already
   required is exactly what makes this cheap to do.

6. **[STRONG] Audit the 78–85k payload by KIND, not size.** Split into (a) intent/why, (b)
   high-fidelity references, (c) prescriptive rules/examples. The vendor endorses (a) and (b) with
   no volume caveat and says (c) *"can degrade output quality."* At 1M context, 85k is ~8% of the
   window — capacity is not the issue; composition is.

7. **[STRONG] Every node brief should lead with WHY.** *"I'm working on [the larger task] for [who
   it's for]. They need [what the output enables]. With that in mind: [request]."* This is the one
   thing both assigned sources say to **add**.

8. **[STRONG] Every node needs the autonomous-pipeline reminder.** The DAG's nodes are `--bg` with
   no watching user — precisely the documented case: *"You are operating autonomously. The user is
   not watching in real time and cannot answer questions mid-task…"* plus the end-of-turn check
   against ending on a promise. **This repo has been bitten by exactly this** (agents idling without
   delivering), so it is a targeted fix, not a speculative one.

9. **[STRONG] Add the progress-grounding instruction to every node.** *"Before reporting progress,
   audit each claim against a tool result from this session"* — reported to have *"nearly eliminated
   fabricated status reports even on tasks designed to elicit them."* A DAG that auto-advances on a
   node's self-reported success is exactly the system a fabricated status report breaks.

10. **[STRONG] Never show DAG nodes a remaining-token countdown.** *"Avoid surfacing explicit
    context-budget counts where possible"* — it triggers premature summarize-and-hand-off, which in
    a DAG means a node quitting early and the next node inheriting a truncated result.

11. **[MODERATE — the fix for this repo's recurring delivery failure] Pair the delivery tool with
    elicitation language in the SYSTEM PROMPT.** *"Defining the tool is not sufficient on its own;
    without an instruction in the system prompt, Claude Fable 5 rarely calls it."* The repo's
    repeated `SendMessage`-before-idle failures are this exact shape, and the vendor's diagnosis is
    that availability is not enough — the role definition must elicit the call. Also note *"Tool
    inputs are never summarized, so the content arrives intact"*, which is the mechanism that makes
    a tool-based handoff more reliable than final assistant text.

12. **[MODERATE] The `review` stage's fresh-context design is right; its cross-family design is
    un-sourced.** *"Separate, fresh-context verifier subagents tend to outperform self-critique."*
    The vendor justifies this on **freshness**, and says nothing about model-family diversity. Also
    consider rubric-driven verification: *"Rubrics allow Claude to … verify your taste in a
    particular field."*

13. **[MODERATE] Prefer references-as-code over prose.** *"you should prefer files that are in code
    as it provides clear, high-fidelity instructions to Claude in a language it knows very well"*,
    and *"A spec may also be a detailed test suite."* For `implement`, a failing test is a better
    brief than a paragraph.

14. **[MODERATE] Strip examples from briefs, especially `research`.** *"giving examples actually
    constrains them to a certain exploration space."*

15. **[MODERATE] Budget node runtimes for the new regime.** *"Individual requests on hard tasks can
    run for many minutes at higher effort settings … autonomous runs can extend for hours"*, and
    `xhigh` is specified for tasks *"over 30 minutes"*. Node timeouts tuned to pre-Fable durations
    will kill healthy nodes. The launchd tick watchdog is the right shape — *"check on runs
    asynchronously, for example through scheduled jobs, rather than blocking"*.

16. **[MODERATE] If any stage runs on Fable, audit its brief for reasoning-echo instructions.**
    Instructions to *"echo, transcribe, or explain its internal reasoning as response text can
    trigger the `reasoning_extraction` refusal category … causing elevated fallbacks to Claude Opus
    4.8."* A `review` brief asking an agent to "show your reasoning" is a plausible trigger, and the
    failure would look like unexplained model substitution.

17. **[WEAK — inference, cheap to act on] Re-test the repo's rule corpus against the 80% result.**
    Anthropic deleted most of a professionally-tuned system prompt with no measurable eval loss, and
    source 2 says over-prescriptive skills *"can degrade output quality."* That is not a claim any
    specific rule here is wrong — many encode real measured local failures. It is a claim the corpus
    deserves a measured re-test rather than monotonic growth. `/doctor` is the vendor's own tool:
    *"use the command /doctor in Claude Code to rightsize your skills, and CLAUDE.md files."*

---

## Limitations — what I did NOT read

1. **"A field guide to Claude Fable 5: Finding your unknowns"** (Jul 6, 2026) — source 1's closing
   line points at it (*"check out our Fable field guide"*). Not fetched. Most likely to carry
   additional Fable-specific prompting shape.
2. **`/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`** — source 2
   defers cross-model techniques here. Not fetched; may contain the system-vs-user-turn guidance
   that is absent from everything I read.
3. **`/docs/en/build-with-claude/thinking`** (and `#thinking-and-effort`) — not fetched; the deeper
   thinking/effort interaction lives there.
4. **"Choosing a Claude model and effort level in Claude Code"** — linked from source 5 and, by
   title, the most Claude-Code-specific version of the model/effort decision. Not fetched. **This is
   the highest-value remaining follow-up for #574.**
5. **`/docs/en/build-with-claude/task-budgets`** — listed as a supported Fable feature (*"Give
   Claude an advisory token budget for the full agentic loop to help the model self-regulate on long
   agentic tasks"*). Not fetched, and potentially relevant to bounding node cost.

---

## GitHub repos touched

_None._ All five sources are Anthropic-owned web properties (`claude.com/blog`,
`platform.claude.com/docs`). No GitHub repository source, README, issue, or `llms.txt` was consulted.
