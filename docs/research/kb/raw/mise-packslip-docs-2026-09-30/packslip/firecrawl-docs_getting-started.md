[Skip to content](https://packslip.dev/docs/getting-started/#main)

# Getting started

This walkthrough creates a small release and verifies it locally. It uses
an unlogged key signature so you can try the format without a CI identity
or a connection to the signing services. For publishing, use
[GitHub Actions](https://packslip.dev/docs/publishing/) or a logged key signature.

## Install packslip

We recommend [mise](https://mise.jdx.dev/getting-started.html) to install
packslip and manage its version. You can also download a binary or build
from source.

miseDownloadBuild from source

**mise**

With [mise installed and activated](https://mise.jdx.dev/getting-started.html), run:

Copy

```sh
mise use -g github:jdx/packslip
packslip version
```

This downloads a release binary and makes packslip available globally
through mise. Omit `-g` to manage it in the current project instead.

**Download**

Download an archive for your operating system and architecture from the
[GitHub releases](https://github.com/jdx/packslip/releases). Extract it
and put the `packslip` executable on PATH, then check the installation:

Copy

```sh
packslip version
```

**Build from source**

With Git and Rust 1.95 or newer installed:

Copy

```sh
git clone https://github.com/jdx/packslip.git
cd packslip
cargo install --path . --locked
packslip version
```

Cargo installs the executable in its bin directory, usually `~/.cargo/bin`.
Make sure that directory is on PATH. Use a separate empty directory for
the walkthrough below.

## Create a sample release

The following commands use a POSIX shell and `tar`. Run them in an empty
directory. The sample is a portable shell script, so it needs no
platform-specific compiler.

Copy

```sh
mkdir -p staging/bin dist
printf '#!/bin/sh\nprintf "hello from mytool\\n"\n' > staging/bin/mytool
chmod +x staging/bin/mytool
tar -czf dist/mytool-1.2.3.tar.gz -C staging bin
packslip keygen --out release.key
```

`keygen` writes the private key to `release.key` and the public key to
`release.pub`. Keep the private key out of source control. Consumers need
only the public key.

## Sign the manifest

Copy

```sh
packslip create \
  --project mytool.example.com \
  --version 1.2.3 \
  --key release.key --no-log \
  --out dist \
  --url-base https://mytool.example.com/releases/1.2.3 \
  --bin mytool \
  dist/mytool-1.2.3.tar.gz:any
```

The command writes `dist/packslip.sigstore.json`. It hashes the archive,
finds `bin/mytool` inside it, and records the download URL. The `:any`
suffix explicitly marks the artifact as platform-independent. The example
URL is metadata; `create` neither contacts it nor uploads files to it.

## Read the manifest

The bundle contains a signed statement. Its release metadata looks like
this excerpt (the digest is abbreviated):

Copy

```json
{
  "subject": [{\
    "name": "mytool-1.2.3.tar.gz",\
    "digest": { "sha256": "..." }\
  }],
  "predicateType": "https://packslip.dev/release/v1",
  "predicate": {
    "project": "mytool.example.com",
    "version": "1.2.3",
    "artifacts": [{\
      "name": "mytool-1.2.3.tar.gz",\
      "url": "https://mytool.example.com/releases/1.2.3/mytool-1.2.3.tar.gz",\
      "format": "tar.gz",\
      "bin": ["bin/mytool"]\
    }]
  }
}
```

| Field | What the consumer does with it |
| --- | --- |
| `subject` | Checks the downloaded file against its signed digest. |
| `predicateType` | Recognizes the payload as a packslip release statement. |
| `project` and `version` | Confirms that this is the requested project and release. |
| `artifacts[].name` | Connects the artifact metadata to its entry in `subject`. |
| `url` and `format` | Finds the file and determines how to unpack it. |
| `bin` | Finds the executable at its actual archive path. |

This sample omits `os`, `arch`, and `libc` because `:any` declared no
platform restriction. The complete statement also includes the artifact’s
size, publication time, signing identity, and other generated fields.
The surrounding bundle carries the signature and verification material.

The excerpt explains the structure; it is not a complete signed bundle.
Use the generated file in the verification step below.

## Verify the archive

Copy

```sh
packslip verify dist/packslip.sigstore.json \
  --pubkey release.pub --allow-unlogged \
  --artifact dist/mytool-1.2.3.tar.gz
```

A successful exit means the bundle passed verification against your key
and the supplied archive matched its signed digest and size.
`--allow-unlogged` is necessary because this example used `--no-log`.
Without `--artifact`, the command checks the bundle but not the archive.

To inspect the signed metadata:

Copy

```sh
packslip show dist/packslip.sigstore.json
```

`show` only decodes the statement; it does not verify it.

## Publish a real release

For a key-signed release, omit `--no-log` when creating the bundle and
`--allow-unlogged` when verifying it. Signing then contacts Rekor to log
the signature. Reuse your signing key and distribute the public key
through a channel consumers trust.

Upload the artifact and bundle to their declared URLs. For a project on
your own domain, also [publish a signed release list](https://packslip.dev/docs/release-lists/).
For GitHub, [use the action](https://packslip.dev/docs/publishing/) to sign with the workflow’s
identity instead. See [Artifact configuration](https://packslip.dev/docs/describing-releases/)
to adapt the example to your release layout.