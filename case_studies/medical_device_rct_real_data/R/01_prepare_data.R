message("[01] Downloading and validating the real patient-level dataset")

if (file.exists(RAW_CSV)) unlink(RAW_CSV)
download.file(SOURCE_URL, RAW_CSV, mode = "wb", quiet = TRUE, method = "libcurl")
if (!file.exists(RAW_CSV) || file.info(RAW_CSV)$size <= 0) {
  stop("Dataset download failed or produced an empty file")
}

dat <- read.csv(RAW_CSV, na.strings = c("", "NA"), check.names = FALSE)

required <- c(
  "rownames", "age", "gender", "asa", "BMI", "Mallampati", "Randomization",
  "attempt1_time", "attempt1_S_F", "attempt2_time", "attempt2_assigned_method",
  "attempt2_S_F", "attempt3_time", "attempt3_assigned_method", "attempt3_S_F",
  "attempts", "failures", "total_intubation_time", "intubation_overall_S_F",
  "bleeding", "ease", "sore_throat", "view"
)
missing_cols <- setdiff(required, names(dat))
if (length(missing_cols) > 0) {
  stop("Required source columns missing: ", paste(missing_cols, collapse = ", "))
}

names(dat)[names(dat) == "rownames"] <- "patient_id"
dat$patient_id <- as.integer(dat$patient_id)
dat$device <- factor(dat$Randomization, levels = c(0, 1), labels = unname(DEVICE_LABELS))
dat$sore_throat_any <- ifelse(is.na(dat$sore_throat), NA_integer_, as.integer(dat$sore_throat > 0))
dat$repeat_attempt <- as.integer(dat$attempts > 1)
dat$asa_3_4 <- as.integer(dat$asa >= 3)
dat$mallampati_3_4 <- ifelse(is.na(dat$Mallampati), NA_integer_, as.integer(dat$Mallampati >= 3))
dat$female <- as.integer(dat$gender == 0)

qc_rows <- list()
add_qc <- function(check_id, domain, status, n_affected, detail) {
  qc_rows[[length(qc_rows) + 1L]] <<- data.frame(
    check_id = check_id,
    domain = domain,
    status = status,
    n_affected = as.integer(n_affected),
    detail = detail,
    stringsAsFactors = FALSE
  )
}

add_qc(
  "Q01", "shape", ifelse(nrow(dat) == 99, "PASS", "FAIL"), abs(nrow(dat) - 99),
  paste0("Expected 99 rows from the public teaching release; observed ", nrow(dat), ".")
)
add_qc(
  "Q02", "identifier", ifelse(!anyDuplicated(dat$patient_id), "PASS", "FAIL"),
  sum(duplicated(dat$patient_id)), "Patient identifiers must be unique."
)
invalid_random <- sum(!is.na(dat$Randomization) & !dat$Randomization %in% c(0, 1))
add_qc("Q03", "randomization", ifelse(invalid_random == 0, "PASS", "FAIL"), invalid_random,
       "Randomization must be coded 0=Macintosh #4 or 1=Pentax AWS video.")

arm_counts <- table(dat$Randomization, useNA = "ifany")
expected_arms <- identical(as.integer(arm_counts[c("0", "1")]), c(49L, 50L))
add_qc(
  "Q04", "randomization", ifelse(expected_arms, "PASS", "REVIEW"), 0,
  paste0("Observed randomized-device counts: Macintosh #4=", sum(dat$Randomization == 0, na.rm = TRUE),
         "; Pentax AWS video=", sum(dat$Randomization == 1, na.rm = TRUE), ".")
)

binary_vars <- c("attempt1_S_F", "intubation_overall_S_F", "bleeding")
for (v in binary_vars) {
  bad <- sum(!is.na(dat[[v]]) & !dat[[v]] %in% c(0, 1))
  add_qc(paste0("Q_BIN_", v), "range", ifelse(bad == 0, "PASS", "FAIL"), bad,
         paste0(v, " must be binary 0/1 when observed."))
}

range_checks <- list(
  age = c(20, 77),
  asa = c(2, 4),
  BMI = c(31, 61),
  Mallampati = c(1, 4),
  attempts = c(1, 3),
  failures = c(0, 2),
  total_intubation_time = c(9, 100),
  ease = c(0, 100),
  sore_throat = c(0, 3),
  view = c(0, 1)
)
for (v in names(range_checks)) {
  lo <- range_checks[[v]][1]
  hi <- range_checks[[v]][2]
  bad <- sum(!is.na(dat[[v]]) & (dat[[v]] < lo | dat[[v]] > hi))
  add_qc(paste0("Q_RANGE_", v), "range", ifelse(bad == 0, "PASS", "REVIEW"), bad,
         paste0(v, " checked against documented range [", lo, ", ", hi, "]."))
}

