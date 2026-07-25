# How I Make Opus Think Like Fable (5 easy steps)

Source: https://www.youtube.com/watch?v=XTBWVVcF3Pk
Type: video transcript (YouTube auto-captions)

Since we all got access to Fable 5, I've spent a few thousand dollars in usage credits just playing around with it, understanding how it works, and understanding more importantly how we as people can get the most out of a model this powerful.

And I think one of the most important takeaways I've had is that yes, Fable 5 is an incredible model, don't get me wrong, but the model isn't really the moat.

So, think about it like this.

You've got a beginner with AI, and you've got someone like Andre Karpathy, for example.

If you give the beginner Fable 5, and you give Karpathy Sonnet 3.7, Karpathy will build something better than the beginner, even though the beginner's model is exponentially better.

And that's because of the fact that it's way more important the way you instruct it and the systems you build and the loops you build around the model.

Here's another example I want you to think about.

I've obviously tested Fable 5 a ton.

I've also tested Opus a ton and Sonnet a ton.

One of my favorite things to do lately is to use the dynamic workflows that Claude Code lets us, you know, spin up.

And I've done a ton of dynamic workflows where I said, "Hey Fable, design a workflow, and then all of your little sub-agents, have those be Fable as well." And then I would do the exact same tests with Fable orchestrating a bunch of Opus sub-agents, and Fable orchestrating a bunch of Sonnet agents.

And what I found is that when I run those dynamic workflows, the results are about the same, even though the Fable runs costed me exponentially more.

So, anyways, the point I'm trying to make, you can't keep the model's intelligence, but you can keep its process.

So, today what I want to talk about is basically, really quickly, how can you turn a model like Opus into something that feels more like Fable?

And the first thing is that you have to think of this model more like a teacher rather than a workhorse.

When we all got access to Fable, I think we were basically just pushing it to its limits.

And Anthropic even put out some stuff about like seeing how it's really good at like long tasks, you know, working towards a goal, planning it out, executing it, and then verifying it.

And it is really good at that, but the whole idea of model routing is basically finding that balance, you know?

This task takes this much intelligence, so why would you need a model that has this much intelligence and cost you this much for something that you could, you know, grab a much smaller, cheaper model, and you could get the task done at the same level of quality.

And that is the whole name of the game, and that's going to be a very important skill to master as we head into, you know, the next years of AI.

So, rather than having Fable, you know, plan everything out and do everything, we're trying to extract the way that Fable thinks, and then let other smaller models think it like that and execute like that.

I've had Fable go through my setups and make improvements and go through my skills and improve them, and I realized that I was just treating Fable like kind of like a co-founder or more like an officer at my company rather than just an employee.

Kind of like a senior engineer that is about and it's trying to package up everything that it knows to hand over to the new cohort of junior engineers that's going to come over or come in and take its place.

So, one thing that happened recently was the system prompts got leaked from Cloud Fable 5.

So, I read through this whole thing, I had Fable 5 read through this whole thing, and we picked out some important things that we noticed from this prompt itself.

Partial recognition from training does not mean current knowledge, meaning just because something's in your memory, you should probably verify it.

Very similarly over here, a prompt implying a file is present doesn't mean one is.

So, it's told to check that things actually exist.

So, basically, making sure at every step of the way that what it's doing and what it's done is accurate.

Address even an ambiguous query before asking for clarification.

So, answer first, then ask.

One question max.

Acknowledge what went wrong, stay on problem, maintain self-respect.

One for signal facts, three to five for medium tasks, five to 10 for deeper research comparison.

So, basically talking about effort.

So, yes, we have the discussion around what model is right for the task, but we also have the discussion around what effort level is right for the task.

And something that I like to look at is this example, which was on the release blog for Cloud Fable 5 and Mythos 5.

So, this compares Fable 5 and Opus 4.8 as well as GPT 5.5 when it comes to the score on the Y axis, the cost on the X axis, and then we see each of these models, and we see different effort levels.

So, if you're one of those people that has just turned on Fable 5 and you're just using it on the default effort level, or same with Opus, and you never play with those, then definitely start playing around cuz it gets a little interesting.

Like here you'll notice that Fable 5 on low is pretty similar to Opus 4.8 on high.

Now, Fable 5 is a little bit more expensive and a little bit higher quality, as you can see here, but they're kind of similar.

But that doesn't always mean that higher effort is actually better.

I've had a lot of times where with Fable I'm just basically using it on high, because when I use X higher max, or even on Opus, when I use X higher max, it starts to go way longer, get way more expensive, and then it overthinks, and it, you know, second-guesses itself, and then it ends up producing something worse than if I just would have gone with Opus 4.8 on high, or Fable on high.

Anyways, after reading through the system prompts and after playing with the models for so long, there are two things that I want you guys to do.

This first one is to basically take the way that you have been playing with Fable, and the the hardness, or, you know, whatever you want to call it, however you've been using it, and turn that into something that Opus can do, and that Sonic can do.

So basically we're extracting the Fable method.

Now, one thing that I would encourage you to do is, if you've ever gotten a deliverable from Fable that you just loved, and you couldn't really explain what you loved about it, have Fable analyze it, or have Opus analyze it.

And if you can look back at the session, that's even better.

