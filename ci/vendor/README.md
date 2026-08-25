# SAS ODA client encryption bundle

This directory must never contain the raw SAS JAR files or an unencrypted ZIP.

The automated SAS OnDemand for Academics workflow expects exactly one encrypted
bundle at:

`ci/vendor/SAS-ODA-JarFiles.zip.gpg`

The bundle is the user-obtained SAS ODA client encryption package containing:

- `sas.rutil.jar`
- `sas.rutil.nls.jar`
- `sastpj.rutil.jar`

The repository stores only GPG ciphertext. The symmetric passphrase is held in
the GitHub Actions repository secret `SAS_ODA_JARS_PASSPHRASE` and must never be
committed. During a run, GitHub decrypts the bundle only on the ephemeral runner,
verifies the three pinned SHA256 identities, installs them into the temporary
SASPy runtime, runs the ODA validation, and then destroys the runner.

Pinned SHA256 values are enforced by
`scripts/install_sas_oda_encryption_jars.py`.
