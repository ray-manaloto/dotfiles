# Graphify + Obsidian: Build an AI Second Brain That Never Forgets (Real Setup)

Source: https://www.youtube.com/watch?v=rtutpoT4SYg
Type: video transcript (YouTube auto-captions)

This year, almost 90,000 developers starred a tool that turns any folder on your computer into a living map of everything inside it.

Your code, your notes, your PDFs, even your screenshots.

Separately, 42,000 starred five small files written by the CEO of Obsidian that teach AI agents to work inside your notes.

Two different projects, two different authors, and almost nobody has noticed that they snap together.

One of them draws the map of everything you know.

The other one gives your AI hands to work inside it.

Today, I plug them together on my own machine, and I'm going to show you every step with real commands and real numbers.

And because this is a video about knowledge graphs, we are doing something I have never done before.

Watch the bottom corner.

This video is going to map itself while you watch it.

Every idea becomes a node.

Every connection becomes a line.

By the end, you will see everything we covered as one living atlas.

Let's start with the problem.

Graphifi's own readme opens with a story about Andrej Karpathy.

He keeps a folder called raw where he drops papers, tweets, screenshots, and notes.

No structure, just a pile.

And honestly, that is all of us.

Somewhere on your machine, there is a pile.

Meeting notes next to PDFs, next to code, next to whiteboard photos.

You know there are connections buried in there.

You just cannot see them.

And your AI has two problems with that pile.

First, every time you ask a question, it has to reread everything.

And you pay for every single word it reads.

Second, the moment the session ends, it forgets.

Tomorrow, it walks in with amnesia and reads the whole pile again.

No structure and no memory.

Keep those two problems in mind because each of these tools kills one of them.

Tool one, Graphify, an open-source skill for Claude code, Code Explainer, Gemini CLI, basically any coding agent.

One command, {slash} graphify, then a dot for whatever folder you are in.

It reads everything in that folder.

For code, it does not guess.

It reads the actual structure, which function calls which what imports what.

For PDFs and documents, it pulls out the ideas.

And for images, it uses AI vision.

Screenshots, diagrams, a photo of your whiteboard, even notes in another language.

Everything lands in one connected map.

And the map tells you three things a pile never could.

First, your god nodes.

The handful of concepts that everything else connects through.

Second, surprising connections.

Links between things you never realized were related.

Each with a plain English explanation of why.

And third, my favorite part, honesty tags.

Every single connection is labeled.

Extracted means it found this in your files.

Inferred means it worked this out.

Ambiguous means it is not sure.

Your map never pretends to know something it does not.

And I did not take any of that on faith.

I ran it on a real project, Karpathy's nanoGPT on this machine.

Here is the real output. 73 nodes, 76 edges, 19 communities, built in seconds, without a single AI call, because code needs none.

This is the interactive map it produced.

Every dot is a concept.

Every color is a community.

And the biggest node on the map, the one everything flows through, is the GPT class itself.

It found the heart of the code base on its own.

Here is the number that made this repo famous.

On their benchmark, a messy 52 file corpus of repos, papers, and images, answering questions through the graph, used 71 times fewer tokens than reading the raw files.

And the map is saved to disk.

Ask it a question in 3 weeks, it answers from the graph.

Problem one, structure, solved.

Now, the moment most of this video exists for.

Buried in Graphifi's output options is one command most people scroll past.

Graphifi export Obsidian.

I ran it.

And it turned my entire knowledge graph into a real Obsidian vault. 92 nodes, one per concept, each with proper properties on top, real double-bracket wiki links for every connection, and the honesty tags carried over.

It even drew a canvas file, a whiteboard of the whole graph, in Obsidian's own open format.

Your map just became a vault you can walk around in.

And that matters because of tool two. 6 months ago, Steph Ango, the CEO of Obsidian, who goes by Kepano, did something no other software CEO had done.

He personally taught AI agents to use his own product.

