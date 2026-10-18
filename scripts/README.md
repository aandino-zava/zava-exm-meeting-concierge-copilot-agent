# Build and deployment scripts

[GitHub Actions](../.github/workflows/meeting-concierge.yml) is the main build and deployment path. Follow [the setup guide](../docs/deployment.md) to authorize the receiving tenant and configure its GitHub environment. [Manual installation](../docs/manual-install.md) is available for downloaded packages.

## Run local checks

Use Python 3.12, PowerShell, and an official Power Platform CLI. The workflow pins its CLI and Python dependencies. Local checks and packaging do not require target sign-in.

```powershell
python -m pip install -r scripts/requirements.txt
python scripts/validate.py
python scripts/test_resolver.py
python scripts/test_prepare_dev_export.py
./scripts/pack-solution.ps1
python scripts/test_deployment.py
python scripts/test_verify_import.py
./scripts/test-import.ps1
```

Pack writes `build/ZavaExMMeetingConcierge.zip` and `build/SHA256SUMS.txt`. Set `CONCIERGE_PACKAGE_PATH` to a built ZIP when running `test_deployment.py` to check that artifact; otherwise it checks the committed download. The scheduling interpreter uses simulated services. Import-script tests use fake PAC and do not contact a tenant.

## Deployment helpers

`import-solution.ps1` validates settings and package hash before calling PAC with an explicit target URL. `-ValidateOnly` performs the checks without tenant access. Without an override it uses the committed package/provenance; `-PackagePath` and `-ChecksumFile` together select a checked workflow artifact. It does not create connections, seed rules, publish the agent, or enable flows.

`verify-import.py --folder <unpacked-target-export>` checks imported component presence, internal solution identity/revision, the one Gatekeeper tool, connection declarations, configuration definitions, and off flow states. It does not exercise calendar services or prove permissions. The pipeline uses a temporary target export for this check and does not upload it.

## Refresh the downloadable package

After reviewing source changes and updating the internal platform revision when needed:

```powershell
./scripts/pack-solution.ps1 -OutputPath ./solution/exports/ZavaExMMeetingConcierge.zip
python scripts/record-provenance.py --pac-version '<actual CLI version>'
python scripts/validate.py
```

Product and download names stay stable. Internal revision numbers and Git commit IDs remain technical traceability data. Provenance records a repository build; it does not imply a live export or successful deployment.

## Review live changes

Use [Pull from Dev](../docs/pull-from-dev.md) for the manual GitHub workflow. It prepares the export, rebuilds the package and provenance, checks the result, and opens a review pull request.

For local inspection, `export-solution.ps1 -EnvironmentUrl <source-url>` stages an authenticated live ZIP and unpacked source under `build/live-export/`. It does not overwrite portable source automatically. `prepare-dev-export.py --folder <staged-source>` removes installation values and sets exported flow state off. Add `--apply` only when you intend to replace `solution/unpacked` in your checkout. It preserves Dev logic and rejects unsupported hard-coded installation values. Review and test before rebuilding the download.

`record-provenance.py --source dev-export --source-run-url <workflow-url>` identifies a portable build originating in a normalized Dev export. The default remains a repository-authored build. Neither establishes runtime acceptance.