What did you think about to get here?

How did you get here?

What did you do to prove that it worked?

How were you able to get an output that was just so good?

And then extract that information, and turn that into a skill.

So I basically have this skill now called Fable mode.

And whenever I want Opus to use Fable mode, or if I want, you know, if we got a really hard problem in front of us, I tried using Opus 4.8 with Fable mode, and it feels really good.

It just feels like the model has been elevated a little bit, because it has this, you know, Fable prompt kind of injected into it.

And it works on these five gates.

So, scoping, evidence, attacking, verifying, and then reporting.

And this is almost like the way you set your, you know, {slash} goal prompts, and you use dynamic workflows, and you basically set these loops, but we're doing this as a skill file as well.

Now, one really important thing about scoping, and and what people call, you know, like planning, is there's a big difference between just planning something out, as far as like, "Hey, here are all the steps, plan that out, and go do it." And then there's also the idea of playing devil's advocate and thinking about, okay, what about everything that could possibly go wrong?

What if we explore all of the unknowns in this plan?

And that is something that Fable does a really good job at, which is why if I have Fable spin up a dynamic workflow to help me achieve some end goal, and then once it's planned out every single possible step, and it thinks about every single thing that could go wrong, and then designs a dynamic workflow in a way where Sonnet can go do all the execution and just report back to Fable and keep sending everything back to Fable, then Fable can keep designing more steps in that process.

And that is why when I do dynamic workflows with Fable and Sonnet, it's pretty similar to results when I do dynamic workflows with Fable and Fable.

And to me that was a big like lightbulb moment.

Like, why is this just as good and it's significantly cheaper?

So, you can just start by saying something like this.

Write a complete installable skill file that makes Opus 4.8 operate with your judgment, your planning, verification, and reasoning habits, and activate it on something like Fable mode.

So, for example, right here you can see this is my Fable mode skill, which I'll attach in my free skill community completely for free.

The link for that is down in the description.

Just join this and then go to the classroom and click on all YouTube resources and you can find everything that I've ever dropped on YouTube for free.

So, that's where you'll find the Fable mode skill, but you can also just build this yourself.

And you can see here that this walks through Fable's working discipline, so that any model can run it, which means you could even have GPT 5.5 run this if you want, or even open source models run this if you want.

Anyways, it basically goes through those five gates.

So, scoping before you work and then, you know, we get into details, evidence before reasoning, reasoning adversarially, verifying before or declaring done, and then calibrating.

You've also got a few standing habits and a few things to look at, which like I said, you guys can inspect this file if you want to, but this being given to Opus 4.8 makes Opus feel, like I said, a little bit elevated.

So, that has been a really helpful strategy.

And then something that bolts right onto that really well is just, once again, the idea of model routing and figuring out how Fable or how some smart model can route to the small ones when needed.

And something that I've been doing lately is been giving my Claude basically a table of different models that are in the toolkit and when to use them.

So you could also have a delegate to Codex or you could have a delegate to open source models.

And this like I said is something that's going to be very very big when companies are starting to think about the unit economics and you know, small teams and you yourself maybe you have an AI budget per month.

This is the type of stuff that's going to separate people that are getting you know, a ton more for a ton less.

So a good way to split this up is basically saying, okay, here are the different models in our toolkit.

Here's how much they cost, you know, a higher number meaning a better cost score, you know, cheaper.

And then we have intelligence and taste.

And if you want to throw in some other categories that are based on your workflow, feel free.

But intelligence is kind of like how smart you feel like they are, how much they understand you, how good they are at maybe reviewing code and things like that.

And then on the taste side, this is what I think more of like the, you know, creativity, the thinking out of the box, UI/UX design, things like that.

And so this can really help when you're designing these agent teams or you're delegating to sub agents and you're spinning up dynamic workflows because sometimes your dynamic workflows can utilize a bunch of different Sonnet ones and Haiku ones and then even Opus ones as well.

So here's an example of an actual test that I had run where I used Opus as the orchestrator and I used Opus with this prompt from earlier that we talked about.

Oh, where is it?

Sort of like the the Fable mode prompt and it used a bunch of different Sonnet workers and Opus workers and Haiku workers.

And those were three different tests.

And the one where the Opus orchestrator delegated to all the Haiku scouts, it was this much cheaper, you know, about three times cheaper and the result was the exact same.

So similar to my example with the Fable ones, that is something to be thinking about big time.

So I know this one was quick and I wanted to make it quick, but I've just been seeing a ton of comments and a ton of people in the communities asking about, you know, kind of freaking out about the fact that Fable is going to be taken away.

It is going to come back to subscriptions, that's what Anthropic says at least.

We don't know when, but it will be back.

But all of this, you know, government getting involved and models being taken away stuff, really has me thinking about the fact that, you You we don't own anything.

We don't own these models.

So, what we can own is our processes, our systems, our methodologies, the way that we think about using these models.

And also, we can own hardware, and we can own local models.

So, I'm definitely going to be digging into a lot more of this type of stuff.

So, let me know what you guys want to see around these topics.

But, anyways, if you learned something new or you enjoyed the video, please give it a like.

Helps me out a ton.

And as always, I appreciate you guys making it to the end of the video, and I'll see you on the next one.

Thanks, everyone.
