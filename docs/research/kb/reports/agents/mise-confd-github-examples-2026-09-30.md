# GitHub code search: mise conf.d fragments vs global config.toml tasks (2026-09-30)

Method: gh api search/code, per_page=10, each hit re-fetched via contents API and grepped (conf.d path, `[tasks` header, conf.d symlink). Controls: a must-hit query and a fresh absent term.

## control-must-hit
- query: `path:.config/mise filename:config.toml`
- rc=0 total_count=1020
  - [apollographql/apollo-server/.config/mise/config.toml](https://github.com/apollographql/apollo-server/blob/0c22029c2af47d3829e730e9820c01cef0557627/.config/mise/config.toml) fetch_rc=0 
  - [craftzdog/dotfiles/.config/mise/config.toml](https://github.com/craftzdog/dotfiles/blob/bf2867469b8b7f0260e974a47297a7df61d53052/.config/mise/config.toml) fetch_rc=0 
  - [hashintel/hash/.config/mise/config.toml](https://github.com/hashintel/hash/blob/a6f5727b1f5424c48487c44c24c48c23ba9d3758/.config/mise/config.toml) fetch_rc=0 
  - [apollographql/router/.config/mise/config.toml](https://github.com/apollographql/router/blob/ef3569f14c72be22af568f064fcafa5f2215008c/.config/mise/config.toml) fetch_rc=0 
  - [yutkat/dotfiles/.config/mise/config.toml](https://github.com/yutkat/dotfiles/blob/dfafe9f3e0f76f3c56339e6fdafbea49d4f5a321/.config/mise/config.toml) fetch_rc=0 defines-tasks symlinks-conf.d
  - [bigskysoftware/missing/.config/mise/config.toml](https://github.com/bigskysoftware/missing/blob/b74e1c0da398b2a1ae8a91253cd45337dac12559/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [SeniorMars/dotfiles/.config/mise/config.toml](https://github.com/SeniorMars/dotfiles/blob/ea99c6844e1d8938024ea4753d8b9329bd89d7df/.config/mise/config.toml) fetch_rc=0 
  - [Matt-FTW/dotfiles/.config/mise/config.toml](https://github.com/Matt-FTW/dotfiles/blob/e5b4456a1f1b569aa71fc2c5a3dcb76832639bc2/.config/mise/config.toml) fetch_rc=0 
  - [finos/morphir/.config/mise/config.toml](https://github.com/finos/morphir/blob/90f7df0a125acc27db45a4b98d2b2883ba0ec471/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [masasam/dotfiles/.config/mise/config.toml](https://github.com/masasam/dotfiles/blob/80422354115c54c1bb3e7d4de8a65aecc7e9e924/.config/mise/config.toml) fetch_rc=0 

## control-absent
- query: `qzvxkw_nonexist_7ad6_20260930 path:.config/mise`
- rc=0 total_count=0

## global-confd
- query: `path:.config/mise/conf.d`
- rc=0 total_count=341
  - [yutkat/dotfiles/.config/mise/conf.d/neovim.toml](https://github.com/yutkat/dotfiles/blob/dfafe9f3e0f76f3c56339e6fdafbea49d4f5a321/.config/mise/conf.d/neovim.toml) fetch_rc=0 conf.d-path
  - [apphane-dev/nehir/.config/mise/conf.d/tools.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tools.toml) fetch_rc=0 conf.d-path
  - [apphane-dev/nehir/.config/mise/conf.d/_config.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/_config.toml) fetch_rc=0 conf.d-path
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-dev.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-dev.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-build.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-build.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-install.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-install.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-quality.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-quality.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-raycast.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-raycast.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-workflow.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-workflow.toml) fetch_rc=0 conf.d-path defines-tasks
  - [tbhb/vale-ai-tells/.config/mise/conf.d/20-repotools-env.toml](https://github.com/tbhb/vale-ai-tells/blob/dd60c5dc0d5432f71b0113fe2003fb06d069a71f/.config/mise/conf.d/20-repotools-env.toml) fetch_rc=0 conf.d-path

## chezmoi-confd
- query: `path:dot_config/mise/conf.d`
- rc=0 total_count=109
  - [henrebotha/dotfiles/dot_config/mise/conf.d/rust.toml](https://github.com/henrebotha/dotfiles/blob/edc9054000fe671e28aaa17ad05e35e61bfa9b50/dot_config/mise/conf.d/rust.toml) fetch_rc=0 conf.d-path
  - [henrebotha/dotfiles/dot_config/mise/conf.d/node.toml](https://github.com/henrebotha/dotfiles/blob/edc9054000fe671e28aaa17ad05e35e61bfa9b50/dot_config/mise/conf.d/node.toml) fetch_rc=0 conf.d-path
  - [henrebotha/dotfiles/dot_config/mise/conf.d/ruby.toml](https://github.com/henrebotha/dotfiles/blob/edc9054000fe671e28aaa17ad05e35e61bfa9b50/dot_config/mise/conf.d/ruby.toml) fetch_rc=0 conf.d-path
  - [henrebotha/dotfiles/dot_config/mise/conf.d/python.toml](https://github.com/henrebotha/dotfiles/blob/edc9054000fe671e28aaa17ad05e35e61bfa9b50/dot_config/mise/conf.d/python.toml) fetch_rc=0 conf.d-path
  - [mushanyoung/ravy/dot_config/mise/conf.d/99-custom.toml.tmpl](https://github.com/mushanyoung/ravy/blob/0a63867c03c73651aabf3a7408cb96f31933da58/dot_config/mise/conf.d/99-custom.toml.tmpl) fetch_rc=0 conf.d-path
  - [giard-alexandre/dotfiles/dot_config/mise/conf.d/tools.toml.tmpl](https://github.com/giard-alexandre/dotfiles/blob/04acf9c770f624dec7e902d05b69ca094f0a02c8/dot_config/mise/conf.d/tools.toml.tmpl) fetch_rc=0 conf.d-path
  - [acjackman/dotfiles/dot_config/mise/conf.d/symlink_moov.toml.tmpl](https://github.com/acjackman/dotfiles/blob/f705346aeab3b2c26371912b38851d1bb88a0bb4/dot_config/mise/conf.d/symlink_moov.toml.tmpl) fetch_rc=0 conf.d-path
  - [supermomonga/dotfiles-chezmoi/dot_config/mise/conf.d/global.toml.tmpl](https://github.com/supermomonga/dotfiles-chezmoi/blob/08c53e5eba3b4dbc4348ae4d0ab22b3a35c97028/dot_config/mise/conf.d/global.toml.tmpl) fetch_rc=0 conf.d-path
  - [jotu/dotfiles/dot_config/mise/conf.d/00-base.toml.tmpl](https://github.com/jotu/dotfiles/blob/83a534343da15e25820c9183da8d94ac66f4c6ec/dot_config/mise/conf.d/00-base.toml.tmpl) fetch_rc=0 conf.d-path defines-tasks
  - [niklas-heer/dotfiles/dot_config/mise/conf.d/capture-gate.toml](https://github.com/niklas-heer/dotfiles/blob/7743a0ab4d7840c00fb2ddf76f947ca60b84c04b/dot_config/mise/conf.d/capture-gate.toml) fetch_rc=0 conf.d-path

## confd-tasks
- query: `path:.config/mise/conf.d tasks`
- rc=0 total_count=147
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-dev.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-dev.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-build.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-build.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-install.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-install.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-quality.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-quality.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-raycast.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-raycast.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/nehir/.config/mise/conf.d/tasks-workflow.toml](https://github.com/apphane-dev/nehir/blob/f097f35a22c463b343c16e29327bd317b7573171/.config/mise/conf.d/tasks-workflow.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/karkas/.config/mise/conf.d/tasks-dev.toml](https://github.com/apphane-dev/karkas/blob/e56953d3910dc294910277fc7f88d3a2b058af8b/.config/mise/conf.d/tasks-dev.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/karkas/.config/mise/conf.d/tasks-park.toml](https://github.com/apphane-dev/karkas/blob/e56953d3910dc294910277fc7f88d3a2b058af8b/.config/mise/conf.d/tasks-park.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/karkas/.config/mise/conf.d/tasks-build.toml](https://github.com/apphane-dev/karkas/blob/e56953d3910dc294910277fc7f88d3a2b058af8b/.config/mise/conf.d/tasks-build.toml) fetch_rc=0 conf.d-path defines-tasks
  - [apphane-dev/karkas/.config/mise/conf.d/tasks-quality.toml](https://github.com/apphane-dev/karkas/blob/e56953d3910dc294910277fc7f88d3a2b058af8b/.config/mise/conf.d/tasks-quality.toml) fetch_rc=0 conf.d-path defines-tasks

## confd-symlink-ln
- query: `"mise/conf.d" ln`
- rc=0 total_count=358
  - [jdx/mise/docs/configuration.md](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/docs/configuration.md) fetch_rc=0 defines-tasks symlinks-conf.d
  - [coder/coder/dogfood/coder/ubuntu-26.04/Dockerfile.base](https://github.com/coder/coder/blob/1f7aa2d14c63d06521ce540f9c18cba8d290261d/dogfood/coder/ubuntu-26.04/Dockerfile.base) fetch_rc=0 
  - [tjun/dotfiles/README.md](https://github.com/tjun/dotfiles/blob/c5bf1fe02407fba3ffbd5968f3308803abed8801/README.md) fetch_rc=0 symlinks-conf.d
  - [bamaas/Hunt/README.md](https://github.com/bamaas/Hunt/blob/9cb6a466861208675e051bb874c259886390c692/README.md) fetch_rc=0 symlinks-conf.d
  - [s2terminal/dotfiles/install.sh](https://github.com/s2terminal/dotfiles/blob/26d17ae9212b09b83886eaebc1b92f2b08a00b8c/install.sh) fetch_rc=0 symlinks-conf.d
  - [jdx/mise/src/config/config_file/config_root.rs](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/src/config/config_file/config_root.rs) fetch_rc=0 symlinks-conf.d
  - [y-kamiya/dotfiles/setup.sh](https://github.com/y-kamiya/dotfiles/blob/422c1115eb728827238ac3077edb558f3f58d830/setup.sh) fetch_rc=0 
  - [lightster/.dotfiles/mise/tasks/configs.sh](https://github.com/lightster/.dotfiles/blob/1917a189ad0b8b919bb523168f5e447d68fa78f6/mise/tasks/configs.sh) fetch_rc=0 symlinks-conf.d
  - [klp2/dot-files/install.sh](https://github.com/klp2/dot-files/blob/6a42ca18edcbc6ec96a952d64496824507a7e455/install.sh) fetch_rc=0 symlinks-conf.d
  - [jdx/mise/src/config/mod.rs](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/src/config/mod.rs) fetch_rc=0 symlinks-conf.d

## confd-symlink-word
- query: `"mise/conf.d" symlink`
- rc=0 total_count=538
  - [jdx/mise/docs/configuration.md](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/docs/configuration.md) fetch_rc=0 defines-tasks symlinks-conf.d
  - [jdx/mise/src/config/mod.rs](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/src/config/mod.rs) fetch_rc=0 symlinks-conf.d
  - [jdx/mise/src/config/config_file/config_root.rs](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/src/config/config_file/config_root.rs) fetch_rc=0 symlinks-conf.d
  - [jdx/mise/docs/bootstrap.md](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/docs/bootstrap.md) fetch_rc=0 defines-tasks symlinks-conf.d
  - [jdx/mise/src/lockfile.rs](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/src/lockfile.rs) fetch_rc=0 symlinks-conf.d
  - [monumental-archive/.github/mise/committed.sh](https://github.com/monumental-archive/.github/blob/2f5bad239e468ea5fe4c99635edc243f92da45f6/mise/committed.sh) fetch_rc=0 symlinks-conf.d
  - [samhvw8/dotfiles/mise/conf.d/dotfiles.toml](https://github.com/samhvw8/dotfiles/blob/cd1f6f1bb78ec04cfecf8be032db34b0ae65dbac/mise/conf.d/dotfiles.toml) fetch_rc=0 conf.d-path defines-tasks symlinks-conf.d
  - [davidosomething/dotfiles/README.md](https://github.com/davidosomething/dotfiles/blob/909003a5fa84d5a0392426d424eaa761d2f48e18/README.md) fetch_rc=0 symlinks-conf.d
  - [jdx/mise/settings.toml](https://github.com/jdx/mise/blob/8a1042b340c82036d98469a39cdf50cf6d57c4b3/settings.toml) fetch_rc=0 symlinks-conf.d
  - [lvancrayelynghe/dotfiles/CLAUDE.md](https://github.com/lvancrayelynghe/dotfiles/blob/b912a691ef4d7cfe22249de1ff4d4cfb48369410/CLAUDE.md) fetch_rc=0 symlinks-conf.d

## global-config-tasks
- query: `path:.config/mise filename:config.toml tasks`
- rc=0 total_count=126
  - [yutkat/dotfiles/.config/mise/config.toml](https://github.com/yutkat/dotfiles/blob/dfafe9f3e0f76f3c56339e6fdafbea49d4f5a321/.config/mise/config.toml) fetch_rc=0 defines-tasks symlinks-conf.d
  - [bigskysoftware/missing/.config/mise/config.toml](https://github.com/bigskysoftware/missing/blob/b74e1c0da398b2a1ae8a91253cd45337dac12559/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [Matt-FTW/dotfiles/.config/mise/config.toml](https://github.com/Matt-FTW/dotfiles/blob/e5b4456a1f1b569aa71fc2c5a3dcb76832639bc2/.config/mise/config.toml) fetch_rc=0 
  - [finos/morphir/.config/mise/config.toml](https://github.com/finos/morphir/blob/90f7df0a125acc27db45a4b98d2b2883ba0ec471/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [harperreed/dotfiles/.config/mise/config.toml](https://github.com/harperreed/dotfiles/blob/551906762cc7326fa6f4025fcac442100cd92a5d/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [extsoft/elegant-git/.config/mise/config.toml](https://github.com/extsoft/elegant-git/blob/1b9aaecb08f9f266f79a0a9831fc596b942bc8e3/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [disrupted/dotfiles/.config/mise/config.toml](https://github.com/disrupted/dotfiles/blob/2df5f6c7516eb2c74a351386c13f1142ca6ab8ac/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [infogulch/xtemplate/.config/mise/config.toml](https://github.com/infogulch/xtemplate/blob/64a569a35f6bb79e1bdc67566026aeba72ee9de3/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [theowenyoung/home/.config/mise/config.toml](https://github.com/theowenyoung/home/blob/9bf3ea9b31cf1f05a149b702dca26ebd51c34924/.config/mise/config.toml) fetch_rc=0 defines-tasks
  - [finos/morphir-scala/.config/mise/config.toml](https://github.com/finos/morphir-scala/blob/dc2de8c53010c37d79f0a6da3084b555ea5cbeb9/.config/mise/config.toml) fetch_rc=0 

## chezmoi-global-tasks
- query: `path:dot_config/mise filename:config.toml tasks`
- rc=0 total_count=63
  - [DanielMSchmidt/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/DanielMSchmidt/dotfiles/blob/b0b48d89f4121c5898ea5a8f980f4b8786ef3a74/dot_config/mise/config.toml.tmpl) fetch_rc=0 
  - [yuk1ty/dotfiles/dot_config/mise/config.toml](https://github.com/yuk1ty/dotfiles/blob/75d6bad6034fa552b8e66566bee193d8429777b4/dot_config/mise/config.toml) fetch_rc=0 defines-tasks
  - [aFuzzyBear/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/aFuzzyBear/dotfiles/blob/57632c6e3757cda6b7b2b69daf62be92d583b14d/dot_config/mise/config.toml.tmpl) fetch_rc=0 defines-tasks symlinks-conf.d
  - [BasixKOR/.dotfiles/dot_config/mise/config.toml](https://github.com/BasixKOR/.dotfiles/blob/7e289b9cccf86bac02362f56616fce154cddae21/dot_config/mise/config.toml) fetch_rc=0 
  - [aguil/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/aguil/dotfiles/blob/91c60339f87d9c43307e61c0e180ea3deddf5aa9/dot_config/mise/config.toml.tmpl) fetch_rc=0 
  - [phyrog/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/phyrog/dotfiles/blob/7ef0b8fef9b146497b55ba2901c3b456b106b679/dot_config/mise/config.toml.tmpl) fetch_rc=0 defines-tasks
  - [LandazuriPaul/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/LandazuriPaul/dotfiles/blob/10e1e60adc27a3baef00f5662f7eef709c5821de/dot_config/mise/config.toml.tmpl) fetch_rc=0 defines-tasks
  - [zeekcheung/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/zeekcheung/dotfiles/blob/bd696a09f6c3828d5b3c2cc48e0c3fe7ba1bfa39/dot_config/mise/config.toml.tmpl) fetch_rc=0 defines-tasks
  - [katsuobushiFPGA/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/katsuobushiFPGA/dotfiles/blob/2f154ef4db21d8305b5a0bb1d3db7f08330d4139/dot_config/mise/config.toml.tmpl) fetch_rc=0 defines-tasks
  - [mimukit/dotfiles/dot_config/mise/config.toml.tmpl](https://github.com/mimukit/dotfiles/blob/c45d4161e20297dc2fef86134ebda06d505308c3/dot_config/mise/config.toml.tmpl) fetch_rc=0 
