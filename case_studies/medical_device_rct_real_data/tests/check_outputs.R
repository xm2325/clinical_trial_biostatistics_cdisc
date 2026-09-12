args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) != 1) stop("check_outputs.R must be executed with Rscript")
this_file <- sub("^--file=", "", file_arg)
case_dir <- normalizePath(file.path(dirname(this_file), ".."), mustWork = TRUE)
setwd(case_dir)

required_files <- c(
  "outputs/data_provenance.csv",
  "outputs/missingness.csv",
  "outputs/qc_findings.csv",
  "outputs/baseline_table.csv",
  "outputs/binary_outcomes.csv",
  "outputs/continuous_outcomes.csv",
  "outputs/sensitivity_analysis.csv",
  "outputs/analysis_summary.md",
  "outputs/stakeholder_brief.md",
  "outputs/day5_handoff.md",
  "outputs/figures/first_attempt_success.png",
  "outputs/figures/total_intubation_time.png",
  "outputs/figures/missingness.png",
  "outputs/figures/study_to_decision.png"
)
missing_files <- required_files[!file.exists(required_files)]
if (length(missing_files) > 0) stop("Missing generated outputs: ", paste(missing_files, collapse = ", "))

qc <- read.csv("outputs/qc_findings.csv", check.names = FALSE)
if (any(qc$status == "FAIL")) {
  stop("QC contains FAIL rows: ", paste(qc$check_id[qc$status == "FAIL"], collapse = ", "))
}

prov <- read.csv("outputs/data_provenance.csv", check.names = FALSE)
get_prov <- function(key) prov$value[prov$item == key]
if (as.integer(get_prov("rows")) != 99L) stop("Expected 99 rows in teaching release")
if (!nzchar(get_prov("raw_file_md5"))) stop("Raw-data MD5 was not recorded")

binary <- read.csv("outputs/binary_outcomes.csv", check.names = FALSE)
first <- binary[binary$variable == "attempt1_S_F", , drop = FALSE]
if (nrow(first) != 1L) stop("Expected one first-attempt outcome row")
if (!identical(as.integer(first$aws_n), 50L)) stop("Expected 50 AWS records")
if (!identical(as.integer(first$mac_n), 49L)) stop("Expected 49 Macintosh records")
if (!identical(as.integer(first$aws_events), 43L)) stop("Unexpected AWS first-attempt-success count")
if (!identical(as.integer(first$mac_events), 45L)) stop("Unexpected Macintosh first-attempt-success count")

ov <- binary[binary$variable == "intubation_overall_S_F", , drop = FALSE]
if (!identical(as.integer(ov$aws_events), 46L)) stop("Unexpected AWS overall-success count")
if (!identical(as.integer(ov$mac_events), 49L)) stop("Unexpected Macintosh overall-success count")

miss <- read.csv("outputs/missingness.csv", check.names = FALSE)
if (sum(miss$n_missing) != 4L) stop("Expected four missing core-variable cells in the public teaching release")
if (sum(miss$n_missing > 0) != 3L) stop("Expected three core variables with missing values")

q08 <- qc[qc$check_id == "Q08", , drop = FALSE]
q09 <- qc[qc$check_id == "Q09", , drop = FALSE]
if (nrow(q08) != 1L || q08$status != "REVIEW" || q08$n_affected != 1L) {
  stop("Expected one source-timing row to remain a REVIEW item")
}
if (nrow(q09) != 1L || q09$status != "REVIEW") {
  stop("Expected source view-code definition to remain a REVIEW item")
}

continuous <- read.csv("outputs/continuous_outcomes.csv", check.names = FALSE)
time_row <- continuous[continuous$variable == "total_intubation_time", , drop = FALSE]
if (nrow(time_row) != 1L || !is.finite(time_row$median_difference_aws_minus_mac)) {
  stop("Total-time estimate missing")
}

summary_text <- paste(readLines("outputs/analysis_summary.md", warn = FALSE), collapse = "\n")
if (!grepl("not an exact reproduction", summary_text, fixed = TRUE)) {
  stop("Analysis summary is missing the teaching-release evidence boundary")
}

day5_text <- paste(readLines("outputs/day5_handoff.md", warn = FALSE), collapse = "\n")
if (!grepl("Decision message for the study team", day5_text, fixed = TRUE)) {
  stop("Day-5 handoff is missing the decision section")
}
if (!grepl("not an exact reproduction", day5_text, fixed = TRUE)) {
  stop("Day-5 handoff is missing the evidence boundary")
}

figure_sizes <- file.info(c(
  "outputs/figures/first_attempt_success.png",
  "outputs/figures/total_intubation_time.png",
  "outputs/figures/missingness.png",
  "outputs/figures/study_to_decision.png"
))$size
if (any(!is.finite(figure_sizes)) || any(figure_sizes < 1000L)) {
  stop("One or more generated figures are unexpectedly small")
}

cat("medical-device real-data case study checks: PASS\n")
cat("QC rows:", nrow(qc), "| REVIEW:", sum(qc$status == "REVIEW"), "| FAIL: 0\n")
cat("First-attempt success: AWS", first$aws_events, "/", first$aws_n,
    "vs Macintosh", first$mac_events, "/", first$mac_n, "\n")
cat("Median total-time difference (AWS - Macintosh):",
    sprintf("%.2f", time_row$median_difference_aws_minus_mac), "seconds\n")
cat("Recruiter-facing one-pager and day-5 handoff outputs: READY\n")
