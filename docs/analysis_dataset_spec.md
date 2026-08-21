# Analysis dataset specification

This document records the main source-to-derived-variable mappings used by v0.2. It is a compact portfolio analogue of an analysis dataset specification, not a formal CDISC metadata package.

## ADSL-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID | DM | copied |
| USUBJID | DM | copied |
| AGE / SEX / RACE / COUNTRY | DM | copied |
| TRT01P | DM.ARM | copied |
| TRT01A | DM.ACTARM | copied |
| TRTSDT_DM / TRTEDT_DM | DM.RFXSTDTC / RFXENDTC | parsed to date; traceability only |
| TRTSDT | EX.EXSTDTC | minimum non-missing subject date; falls back to DM date only if EX summary is unavailable |
| TRTEDT | EX.EXENDTC | maximum non-missing subject date; falls back to DM date only if EX summary is unavailable |
| EXDURN | TRTSDT / TRTEDT | inclusive calendar-day duration |
| EXN | EX | number of subject EX records |
| EXTRTS | EX.EXTRT | sorted distinct treatment strings joined with ` | ` |
| EXDOSE_MAX | EX.EXDOSE | maximum numeric recorded dose |
| EXDOSE_MEAN | EX.EXDOSE | mean numeric recorded dose across EX records |
| RANDFL | DS.DSDECOD | `Y` if `RANDOMIZED` exists |
| SAFFL | EX | `Y` if at least one EX record exists |
| COMPLFL | DS.DSDECOD | `Y` if `COMPLETED` exists |
| EOSDECOD / EOSTERM / EOSDT | DS | last `DISPOSITION EVENT` by date / DS sequence |
| DCSFL | RANDFL / COMPLFL | `Y` if randomised and not completed |

## ADAE-style

| Variable | Source | Derivation |
|---|---|---|
| STUDYID / USUBJID / AESEQ | AE | copied key |
| AETERM / AEDECOD / AEBODSYS | AE | copied |
| AESEV / AESER / AEREL / AEOUT | AE | copied |
| TRT01A / TRTSDT / TRTEDT / SAFFL | ADSL-style | merge by STUDYID + USUBJID |
| ASTDT / AENDT | AE.AESTDTC / AE.AEENDTC | parsed dates |
| ASTDY | AE.AESTDY | numeric when supplied; otherwise relative-day derivation |
| TRTEMFL | AE + ADSL-style | `Y` when ASTDT is within `[TRTSDT, TRTEDT + 30 days]` and SAFFL=`Y` |
| RELFL | AE.AEREL | `Y` for POSSIBLE / PROBABLE / DEFINITE / RELATED |
| MODSEVFL | AE.AESEV | `Y` for MODERATE / SEVERE |
