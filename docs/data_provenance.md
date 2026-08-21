# Data provenance

Source repository: `pharmaverse/pharmaversesdtm`.

The package documentation states that some test datasets are sourced from the CDISC pilot project and others are constructed for testing. The workflow therefore describes the inputs as **public CDISC pilot-style SDTM test data** rather than making a stronger claim about every record's origin.

Domains used in v0.2:

| Domain | Role in this workflow |
|---|---|
| DM | demographics; planned/actual treatment labels; DM exposure dates retained for traceability |
| EX | observed exposure; safety population; portfolio treatment window; dose summaries |
| DS | randomisation; completion; final disposition / discontinuation reason |
| AE | adverse-event derivations and safety summaries |

The source URLs are fixed in `src/cdisc_portfolio/io.py`. Each run records SHA256 hashes for every downloaded input and generated core output in `outputs/manifest.json`.

The raw CSV files are downloaded at run time and are not committed to this repository.
