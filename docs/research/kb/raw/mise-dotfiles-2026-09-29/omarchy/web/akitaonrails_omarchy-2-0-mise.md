# Omarchy 2.0 - Mise for Organizing Development Environments

[#omarchy](https://akitaonrails.github.io/en/tags/omarchy/) [#developer-tools](https://akitaonrails.github.io/en/tags/developer-tools/) [#containers](https://akitaonrails.github.io/en/tags/containers/)

_September 7, 2025_· [💬 Join the Discussion](https://akitaonrails.github.io/en/2025/09/07/omarchy-2-0-mise-for-organizing-dev-environments/#disqus_wrapper)

_If you're lazy, click [here](https://claude.ai/new?q=Please+open+this+URL+with+web+search+and+read+the+full+article%3A+https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F%0A%0AAfter+reading+the+real+content+of+that+article%2C+do+the+following%3A%0A1%29+Summarize+the+5+most+important+points+and+the+conclusion.%0A2%29+After+the+summary%2C+tell+the+reader+what+key+details%2C+data+and+insights+they+are+missing+by+not+reading+the+full+article.+Be+specific+enough+to+make+them+curious.%0A3%29+Remind+them+they+can+keep+asking+follow-up+questions+about+this+article+right+here+in+this+chat.%0A4%29+Suggest+one+good+follow-up+question+they+could+ask+as+a+starter. "Left click opens Claude. Right click to choose Claude or Grok.") for the TL;DR_

[Claude](https://claude.ai/new?q=Please+open+this+URL+with+web+search+and+read+the+full+article%3A+https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F%0A%0AAfter+reading+the+real+content+of+that+article%2C+do+the+following%3A%0A1%29+Summarize+the+5+most+important+points+and+the+conclusion.%0A2%29+After+the+summary%2C+tell+the+reader+what+key+details%2C+data+and+insights+they+are+missing+by+not+reading+the+full+article.+Be+specific+enough+to+make+them+curious.%0A3%29+Remind+them+they+can+keep+asking+follow-up+questions+about+this+article+right+here+in+this+chat.%0A4%29+Suggest+one+good+follow-up+question+they+could+ask+as+a+starter.) [ChatGPT](https://chatgpt.com/?q=Please+open+this+URL+with+web+search+and+read+the+full+article%3A+https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F%0A%0AAfter+reading+the+real+content+of+that+article%2C+do+the+following%3A%0A1%29+Summarize+the+5+most+important+points+and+the+conclusion.%0A2%29+After+the+summary%2C+tell+the+reader+what+key+details%2C+data+and+insights+they+are+missing+by+not+reading+the+full+article.+Be+specific+enough+to+make+them+curious.%0A3%29+Remind+them+they+can+keep+asking+follow-up+questions+about+this+article+right+here+in+this+chat.%0A4%29+Suggest+one+good+follow-up+question+they+could+ask+as+a+starter.) [Grok](https://grok.com/?q=Please+open+this+URL+with+web+search+and+read+the+full+article%3A+https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F%0A%0AAfter+reading+the+real+content+of+that+article%2C+do+the+following%3A%0A1%29+Summarize+the+5+most+important+points+and+the+conclusion.%0A2%29+After+the+summary%2C+tell+the+reader+what+key+details%2C+data+and+insights+they+are+missing+by+not+reading+the+full+article.+Be+specific+enough+to+make+them+curious.%0A3%29+Remind+them+they+can+keep+asking+follow-up+questions+about+this+article+right+here+in+this+chat.%0A4%29+Suggest+one+good+follow-up+question+they+could+ask+as+a+starter.)

Continuing my posts about [Omarchy](https://www.akitaonrails.com/en/tags/omarchy/), here’s another introductory post, this time about [Mise-en-place](https://mise.jdx.dev/getting-started.html), which already comes pre-installed. On Omarchy, if you press “Super+Alt+Space” the main menu will open. Pick “Install” and then “Development” and you’ll see several languages/frameworks you can install, like Ruby on Rails or Go.

But you don’t need to use these menus. Let me explain.

On a regular Arch Linux or Ubuntu, an amateur would install ruby or python doing something like this:

```
# arch
yay -S ruby python3
# ubuntu
apt install ruby python3
```

**This is the WRONG way.**

These commands will install the latest version of each language, and every time you update the system with `yay -Syu` or `apt upgrade`, they’ll pull in even newer versions.

The thing is, if you develop real projects, **you don’t want the versions to change**.

The version deployed on the cloud server and the version on your local machine **MUST BE THE SAME**.

If you’re using Ruby v3.0.7 and Node.js 22.19.0, you can’t be held hostage to the fact that when you update your system, out of nowhere Ruby 3.4.5 and Node 24.7.0 show up. Everything will start breaking and you’ll be super confused without knowing why. This is the most basic mistake a junior developer makes.

To avoid this, every project you’re working on MUST BE LOCKED TO FIXED VERSIONS.

The easiest way to do this in 2025 is using **MISE**. As I said, it already comes installed and activated on Omarchy, but if you’re using another distro just install Mise manually:

```
yay -S mise

# .bashrc
eval $(mise activate bash)
```

Adapt this for ZSH, Fish or whatever shell you’re using, read the [documentation](https://mise.jdx.dev/installing-mise.html)

Now navigate to your project directory, for example:

```
cd ~/Projects/AkitaOnRails.com
```

And lock the versions:

```
mise use ruby@3.2.3
mise use node@14.21.3
```

This will create a `.tool-versions` file that you should add to your repository’s git:

```
❯ cat .tool-versions
ruby 3.2.3
nodejs 14.21.3

❯ git add .tool-versions
```

And done, every time you `cd` into the directory, Mise will activate exactly the right version for that project. Look:

```
AkitaOnRails.com [ master][$!?⇡][ v24.7.0][💎 v3.2.3]
❯ ruby -v
ruby 3.2.3 (2024-01-18 revision 52bb2ac0a6) [x86_64-linux]

AkitaOnRails.com [ master][$!?⇡][ v24.7.0][💎 v3.2.3]
❯ which ruby
/home/akitaonrails/.local/share/mise/installs/ruby/3.2.3/bin/ruby
```

Notice that, if you’re using the [Starship](https://akitaonrails.com/en/2025/09/07/omarchy-2-0-zsh-configs/) prompt I explained in the previous post, with a preset like Pure Prompt, it shows the version of each language in the prompt so it’s easy to see if you’re on the wrong version.

In this case, if you read carefully, you’ve probably already noticed that **YES, I’M ON THE WRONG VERSION** of Node.js. Look how the prompt says I’m using Node 24.7.0 but the `.tool-versions` file asks for 14.21.3.

The reason it’s “missing” is because this machine was recently installed, but the project is old.

So let’s check:

```
AkitaOnRails.com [ master][$!?⇡][ v24.7.0][💎 v3.2.3]
❯ mise list
Tool    Version            Source                                              Requested
go      1.25.0             ~/.config/mise/config.toml                          latest
node    14.21.3 (missing)  /mnt/data/Projects/AkitaOnRails.com/.tool-versions  14.21.3
node    22.18.0
python  3.13.7
ruby    3.2.3              /mnt/data/Projects/AkitaOnRails.com/.tool-versions  3.2.3
ruby    3.4.5
```

See how in the `mise list` output it says 14.21.3 is “missing”. So let’s install it:

```
AkitaOnRails.com [ master][$!?⇡][ v24.7.0][💎 v3.2.3]
❯ mise use node@14.21.3
mise /mnt/data/Projects/AkitaOnRails.com/.tool-versions tools: node@14.21.3

AkitaOnRails.com [ master][$!?⇡][ v14.21.3][💎 v3.2.3]
❯
```

With the `mise use` command we can ask it to install and use a particular version. If it’s not already installed, it will install it. Notice how after that the Starship prompt changed to reflect that we’re now using 14.21.3. That’s the right way.

If you’re not necessarily in a project directory with locked versions, you can still run commands using a specific version, like this:

```
mise exec ruby@3.2.1 -- ruby ...
```

Say you want to generate a Rails project on a specific Ruby version:

```
mise exec ruby@3.2.3 -- rails new todo-exercise
```

The same goes for generators in Node, like Next.js or any other framework.

I haven’t checked whether LazyVim on Omarchy comes configured this way, but in case it doesn’t, for NeoVim to support Mise you need to add this:

```lua
-- Prepend mise shims to PATH
vim.env.PATH = vim.env.HOME .. "/.local/share/mise/shims:" .. vim.env.PATH
```

Just put this in `~/.config/nvim/lua/config/mise.lua` and it should load the correct path. To integrate with other editors, check [this documentation](https://mise.jdx.dev/ide-integration.html). There are TONS of advanced options and it’s worth reading about them in the [Dev-Tools section](https://mise.jdx.dev/dev-tools/), but the basics are what I listed here.

## And databases?? [Permalink for this section](https://akitaonrails.github.io/en/2025/09/07/omarchy-2-0-mise-for-organizing-dev-environments/\#and-databases)

The same goes for databases. Every project should be locked to a specific version identical to what’s running on the production server and should never depend on operating system packages. You can use mise for this but the most recommended option is to use Docker. Every project **MUST** have a `docker-compose.yml` to spin up only the databases. You don’t need to spin up containers for languages, for that it’s better to use Mise.

If you don’t understand Docker, I made videos teaching it:

Entendendo Funcionamento de Containers - YouTube

Tap to unmute

[Entendendo Funcionamento de Containers](https://www.youtube.com/watch?v=85k8se4Zo70) [Fabio Akita](https://www.youtube.com/channel/UCib793mnUOhWymCh2VJKplQ)

Fabio Akita569K subscribers

[Watch on](https://www.youtube.com/watch?v=85k8se4Zo70)

Configurando Docker Compose, Postgres, com Testes de Carga - Parte Final da Rinha de Backend - YouTube

Tap to unmute

[Configurando Docker Compose, Postgres, com Testes de Carga - Parte Final da Rinha de Backend](https://www.youtube.com/watch?v=-yGHG3pnHLg) [Fabio Akita](https://www.youtube.com/channel/UCib793mnUOhWymCh2VJKplQ)

Fabio Akita569K subscribers

[Watch on](https://www.youtube.com/watch?v=-yGHG3pnHLg)

Adding up Mise + Docker Compose + LazyVim, that’s everything you need to be a productive web developer, while also using your machine’s resources efficiently. Every developer NEEDS to learn this combo of options. Omarchy already brings it all pre-installed, which is why it’s been my recommendation for every beginner.

Don’t worry: Arch Linux (with archinstall) is as easy to install as an Ubuntu or Linux Mint, and Omarchy’s Hyprland is much prettier and smoother than MacOS. The best of both worlds. Learn it today!

Recomendações Disqus

Não foi possível carregar as «Recomendações» da Disqus. Se for um moderador, consulte o nosso [guia de resolução de problemas](https://docs.disqus.com/help/83/).

❮

- 15 dias atrás
- 2 comentários

Codes of conduct were sold as protecting minorities and used to cancel Eich, …

- um mês atrás
- 7 comentários

Do bloqueio do X à majorante de pena pra VPN: o Brasil ensaia censura …

- um mês atrás
- 11 comentários

O ai-memory chegou na versão 2.0 com formato aberto OKF, embeddings …

- um mês atrás
- 2 comentários

ai-memory hit version 2.0 with the open OKF format, local embeddings on by …

- 15 dias atrás
- 8 comentários

Códigos de conduta venderam proteger minorias e serviram pra cancelar …

- 12 dias atrás
- 21 comentários

A corrida da IA por energia enterrou a pauta climática: big techs religando …

- 7 dias atrás
- 12 comentários

Com LLM de fronteira errando menos que a maioria dos devs …

- 12 dias atrás
- 10 comentários

Skills de agente são só prompts em arquivos de texto. Eu mantenho 25 …

❯

Comentários Disqus

Não foi possível carregar o Diqus. Se você é o moderador, por favor veja o nosso [guia de problemas](https://docs.disqus.com/help/83/).

What do you think?

0 Respostas

![Upvote](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/upvote-512x512.png)

Upvote

![Funny](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/funny-512x512.png)

Funny

![Love](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/love-512x512.png)

Love

![Surprised](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/surprised-512x512.png)

Surprised

![Angry](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/angry-512x512.png)

Angry

![Sad](https://c.disquscdn.com/next/current/publisher-admin/assets/img/emoji/sad-512x512.png)

Sad

G

Iniciar a discussão...

﻿

Comentar!

###### Fazer login com

###### ou registre-se no Disqus  ou escolha um nome

### O Disqus é uma rede de conversação

- Não seja um babaca ou faça qualquer coisa ilegal. Tudo é mais fácil dessa maneira.

[Leia todos os termos e condições](https://docs.disqus.com/kb/terms-and-policies/)

Esta plataforma de comentário é hospedada pela Disqus, Inc. Autorizo a Disqus e suas afiliadas a:

- Use, venda e compartilhe minha informação para me permitir usar seus serviços de comentário e para fins de marketing, incluindo publicidade comportamental em diferentes contextos, conforme descrito em nossos [Termos de Serviço](https://help.disqus.com/customer/portal/articles/466260-terms-of-service) e [Política de Privacidade](https://disqus.com/privacy-policy), incluindo complementar essa informação com outros dados sobre mim, como meus dados de navegação e localização.
- Entre em contato comigo ou permita que outros entrem em contato comigo por e-mail com ofertas de bens ou serviços
- Procure qualquer informação pessoal sensível que eu enviar em um comentário. Veja nossa [Política de Privacidade](https://disqus.com/privacy-policy) para mais informações

Confirmo que tenho 18 anos ou mais

- [Favoritar esta discussão](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default# "Favoritar esta discussão")

  - ## Discussão favoritada!



    Favoritar significa que esta é uma discussão que vale a pena compartilhar. Ela é compartilhada nos feeds Disqus de seus seguidores e dá elogios ao criador!


     [Encontre Outras Discussões](https://disqus.com/home/?utm_source=disqus_embed&utm_content=recommend_btn)

[Compartilhar](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default#)

  - Tweetar esta discussão
  - Compartilhar esta discussão no Facebook
  - Compartilhe esta discussão por e-mail
  - Copie o link da discussão

  - [Mais votados](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default#)
  - [Mais recentes](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default#)
  - [Mais antigos](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default#)

Seja o primeiro a comentar.

[Carregar mais comentários](https://disqus.com/embed/comments/?base=default&f=akitaonrails&t_i=%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_u=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F&t_d=&t_t=&s_o=default#)

![](https://io.narrative.io/?companyId=19&id=disqus_id%3Ackuiulo19hbtic&ret=img&ref=https%3A%2F%2Fakitaonrails.github.io%2Fen%2F2025%2F09%2F07%2Fomarchy-2-0-mise-for-organizing-dev-environments%2F)![](https://io.narrative.io/?companyId=1952&id=disqus_id%3Ackuiulo19hbtic&red=https%3A%2F%2Fpx.ads.linkedin.com%2Fdb_sync%3Fpid%3D16269%26puuid%3D%24%7Bnarrative.id.value%7D%26rand%3D0.10055541963)

live.rezync.com

# live.rezync.com is blocked

This page has been blocked by an extension

- Try disabling your extensions.

ERR\_BLOCKED\_BY\_CLIENT

Reload


This page has been blocked by an extension

![](<Base64-Image-Removed>)![](<Base64-Image-Removed>)

pippio.com

# pippio.com is blocked

This page has been blocked by an extension

- Try disabling your extensions.

ERR\_BLOCKED\_BY\_CLIENT

Reload


This page has been blocked by an extension

![](<Base64-Image-Removed>)![](<Base64-Image-Removed>)