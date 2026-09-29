[Skip to content](https://mise.jdx.dev/mise-cookbook/terraform.html#VPContent)

On this page

# Terraform and OpenTofu Cookbook [​](https://mise.jdx.dev/mise-cookbook/terraform.html\#terraform-and-opentofu-cookbook)

Use tasks to keep infrastructure commands pointed at the same working directory. The recipe assumes a `terraform/` directory containing your configuration and any provider credentials already configured in the environment.

## Managing `terraform`/`opentofu` Projects [​](https://mise.jdx.dev/mise-cookbook/terraform.html\#managing-terraform-opentofu-projects)

Terraform configuration often lives in a `terraform/` subdirectory, which means running commands like `terraform -chdir=terraform plan`. The following config lets you invoke all of them through `mise` tasks instead.

mise.toml

toml

```
[tools]
terraform = "1"

[tasks."terraform:init"]
description = "Initializes a Terraform working directory"
run = "terraform -chdir=terraform init"

[tasks."terraform:plan"]
description = "Generates an execution plan for Terraform"
depends = ["terraform:init"]
run = "terraform -chdir=terraform plan"

[tasks."terraform:apply"]
description = "Applies the changes required to reach the desired state of the configuration"
depends = ["terraform:init"]
interactive = true
run = "terraform -chdir=terraform apply"

[tasks."terraform:destroy"]
description = "Destroy Terraform-managed infrastructure"
depends = ["terraform:init"]
interactive = true
run = "terraform -chdir=terraform destroy"

[tasks."terraform:validate"]
description = "Validates the Terraform files"
depends = ["terraform:init"]
run = "terraform -chdir=terraform validate"

[tasks."terraform:format"]
description = "Formats the Terraform files"
run = "terraform -chdir=terraform fmt"

[tasks."terraform:format-check"]
description = "Check formatting without changing files"
run = "terraform -chdir=terraform fmt -check"

[tasks."terraform:check"]
description = "Check formatting and validate the configuration"
depends = ["terraform:format-check", "terraform:validate"]
```

Run `mise run terraform:check` for validation, then `mise run terraform:plan` to inspect proposed changes. `terraform:format` is the separate task that rewrites formatting. Initialization may download providers and update the dependency lockfile even when the selected task is a check.

`terraform:apply` and `terraform:destroy` retain Terraform's confirmation prompts; `interactive = true` gives those commands access to the terminal. This recipe does not save a plan file, so `apply` calculates its own plan before asking for approval.

For OpenTofu, replace the tool declaration with `opentofu = "1"` and the command name `terraform` with `tofu`. The `terraform/` directory and task names can stay as they are, or be renamed to match your project.

If you use a local dotenv file for credentials, add [`env._.file`](https://mise.jdx.dev/environments/#env-file) explicitly. Keep plaintext credential files out of version control; see [secrets](https://mise.jdx.dev/environments/secrets/) for encrypted storage.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)