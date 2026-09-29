# Manage your OWN dotfiles with symlinks?

- URL: https://github.com/omacom/omarchy/discussions/191
- author: LeonardoTrapani (NONE) created: 2025-07-16T10:38:24Z upvotes: 1
- fetched: 2026-09-29 via gh api graphql (lane X)

## Body

I've previously encountered issues with theme management and configuration synchronization in other Arch-Hyprland setups. Typically, these setups use scripts to override existing configuration files rather than symlinking directly, meaning any changes made require running additional scripts to sync updates to `.config` and other directories.

However, your approach seems different. If I understand correctly, themes are symlinked directly and then imported by the configurations, which themselves are symlinked into their appropriate locations (such as `.config`).

Am I correct in understanding your method?

To maintain my own dotfiles and synchronize them with a git repository, would the recommended approach be to fork this repository, modify the configurations directly here, and then rely on these changes being automatically reflected in the `.config` directory and other relevant locations?


EDIT:

I noticed that the files are not actually symlinked, but in config.sh, the .config file is just being copied directly into .config

That's the issue I was talking about before, because for some configurations (for example neovim), where you want to see changes directly, you would want the changes to be reflected instantly.

Why wouldn't omarchy use symlinks to the .config directory, since there would be no issues with the theming configuration?

## Comments
### Zooce (NONE) @ 2025-07-18T07:08:13Z

The way I've been doing it so far (based on my current understanding of how Omarchy works), I updated my dotfiles to start with Omarchy as a base and then I override things I want to change. For example my .bashrc starts with `source ~/.local/share/omarchy/default/bash/rc` (which is what the Omarchy installer puts there by default), all of my overrides are just after that.

For things like Neovim where I've got a whole repo dedicated to my config, I'm just using my own there. I'm sure there's a way for features like theme switching to work in this case, I just haven't gotten there yet.
#### reply gochila-cell (NONE) @ 2025-09-11T08:20:55Z

I also have my nvim repo. I want to use it, should i change the following dir with my dot files `~/.local/share/nvim`?

#### reply Zooce (NONE) @ 2025-09-12T05:06:15Z

I'm not exactly sure what you're saying there, but I'll say whenever I want to try out other Neovim configs or other branches of my own config, I backup or clear out the following directories:
* ~/.local/share/nvim
* ~/.local/state/nvim
* ~/.cache/nvim

Neovim will regenerate those directories on its own.

The actual config for Neovim is typically in ~/.config/nvim

#### reply gochila-cell (NONE) @ 2025-09-12T09:33:30Z

Thanks, it is much clearer. What I meant was replacing nvim with my own config and setup.

Regardless, tanks for the help.

#### reply gochila-cell (NONE) @ 2025-09-15T11:33:24Z

@Zooce What about the directory in `~/.local/share/omarchy/config/nvim`? I understood that if clear all of the directories you mentioned I can import my own config, what about the directory I mentioned latter. I don't want to mess the master branch, will this be an issue?

#### reply Zooce (NONE) @ 2025-09-15T15:10:48Z

Oh you mean making changes to the Omarchy Neovim config? Not sure about that one. I don't think the Omarchy config is really even meant to be customized and is more of a plug-n-play type situation (but I could be wrong). You could always copy it into ~/.config/nvim as a starting point and customize from there.

#### reply LeonardoTrapani (NONE) @ 2025-09-15T16:55:53Z

For these cases I just fork the repo since I have my own neovim config

#### reply Zooce (NONE) @ 2025-09-15T23:44:54Z

I guess that's another way to do it - fork Omarchy and just make the changes you want, syncing with the upstream every once in a while.

#### reply gochila-cell (NONE) @ 2025-09-16T12:02:23Z

Sounds, good! I just fork the repo and do my own mods. Besides, there are somethings I would like to change and add to the menu. I think that is possible, but please let me know if it isn't xd xd. 

### sspaeti (CONTRIBUTOR) @ 2025-09-16T19:00:22Z

Try [stow](https://www.gnu.org/software/stow/), here's a good video - [NEVER lose dotfiles again with GNU Stow](https://www.youtube.com/watch?v=NoFiYOqnC4o) by Typecraft  or a [blog article](https://tamerlan.dev/how-i-manage-my-dotfiles-using-gnu-stow/).

I use it for my dotfiles with omarchy too -- in case of interest, check them out at https://dotfiles.ssp.sh. My omarchy dots are mostly in [hypr](https://github.com/sspaeti/dotfiles/tree/master/hypr/.config/hypr).
#### reply andnig (CONTRIBUTOR) @ 2025-09-20T20:10:29Z

Do you have any tips for how you stay in sync with omarchy updates? Do you manually select what changes to port over?
I had a nice set of dotfiles, but as the updates grew bigger, I abandoned them, forked omarchy and basically reintegrated my dotfiles there. So I use omarchy with my dotfiles on top. 
Your strategy seems to be the opposite - you use your dotfiles, with omarchy sprinkled in. I'm intrigued.

#### reply sspaeti (CONTRIBUTOR) @ 2025-09-21T10:49:16Z

Just don't change the omarchy dots in ~/.local/share/omarchy, and move all your dots in somewhere not touched by Omarchy. I added everything to stow, so where I need to manually merge is `waybar` and `walker` or applications. But because I have them in stow, and therefore git, after every upgrade I see the changes Omarchy made. And I can just port the once I want, and ignore the once I don't.

Also, omarchy makes a backup file of the changed configs, so you never lose anything. So it's a nice workflow now. 

My usecase was or is: I have a very long history of my own dots. So I moved to Omarchy and added mine too it. E.g. I have my own Neovim dots, so I replaced neovim with mine. For the shell, i found a nice way of having `bash` default to Omarchy, and all my personal dotfiles are applied to the `zsh` shell, as this is the one I'm using. So when I open a terminal, it automatically open zsh shell with all my dots. So I don't need to thinker with Omarchy's default. If I need something for Omarchy, I just port it to zsh. But so far, my zsh is much more advanced, including tmux, than Omarchy, which is basic bash with starship. Not sure if that helps, feel free to follow up. 

#### reply EFrMG (CONTRIBUTOR) @ 2026-07-26T04:51:08Z

Stow is way more limited than Chezmoi. One very tedious thing too, apart from the limitations, is that you have to go file by file and delete them if you intend to replace them with symlinks from your git-tracked directory.
Every time Omarchy makes a migration with `sed -i` as well, one has to go straight into where that changed file is and revise it manually, copy the changes over to the tracked file manually, to then set up a symlink.

### ronald2wing (NONE) @ 2026-08-18T19:37:35Z

Can we have something like this built into Omarchy?
Just a file with a format like below:
```
global repo-path
global config-destination
git-repo repo-path config-destination
```
Basically, it will fetch the git repo and match the repo path to the config, like stow, but in a single file without pulling the repo. This way, people will also be able to use others' online dotfiles.

