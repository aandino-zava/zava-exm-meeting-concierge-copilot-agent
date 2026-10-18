# Pull Dev changes into GitHub

Run **Pull from Dev** when you want to bring saved changes from your Dev solution back into this repository. It exports the solution, prepares portable source, rebuilds the deployable ZIP, runs checks, and opens a pull request. Review and merge that pull request to update main and its downloadable package.

The workflow does not import into Dev, publish the agent, turn flows on or off in Dev, or deploy anywhere else. It changes flow state only in the exported files, so the package still ships with processing off.

## 1. Set up access once

Use a GitHub environment for the **Dev source**, for example `dev`. An environment used to deploy into a different tenant is not automatically authorized to export from Dev.

1. Follow [the deployment identity setup](deployment.md#authorize-github-in-the-receiving-tenant) for your Dev tenant: Entra application, Dataverse application user, a role that can export this solution, and GitHub environment federation. You can reuse an existing authorized application and GitHub environment if they already point to this Dev environment. No new runtime account connections or deployment settings JSON are needed just to export.
2. In repository **Settings > Environments > dev**, restrict deployment branches to **main**. Add a required reviewer if supported by your GitHub plan.
3. Set these GitHub **environment variables**:

   | Name | Value |
   | --- | --- |
   | `ENVIRONMENT_URL` | Your intended Dev Dataverse organization URL |
   | `TENANT_ID` | Dev tenant Directory ID |
   | `CLIENT_ID` | Application ID authorized to export from Dev |
   | `DEV_EXPORT_ENABLED` | `true` |

4. The Entra federated credential must match the repository and exact GitHub environment name, for example `repo:OWNER/REPOSITORY:environment:dev`, with issuer `https://token.actions.githubusercontent.com` and audience `api://AzureADTokenExchange`.
5. Under repository **Settings > Actions > General > Workflow permissions**, enable **Allow GitHub Actions to create and approve pull requests**. The workflow requests write permissions for contents and pull requests. It creates a review request; it does not approve or merge one. Organization policy must allow these permissions.

Set `DEV_EXPORT_ENABLED=true` only on environments you intend to use as Dev sources. The workflow also requires main and serializes with deployment runs using the same GitHub environment name.

## 2. Finish your changes in Dev

1. Save the agent and flows. Publish Dataverse table and column changes that need publication. Pause editing while the export runs so it captures a consistent set of saved changes. The workflow does not publish all environment customizations for you.
2. Make changes inside the **Zava ExM Meeting Concierge** solution. Add new dependencies to that solution, and resolve missing dependencies before exporting. Components outside it are not automatically discovered and added.
3. Keep mailbox, Calendar ID, and assistant recipient in configuration. Dev must include the current portable settings and flows that use them. An older lab installation with hard-coded values needs reconciliation with the current package before this workflow can accept it. Preserve existing Dev changes before importing any replacement package.
4. Keep the Gatekeeper behavior unless you deliberately intend to change it. Changed business rules, tools, or connectors can require corresponding tests, setup templates, and documentation changes; an export cannot write those for you.

Agent changes must be saved to the solution. Publishing the live conversational agent is a separate runtime operation and is not performed by this workflow.

## 3. Run Pull from Dev

1. Open GitHub **Actions > Pull from Dev > Run workflow**.
2. Choose branch **main** and the GitHub environment configured for Dev, then run it.
3. Approve the environment request if you configured one. Wait for **Export check and propose changes** to finish.
4. Open the pull request linked in the workflow summary. It contains the source diff, rebuilt `ZavaExMMeetingConcierge.zip`, checksum, and build provenance. The checked package is also downloadable from the run's artifacts.

Current environment values, configuration defaults, and connection instance IDs are removed from the portable export. Packaged flows are set off. The workflow rejects remaining email literals or tenant URLs, and the existing credential-pattern checks must pass before any branch, pull request, or package artifact is published. The raw Dev export is not uploaded.

If portable source is unchanged, the summary says so and no pull request or replacement package is created. If a check fails, no change is made to main. Read the failed step and correct the issue before rerunning.

## 4. Review and merge

Review **Files changed**, especially agent instructions, flow behavior, table changes, and dependencies. Run calendar tests in Dev for behavior you changed. Check that no private values were included. Update documentation or deployment settings when required, then merge the pull request.

All source, scheduling, package, and deployment-script checks run within Pull from Dev before the pull request is created. If GitHub separately requests approval for a bot-created pull request's checks, approve that run. Do not assume a bot-created push will trigger another workflow. The export run linked in the pull request provides its completed checks.

After merging, main contains the updated deployable package. Use the existing **Meeting Concierge** deployment workflow when you want to install it elsewhere. Merging does not deploy the changes or prove receiving-tenant acceptance.

## What travels and what does not

Included solution components can carry saved agent definitions, flows, Dataverse tables and columns, and dependencies. The workflow preserves the Power Apps setting that disables AI form-fill suggestions for Rule Text.

It does not synchronize rule table rows, other business data, account credentials, connection ownership/sharing, calendar events, run history, or target-specific authentication and publication. Keep required rule data in the reviewed setup process. The existing single-agent, three-connection, three-setting package checks remain in force; structural changes outside that design need an accompanying repository change rather than silently weakening the checks.

## If a step fails

| Failed step | What to check |
| --- | --- |
| Check Dev setup | Select main; verify the Dev URL and IDs; set `DEV_EXPORT_ENABLED=true` on that GitHub environment |
| Sign in to Dev | Exact federation subject, tenant/application IDs, Dataverse application user, and export permissions |
| Export Dev solution | Correct solution identity, application access, and included dependencies |
| Prepare portable source | Missing portable configuration, hard-coded recipients, tenant URLs, or unresolved dependencies; the workflow does not guess replacements |
| Package or tests | Review the changed behavior, tools, connections, and settings; make the intended matching repository/test changes |
| Open review pull request | Allow Actions pull requests and contents writes; if the branch was saved, open the pull request manually from `dev-export/...` |

This workflow has local preparation and package checks. A live Dev export through GitHub federation still needs its first authorized run; no successful live synchronization is implied by those local checks.