# Structural missingness: later-attempt fields should be absent when that attempt was not needed.
q_attempt2_unexpected_present <- sum(dat$attempts == 1 & !is.na(dat$attempt2_time))
q_attempt2_unexpected_missing <- sum(dat$attempts >= 2 & is.na(dat$attempt2_time))
add_qc(
  "Q05", "structural_missingness",
  ifelse(q_attempt2_unexpected_present + q_attempt2_unexpected_missing == 0, "PASS", "REVIEW"),
  q_attempt2_unexpected_present + q_attempt2_unexpected_missing,
  "Attempt-2 time is expected to be missing when only one attempt was required, and observed when >=2 attempts occurred."
)
q_attempt3_unexpected_present <- sum(dat$attempts < 3 & !is.na(dat$attempt3_time))
q_attempt3_unexpected_missing <- sum(dat$attempts >= 3 & is.na(dat$attempt3_time))
add_qc(
  "Q06", "structural_missingness",
  ifelse(q_attempt3_unexpected_present + q_attempt3_unexpected_missing == 0, "PASS", "REVIEW"),
  q_attempt3_unexpected_present + q_attempt3_unexpected_missing,
  "Attempt-3 time is expected to be missing unless a third attempt occurred."
)

unexpected_missing_vars <- c(
  "age", "gender", "asa", "BMI", "Mallampati", "Randomization", "attempt1_time",
  "attempt1_S_F", "attempts", "failures", "total_intubation_time",
  "intubation_overall_S_F", "bleeding", "ease", "sore_throat", "view"
)
missingness <- data.frame(
  variable = unexpected_missing_vars,
  n_missing = vapply(unexpected_missing_vars, function(v) sum(is.na(dat[[v]])), integer(1)),
  n_total = nrow(dat),
  stringsAsFactors = FALSE
)
missingness$pct_missing <- missingness$n_missing / missingness$n_total
write_csv(missingness, file.path(DIR_OUTPUT, "missingness.csv"))

n_nonzero_missing <- sum(missingness$n_missing > 0)
add_qc(
  "Q07", "unexpected_missingness", ifelse(n_nonzero_missing == 0, "PASS", "REVIEW"),
  sum(missingness$n_missing),
  paste0(n_nonzero_missing, " core variables contain at least one missing value; analysis uses explicit available-case denominators.")
)

# Do not infer a correction. Surface time inconsistencies to a reviewer.
time_issue <- which(
  !is.na(dat$attempt1_time) & !is.na(dat$total_intubation_time) &
    dat$attempt1_time > dat$total_intubation_time
)
add_qc(
  "Q08", "source_definition", ifelse(length(time_issue) == 0, "PASS", "REVIEW"), length(time_issue),
  if (length(time_issue) == 0) {
    "No first-attempt time exceeds total intubation time."
  } else {
    paste0("Patient ID(s) ", paste(dat$patient_id[time_issue], collapse = ", "),
           " have first-attempt time greater than supplied total intubation time. Source values are retained; no silent repair is made.")
  }
)

# The public data dictionary's verbal label for Cormack-Lehane grades is internally
# difficult to reconcile with the usual clinical ordering. Keep raw code only.
add_qc(
  "Q09", "source_definition", "REVIEW", nrow(dat),
  "The source dictionary describes view=0 as 'not good' for grades 1/2 and view=1 as 'good' for grades 3/4. The raw code is retained but excluded from clinically labelled inference pending source clarification."
)

qc <- do.call(rbind, qc_rows)
write_csv(qc, file.path(DIR_OUTPUT, "qc_findings.csv"))

provenance <- data.frame(
  item = c("source_url", "source_documentation", "original_study_doi", "tshs_use_statement", "retrieved_utc", "rows", "columns_after_derivation", "raw_file_md5"),
  value = c(
    SOURCE_URL,
    SOURCE_DOC,
    SOURCE_STUDY_DOI,
    TSHS_URL,
    format(Sys.time(), tz = "UTC", usetz = TRUE),
    as.character(nrow(dat)),
    as.character(ncol(dat)),
    unname(tools::md5sum(RAW_CSV))
  ),
  stringsAsFactors = FALSE
)
write_csv(provenance, file.path(DIR_OUTPUT, "data_provenance.csv"))

saveRDS(dat, ANALYSIS_RDS)
message("[01] Prepared ", nrow(dat), " patients; QC rows: ", nrow(qc))
