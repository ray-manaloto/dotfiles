[Skip to content](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/#main)

On this page

I’ve learned the hard way that starting a job on a large engineering team as a senior engineer is more than simply writing good code. You have to drive initiatives at a social level and not simply because you know more about the codebase.

For a new hire this is especially a challenge. **You need to learn the system that your colleagues already understand.** You might be a higher level but you’ll be a worse engineer for the first few months while you ramp up.

## 1\. Write Half the Code [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#1-write-half-the-code)

Tasks are not simply work to be done. For a senior engineer, they’re also tools for developing the team itself. If you just take tasks and complete them yourself you’ll squander the possibility of spreading knowledge across the team.

I prefer pairing to spread knowledge but have really struggled to bring that culture into most teams. What I do more often now is implement half of what we need and leave the rest to another engineer. If something needs to be done for mac + windows for example, I’ll do the mac part and leave the windows for someone else. Usually they can use your half as a reference point so it won’t be too difficult for them and it makes reviewing much better since 2 people have much more context.

A task like this has already been scoped out by the senior engineer and they would’ve noticed any potential complexity. Both implementation and estimation should be predictable and a great task for a more junior engineer to develop their skills and not spin their wheels.

Not only that, but people generally enjoy delivering things together.

## 2\. Own Something [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#2-own-something)

In the first 6 months you must be considered the undisputed owner of a component. It might not be a big thing, maybe it’s some metrics library or a linting tool, but it has to be something. You need that wedge to at least start ownership somewhere.

Once you own a component you’ll likely own it for life (well, until you leave the team/company). Rarely do components get moved between teams—and even more rarely is it a successful handoff. So maybe don’t go too crazy, but you’ll be expected to at least be able to point to something you own in performance reviews for sure.

It’s also helpful for collaborating. If you’re the “eslint guy” then you’ll regularly be interacting with other people that need help with eslint or are trying to extend it.

## 3\. Be The Notetaker [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#3-be-the-notetaker)

**Take the minutes during meetings.** If your team doesn’t currently do this, just share your screen and start doing it. It’s highly unlikely anyone will take issue unless someone is showing a presentation or something. I like [quip](https://quip.com/) for this task but it really doesn’t matter what tool you use.

If taking minutes is already part of a team’s culture, generally people don’t want to be a notetaker so nobody is going to mind if you take on that responsibility.

When people are talking try to organize bullet points into 2 sections: what you discussed and action items. Editorializing people’s points will be hard as you gain context, but it’ll force you to actually understand what they’re saying. You might need to ask questions or have others fill in some gaps but that’s ok.

Make it clear that assigning action items to people is not saying that a task must be done by them, just that they are the owners of making sure it happens (“it” is usually just finding the answer to an unknown). The EM will apprecaite smoothly organizing who should be doing what. The EM is usually in need of being able to go back into docs for reference too so they’ll love the minutes too.

The downside is you won’t be able to talk as much since you’ll be busy. That’s ok though because while you’re new you’re lacking context and it’s probably better to be a little bit quieter—that’s true for me anyhow. (I’m known to provide terrible solutions because I don’t even realize the context I’m missing.)

In large meetings where you can’t share your screen just take notes of important things people say. This is the #1 way I’ve found to pay better attention in meetings. You don’t need to share it or even look at the notes again, just try to write at least 1 point down in every meeting.

## 4\. Don’t Assume You Know the Answer [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#4-dont-assume-you-know-the-answer)

The way you learn anything is by making mistakes. I believe you can’t learn anything unless you do it the wrong way first (or at least get close enough). Junior engineers will have solutions to problems and if they experiment with applying them—they’ll continue to develop. **Your job is to foster that dynamic.**

Senior engineers—on the other hand—are expected to use their vast background experience to quickly resolve issues similar to what they’ve run into in the past. Senior engineers need to walk a tightrope between providing their experience and shoving solutions down engineers throats.

A lot of this simply comes down to language and they way you present yourself. Give them extra context by talking about past experience (most senior engineers talk endlessly about $lastjob and I think that’s ok—if maybe a little dry after a while). Don’t dictate how things should be done.

If they’re going down a road you disagree with it’s good to make your point understood but nothing more. Be the one that steps aside (I talk more about this in “10. Force Decisions”).

Here are a few examples:

- Don’t say: “If we did X instead of Y we wouldn’t have to worry about Z.”
- Say: “Have you considered doing Y? I did that on a previous project and it helped Z.”
- Don’t say: “I think we should stop doing X.”
- Say: “Are you concerned about how we use X?”
- Don’t say: “X isn’t very clean code, we should do Y.”
- Say: “I don’t have a strong preference about that code."—You don’t and you should never have a strong preference regarding code style. If someone else feels strongly about code style, I’d just let them.

You can’t just swap words out like this though. You can word something in a nice way but if what you’re really doing is demanding solutions your way you haven’t accomplished anything. Try to be as curious as possible to avoid that.

## 5\. Find the Pain Points [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#5-find-the-pain-points)

Have 1:1s with team leads from cousin teams, find out what they’re working on, find out what’s a headache. Fixing an annoyance from another team is a surefire way to build rapport. There is a problem somewhere that you’re perfect for: you just need to find it. My go-to is updating dependency versions and build tools.

Is there something they don’t want to maintain anymore? Could that be your first component to own?

Is there some duplicate work going on? Collaborate instead. And make absolutely sure you mention this when talking to your skip. In my experience there isn’t anything upper management likes to hear more[1](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/#fn:1) than sharing efforts across teams.

## 6\. Don’t Refactor [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#6-dont-refactor)

Refactoring is a waste of time and easily harmful for a senior engineer. Refactoring keeps you _within_ your codebase and outside of working with other teams. I argue it provides questionable value anyhow—as someone that’s done a ton of it. It’s necessary on occasion but be mindful you’re not spending too much time pruning up the rose bushes.

If something significant is really dying for a refactor just keep it in the back of your mind. Unless the rest of the team is also clamoring for a fix it might just be best to wait until you’ve established yourself.

Where this can really go sideways is when you refactor code a colleague wrote and they don’t like your design. Aesthetics are often in the eye of the beholder and stepping on someone else’s idea of beauty will rapidly damage rapport. They probably won’t feel comfortable telling you about it either.

Honestly life is too short to debate whether the arguments to a function should be an object or parameters. This is a decision better left to more junior engineers anyways as they’ll be dealing with the code more. **You should be focused on how components interact—not the style of the code.**

## 7\. Write Good Specs [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#7-write-good-specs)

You’ll be judged more on how well you write specs than code. Spec writing of course has little to do with the spec but everything around it: how it was built, how you gathered information from stakeholders, how you distributed the information, all of that and more. The product of a spec is not a doc it’s actually those conversations.

The goal is to get people to provide appropriate input about a problem, get the right people to provide potential solutions, form that solution, and communicate what it will be. Ultimately we just want to solve a problem in an effective way. The doc is just a tool to make that happen.

See if you can find a good name for your project. Marketing is for engineers too[2](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/#fn:2).

Reference the things that upper management is saying. Reference their master plans at least once in every spec to tie things back to them. They’ll greatly appreciate that you’re listening.

## 8\. Be Social [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#8-be-social)

You need to be a familiar face to as many as possible. That way they feel comfortable coming to you—or at least even know who you are.

Some ideas for activities:

- Game night
- Coffee break
- Dinner at your home with 1-2 people

Try to make regular activities. What we do at WhatsApp (not so secretly) is schedule game nights every couple of weeks at a regular time. What we don’t do is publicly list the event. We just say an hour before it happens on a Friday that they can optionally come join a round of [Codenames](https://codenames.game/) or something. We’ve found this gets more people than trying to set aside time in advance.

## 9\. Force Decisions [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#9-force-decisions)

Teams often don’t know what decision to make. Sometimes these are because people feel strongly about a certain approach, but more often it’s because nobody feels strongly enough to make the decision on behalf of the team. I’ve got 2 (admittedly similar) tricks up my sleeve for when this happens:

**McDonald’s method** — My classic method (that I got from somewhere years ago but no idea where) of doing this involves the canonical example of a team that can’t decide where to get lunch. I say McDonald’s. Nobody wants to dine at McDonald’s on the company dime so people will be quick to suggest acceptable alternatives. I do this with software too: suggest the obviously bad approach to force others to explain their alternatives that are clearly better.

**Disagree and Commit** — This is famously an Amazon principle that I quite like. It’s usually better to do anything so we can improve and iterate as we go rather than pontificate about what could be. Remember this yourself if the team is going a direction you disagree with. If it’s truly a terrible idea—they’ll find out soon enough. Besides, you might be wrong!

## 10\. Give Tech Talks [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#10-give-tech-talks)

There is no easier way to be perceived as an expert than by giving a presentation. There is likely a domain you have experience with that the team is less familiar with.

Hopefully your organization already has some kind of regular presentations like this but if not—what a great opportunity to start one!

## Summary [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#summary)

Thanks for reading. I’m still a work in progress myself and if I’m frank: I need to take my own advice sometimes. I’d love it if you could let me know what you think and if you have any more tips. I want to do a “10 More” article at some point and have it be some kind of an anthology.

## Footnotes [\#](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/\#footnotes)

* * *

1. One from Heroku I loved was “Project Glostick”. [↩︎](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/#fnref:1)

2. Well maybe that their department just got +2000 head count. [↩︎](https://jdx.dev/posts/2020-09-16-10-tips-ramping-up-as-a-senior-engineer/#fnref:2)