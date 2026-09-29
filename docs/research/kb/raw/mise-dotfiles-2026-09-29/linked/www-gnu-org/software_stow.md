[**Skip to main text**](https://www.gnu.org/software/stow/#content)

[Free Software Supporter](https://www.fsf.org/fss):


[JOIN THE FSF](https://www.fsf.org/associate/support_freedom?referrer=4052)

[Site navigation](https://www.gnu.org/software/stow/#navigation "More...") [**Skip**](https://www.gnu.org/software/stow/#content)

- [ABOUT GNU](https://www.gnu.org/gnu/gnu.html)
- [PHILOSOPHY](https://www.gnu.org/philosophy/philosophy.html)
- [LICENSES](https://www.gnu.org/licenses/licenses.html)
- [EDUCATION](https://www.gnu.org/education/education.html)
- = [SOFTWARE](https://www.gnu.org/software/software.html) =
- [DISTROS](https://www.gnu.org/distros/distros.html)
- [DOCS](https://www.gnu.org/doc/doc.html)
- [MALWARE](https://www.gnu.org/proprietary/proprietary.html)
- [HELP GNU](https://www.gnu.org/help/help.html)
- [AUDIO & VIDEO](https://www.gnu.org/audio-video/audio-video.html)
- [GNU ART](https://www.gnu.org/graphics/graphics.html)
- [FUN](https://www.gnu.org/fun/humor.html)
- [GNU'S WHO?](https://www.gnu.org/people/people.html)
- [SOFTWARE DIRECTORY](https://directory.fsf.org/)
- [HARDWARE](https://h-node.org/)
- [SITEMAP](https://www.gnu.org/server/sitemap.html)

## GNU Stow

* * *

GNU Stow is a symlink farm manager which takes distinct packages
of software and/or data located in separate directories on the
filesystem, and makes them appear to be installed in the same place.
For example, `/usr/local/bin` could contain symlinks to
files within `/usr/local/stow/emacs/bin`,
`/usr/local/stow/perl/bin` etc., and likewise recursively
for any other subdirectories such as `.../share`,
`.../man`, and so on.

This is particularly useful for keeping track of system-wide and
per-user installations of software built from source, but
[can\\
also facilitate a more controlled approach to management of configuration\\
files in the user's home directory](http://brandon.invergo.net/news/2012-05-26-using-gnu-stow-to-manage-your-dotfiles.html), especially when
[coupled\\
with version control systems](http://lists.gnu.org/archive/html/info-stow/2011-12/msg00000.html).

Stow is implemented as a combination of a [Perl](http://www.perl.org/) script providing a CLI interface,
and a [backend Perl\\
module](http://search.cpan.org/dist/Stow/) which does most of the work. Stow is [Free Software](http://www.gnu.org/philosophy/free-sw.html),
licensed under the [GNU\\
General Public License](http://www.gnu.org/copyleft/gpl.html).

### Latest news

_Sun 8 September 2024_
Stow 2.4.1 has been released. This release contains some
minor bug-fixes — specifically, fixing
the `--dotfiles` option to work correctly with ignore
lists, allowing options in `.stowrc` with spaces, and
avoiding a spurious warning on Perl >= 5.40. There were also some
clean-ups and improvements, mostly internal and not visible to
users.
[Read\\
details of what's new.](http://git.savannah.gnu.org/cgit/stow.git/tree/NEWS)_Sun 7 April 2024_
Stow 2.4.0 has been released. This release contains some
much-wanted bug-fixes — specifically, fixing the `--dotfiles`
option to work with `dot-foo` directories, and avoiding
a spurious warning when unstowing. There were also very many clean-ups
and improvements, mostly internal and not visible to users.
[Read\\
details of what's new.](http://git.savannah.gnu.org/cgit/stow.git/tree/NEWS)

### Downloading Stow

Stow
can be found on the main GNU ftp server:
[http://ftp.gnu.org/gnu/stow/](http://ftp.gnu.org/gnu/stow/)
(via HTTP) and
[ftp://ftp.gnu.org/gnu/stow/](ftp://ftp.gnu.org/gnu/stow/)
(via FTP). It can also be found
on the [GNU mirrors](https://www.gnu.org/prep/ftp.html);
please
[use\\
a mirror](http://ftpmirror.gnu.org/stow/) if possible.

There is also a [git repository](https://savannah.gnu.org/git/?group=stow)
containing the latest development code.

### Documentation

[Documentation for\\
Stow](https://www.gnu.org/software/stow/manual/)
is available online, as
is [documentation for most GNU software](https://www.gnu.org/manual/). You may
also find more information about
Stow
by running
_info stow_
or
_man stow_,
or by looking at
_/usr/share/doc/stow/_,
_/usr/local/doc/stow/_,
or similar directories on your system. A brief summary is available by
running _stow --help_.

### Mailing lists

Stow
has the following mailing lists:

- [help-stow](https://lists.gnu.org/mailman/listinfo/help-stow) is
for general user help and discussion.
- [stow-devel](https://lists.gnu.org/mailman/listinfo/stow-devel)
is used to discuss most aspects of
Stow,
including development and enhancement requests.
- [bug-stow](https://lists.gnu.org/mailman/listinfo/bug-stow)
is for bug reports.

Announcements about
Stow are posted to
[info-stow](http://lists.gnu.org/mailman/listinfo/info-stow)
and also, as with most other GNU software, to
[info-gnu](http://lists.gnu.org/mailman/listinfo/info-gnu)
( [archive](http://lists.gnu.org/archive/html/info-gnu/)).

Security reports that should not be made immediately public can be
sent directly to the maintainer. If there is no response to an urgent
issue, you can escalate to the general
[security](http://lists.gnu.org/mailman/listinfo/security)
mailing list for advice.

The Savannah project also has a
[mailing lists](https://savannah.gnu.org/mail/?group=stow) page.

### Getting involved

Development of
Stow,
and GNU in general, is a volunteer effort, and you can contribute. For
information, please read [How to help GNU](https://www.gnu.org/help/). If you'd
like to get involved, it's a good idea to join the [stow-devel](https://lists.gnu.org/mailman/listinfo/stow-devel) mailing
list.

Bug reportingPlease send bug reports to the
[bug-stow](https://lists.gnu.org/mailman/listinfo/bug-stow)
mailing list (see [Mailing lists](https://www.gnu.org/software/stow/#mail) above).DevelopmentFor [development sources](https://savannah.gnu.org/git/?group=stow) and other
information, please see the
[Stow\\
project page](http://savannah.gnu.org/projects/stow/)
at [savannah.gnu.org](http://savannah.gnu.org/).
There is also a [stow-devel](https://lists.gnu.org/mailman/listinfo/stow-devel)
mailing list (see [Mailing lists](https://www.gnu.org/software/stow/#mail) above).Translating
StowStow is not currently multi-lingual, but patches would be
gratefully accepted. Please e-mail [stow-devel](https://lists.gnu.org/mailman/listinfo/stow-devel)
if you intend to work on this.MaintainersStow
is currently being maintained by Adam Spiers.
Please use the mailing lists for contact.

### Licensing

Stow
is free software; you can redistribute it and/or modify it under the
terms of the [GNU General Public License](http://www.gnu.org/licenses/gpl.html) as published by the Free
Software Foundation; either version 3 of the License, or (at your
option) any later version.

* * *

[BACK TO TOP ▲](https://www.gnu.org/software/stow/#header)

> [![ [FSF logo] ](https://www.gnu.org/graphics/fsf-logo-notext-small.png)](https://www.fsf.org/)**“The Free Software Foundation (FSF) is a nonprofit with a worldwide**
> **mission to promote computer user freedom. We defend the rights of all**
> **software users.”**

[JOIN](https://www.fsf.org/associate/support_freedom?referrer=4052) [DONATE](https://donate.fsf.org/) [SHOP](https://shop.fsf.org/)