Five skills, published free on GitHub, 2,000 stars and climbing.

I covered them in depth in a previous video.

But inside this system, they play a different role.

They are the hands.

With those five skills installed, your agent can write notes in Obsidian's own dialect, wiki links and all, so nothing breaks.

It can turn any pile of notes into a live table with filters and formulas using bases.

It can draw on that canvas whiteboard GraphiFi just exported because both speak the same open format.

It can drive the app itself through the official command line, over 100 commands.

And with Diffuddle, it can take any webpage and strip it down to clean markdown.

Remember that last one.

It is about to become the front door of the whole system.

Hold on.

The Atlas just flagged something.

One node it cannot classify.

Tagged ambiguous.

It is you.

Real talk. 90% of you watching haven't subscribed.

On Facebook, subscribe is the supporter button.

That is what keeps the lights on here.

On YouTube, it's free and it tells the algorithm to send you more.

Subscribe to support us.

There it is.

Extracted.

Confirmed part of the graph.

Back to the system.

Now watch what happens when the map and the hands run as one loop.

Step one, capture.

You find a paper, a tweet, an article.

One command, GraphiFi add with the URL.

It fetches it, saves it to your raw folder, and wires it into the graph.

Or your agent clips it with Diffuddle first.

Clean markdown straight into the vault.

Step two, the map updates itself.

Run it in watch mode and it rebuilds as files change.

Or install the Git hook and every commit redraws the map automatically.

Step three, you stop asking your AI to read files and start asking the graph.

What connects this idea to that one?

Show me the shortest path between these two functions.

I ran that on nanoGPT.

Two hops, straight through the model file.

Every link labeled extracted.

Step four, your agent writes what it learns back into the vault as proper notes with proper links.

Which means step five happens on its own.

The next rebuild picks up those notes and the map grows.

Capture map, ask, write back.

That is not a chatbot with a folder.

That is a second brain that maintains itself.

And I am not the only one wiring this.

There is already a community repo, Claude code memory setup by Lucas Rosati, over 800 stars, built on exactly this pairing, Obsidian plus Graphifi as persistent memory for Claude code.

Sessions end, the Atlas survives.

Problem two, amnesia, solved.

Here is your whole setup, about 15 minutes, four commands.

One, pip install Graphifi, then Graphifi install.

Quick honest note, the package is spelled with two Y's right now while they reclaim the original name.

And on a Mac, if pip complains, use pipx instead.

Two, open your agent in any folder and type {slash} Graphifi with a dot.

First run on documents takes a while.

After that, it only rereads what changed.

Three, graphify export Obsidian and open the result as a vault.

Four, install the hands.

In Claude code {slash} plugin marketplace add Kapono {slash} Obsidian skills.

Then {slash} plugin install install.

On anything else, NPX skills add with the repo URL.

Then give it the first prompt of its new life.

Read my graph report and write me a summary note in the vault linking every god node.

Two honest caveats before you start.

Documents and images get processed through your AI assistant.

So, big piles take real time on the first pass.

And the Obsidian command line needs version 1.12 or newer and ships turned off.

One switch in settings fixes that.

And now look at the corner.

Remember the empty map from minute one?

This is the video you just watched as a graph.

The pile, the map, the bridge, the hands, the loop, all connected.

And you sitting right in the middle, tagged, extracted.

This is what your own work can look like tonight.

So, here is the sentence to take with you.

Stop feeding your AI a pile.

Hand it an atlas.

I put the whole system on paper for you.

The atlas setup, every command from this video, the full loop diagram, the first prompts to run, and the honest caveats in one free PDF.

Comment the word atlas and my agent sends it to you or grab it from the link below.

And if you are starting from zero, my premium beginner guide to Claude code takes you from a blank terminal to your first real automation step-by-step linked below with my other beginner guides.

Follow Hyper Automation Labs on YouTube Facebook and Instagram.

The Atlas keeps growing.

See you inside.
