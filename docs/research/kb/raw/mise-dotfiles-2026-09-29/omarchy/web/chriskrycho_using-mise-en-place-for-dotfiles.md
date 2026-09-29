**[Assumed audience](https://v4.chriskrycho.com/2018/assumed-audiences.html):** People who get into the nitty-gritty of managing developer tools on their Mac or Linux computer and know their way around a command line at least a bit.

**[Epistemic status](https://v5.chriskrycho.com/journal/epistemic-status/):** Figuring out the details in near real-time.

For [the new gig](https://v5.chriskrycho.com/journal/next-vanta/), I have a bunch of ephemeral environments that I’ll be using regularly as well as my local machine, and I really want to have those environments feel like“home” in the sense of being easy to jump into and just start working, with all my usual tools available.

This is what [dotfiles repos](https://dotfiles.github.io/) are for! Dotfiles are the files that usually start with a `.` (thus: dot files) in Unix-like systems in a user’s home directory, like `~/.profile`, `~/.zshrc`, `~/.config/fish/config.fish` and so on. Building on this, a number of tools out there make it possible to use a repository as the source for your dotfiles — whether simply by symlinking their contents into your home directory, or by running a setup script that can do that for you — and, critically, can do that _automatically every time an environment gets setup up_. That makes setting up a new developer environment something automatable, and that’s _great_.

I have known about this approach for years, but I have never gotten around to doing it: [Migration Assistant](https://support.apple.com/en-us/102613) has Just Worked™ for a very long time for personal machines, and for work machines, copying over a couple config files has just not been a problem. But with a need to do this _a lot_, things look a bit different. I finally got enough motivation to solve this.

After poking around a bit, especially after reading through my friend [Rob Jackson](https://github.com/rwjblue)’s [dotfiles](https://github.com/rwjblue/dotfiles) and talking with him about his approach (thanks, Rob!) I decided to use [mise-en-place (`mise`)](https://mise.jdx.dev/), which has a handy [task runner](https://mise.jdx.dev/tasks/) system that“just” uses shell scripts on the file system… but that’s exactly what I want. It leaves me minimally coupled to `mise` as a tool: it’s just there to orchestrate a bunch of scripts and manage sequencing and dependencies for me.

Those are things I _can_ do by hand, and that any other task-runner system could do as well. Using \` makes it very easy to let the tool do that coordination, though, while making every individual part of it easy to run (and therefore to test — albeit manually) in isolation.

So: [my public dotfiles](https://github.com/chriskrycho/dotfiles). They’re very much in flux right now as I determine exactly how I want to use them, and I expect to see them change quite a bit as I make much more ongoing use out of these ephemeral development environments in the months ahead. They are designed so that on any reasonably modern Unix-y machine (macOS or most Linux distros) with a Bash installation, checking out and running the `install.sh` script in the root will get everything up and running. That install script is _very_ simple: it checks whether this is a“dry run” (to pass that on like `mise run setup --dry-run`), installs `mise` if it is not already installed, and then executes `mise run setup`.

Right now, those are very simple tasks to install Homebrew and install the packages I want and then set the default shell to [fish](https://fishshell.com/). In the future, I expect to integrate actual dotfiles — particularly my fish and [jj](https://jj-vcs.github.io/jj/latest/) configs, as well as others for tools that I use less often but have customized over the years.

Hopefully this inspires a few of you to do the same with your own setups!

Show preferences


Hide preferences
Color schemematch OSlightdarkSide navigationhide