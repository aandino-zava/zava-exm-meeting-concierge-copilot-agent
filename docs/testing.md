# Testing and verification

## 1. What is checked automatically

The [Meeting Concierge workflow](https://github.com/aandino-zava/zava-exm-meeting-concierge-copilot-agent/actions/workflows/meeting-concierge.yml) runs on pull requests and changes to main. Review the result for the source commit you intend to use.

| Check | What it establishes |
| --- | --- |
| Scheduling simulations | The workflow action definitions follow the fixed protection, scheduling, failure-handling, and notification rules against simulated services |
| Package checks | Required connections and settings are included, no lab defaults are embedded, both flows are packaged off, and the distributable matches the current definitions |
| Import-script safeguards | Invalid settings, invalid target URLs, and checksum mismatches stop before tenant access; deployment uses an explicit target and checked package |
| Post-import verification tests | The verification script accepts complete components and rejects enabled flows, missing configuration/connections, incorrect tool bindings, and mismatched internal revisions |
| Source validation | File formats, local documentation links, current package/source fingerprints, credential patterns, and the single agent tool pass validation |
| Dev export preparation | Installation values are removed, packaged flows are off, Dev edits are preserved, and unsafe or incompatible exports are rejected |

The build saves the solution ZIP and checksum as a downloadable artifact. An explicitly requested deployment uses that same artifact. After import, the deployment job checks the exported target components and inactive flow states.

Simulations use an in-memory calendar and policy service. Package and structural checks do not establish that connector permissions, agent publication, or calendar operations work in a tenant.

## 2. What has been verified in a live environment

The following behaviors were observed in **Zava PP Lab Dev**:

| Scenario | Observed behavior |
| --- | --- |
| No calendar conflict | NoConflict; no calendar change or notification |
| Ordinary meeting conflicts with a protected board meeting | Ordinary meeting moved with its duration preserved; the board meeting stayed unchanged; Resolved; no notification |
| Two protected board meetings conflict | Both stayed unchanged; NeedsHelp; one assistant notification submitted |
| Working-hours lookup | Outlook working hours and Eastern time zone were read and used when selecting replacement times |

These observations predate the portable tenant configuration and do not prove deployment into another tenant or safe handling of simultaneous requests. A successful email action and Sent Items entry establish submission to Outlook, not recipient delivery.

## 3. What remains unverified

- Federated GitHub deployment and complete calendar acceptance in a receiving tenant.
- Target-specific connection permissions, rule visibility, agent authentication/publication, and service licensing until checked during installation.
- Live calendar behavior after the portable configuration changes.
- Competing automatic/direct requests, duplicate requests, and an external booking arriving after the final destination read. A durable mailbox lock and request ledger are not implemented.

The supported scope is one connected account's primary calendar and the approved board-protection rule. Recurring and all-day meetings require manual review. Multi-executive operation and production readiness are outside the demonstrated scope.

Record completed target-environment checks in [the installation acceptance record](../deployment/acceptance.md). Update this summary when new verification changes what can be claimed; do not mark expected behavior as an observed result.

## 4. How to repeat the checks

### Package and scheduling checks

Open the [Meeting Concierge workflow](https://github.com/aandino-zava/zava-exm-meeting-concierge-copilot-agent/actions/workflows/meeting-concierge.yml) and review **Build and check** for the source commit you intend to use. It runs the automated checks listed above and saves the checked package.

Maintainers can repeat these checks locally using [the local check instructions](../scripts/README.md#run-local-checks). That guide lists the required tools, commands, and how to check a newly built package. Local checks do not require tenant credentials.

All checks must pass before using a package.

### Deployment and live calendar acceptance

Follow [the deployment guide](deployment.md), then run its [calendar acceptance scenarios](deployment.md#test-the-installed-solution) using temporary events without attendees. Check actual Outlook times, the resolver's returned result, and notification actions. Do not rely solely on a green parent flow or successful package build.

Complete [the acceptance record](../deployment/acceptance.md) with the package checksum, source commit, target environment, results, and relevant evidence. Stop processing and remove temporary events after testing. The same acceptance steps apply to GitHub Actions deployment and manual import.
