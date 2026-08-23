options(stringsAsFactors = FALSE)

required_packages <- c("jsonlite", "survival")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

suppressPackageStartupMessages(library(survival))

out_dir <- "outputs"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

spec_path <- file.path("spec", "tte_retention.json")
input_path <- file.path(out_dir, "adtte_retention_style.csv")
if (!file.exists(spec_path)) stop("Missing TTE specification: ", spec_path)
if (!file.exists(input_path)) stop("Missing ADTTE-style retention input: ", input_path)

spec <- jsonlite::fromJSON(spec_path, simplifyVector = TRUE)
d <- read.csv(input_path, check.names = FALSE, na.strings = c("", "NA"))

required_cols <- c(
  "STUDYID", "USUBJID", "TRT01P", "TRT01A", "ANLTRT", "ANLTRTSRC", "TRTDIFFL",
  "PARAMCD", "AVAL", "CNSR", "EVNTDESC", "ANL01FL"
)
missing_cols <- setdiff(required_cols, names(d))
if (length(missing_cols) > 0) stop("ADTTE-style input missing columns: ", paste(missing_cols, collapse = ", "))

expected_arms <- as.character(spec$population$treatment_arms)
expected_paramcd <- as.character(spec$parameter$PARAMCD)
analysis_trt_var <- as.character(spec$population$analysis_treatment_variable)
km_times <- as.numeric(spec$analysis$km_timepoints_days)
alpha <- as.numeric(spec$analysis$alpha)
cox_ties <- tolower(as.character(spec$analysis$cox_ties))

if (!identical(as.character(spec$version), "0.17.0")) stop("TTE specification version must be 0.17.0")
if (!identical(analysis_trt_var, "TRT01P")) stop("v0.17 randomized retention analysis must use planned treatment TRT01P")
if (length(expected_arms) != 3) stop("TTE specification must contain exactly three treatment arms")
if (length(km_times) < 1 || any(!is.finite(km_times)) || any(km_times <= 0)) stop("Invalid KM timepoints")
if (!is.finite(alpha) || alpha <= 0 || alpha >= 1) stop("Invalid alpha")
if (!identical(cox_ties, "efron")) stop("v0.17 Cox tie method must be efron")

d <- d[
  d$PARAMCD == expected_paramcd &
    d$ANL01FL == "Y" &
    d$ANLTRT %in% expected_arms,
  , drop = FALSE
]
d$AVAL <- suppressWarnings(as.numeric(d$AVAL))
d$CNSR <- suppressWarnings(as.integer(d$CNSR))
d$ANLTRT <- factor(d$ANLTRT, levels = expected_arms)
d$status <- as.integer(d$CNSR == 0L)
d <- d[order(d$ANLTRT, d$USUBJID), , drop = FALSE]
row.names(d) <- NULL

add_check_factory <- function() {
  checks <- list()
  function(name = NULL, passed = NULL, detail = NULL, required = TRUE, get = FALSE) {
    if (get) return(do.call(rbind, checks))
    checks[[length(checks) + 1]] <<- data.frame(
      check = as.character(name),
      passed = isTRUE(passed),
      required = isTRUE(required),
      detail = as.character(detail),
      stringsAsFactors = FALSE
    )
    invisible(NULL)
  }
}
add_check <- add_check_factory()

planned_actual_diff <- as.character(d$TRT01P) != as.character(d$TRT01A)
add_check(
  "TTE analysis has all three randomized treatment arms",
  identical(levels(droplevels(d$ANLTRT)), expected_arms),
  paste(levels(droplevels(d$ANLTRT)), collapse = ", ")
)
add_check(
  "TTE analysis has one row per subject",
  !anyDuplicated(d$USUBJID),
  paste0("duplicate subjects=", sum(duplicated(d$USUBJID)))
)
add_check(
  "TTE analysis treatment equals planned randomized assignment",
  all(as.character(d$ANLTRT) == as.character(d$TRT01P)),
  paste0("mismatches=", sum(as.character(d$ANLTRT) != as.character(d$TRT01P)))
)
add_check(
  "TTE planned-versus-actual treatment audit flag is exact",
  all((d$TRTDIFFL == "Y") == planned_actual_diff),
  paste0("planned/actual differences=", sum(planned_actual_diff))
)
add_check("TTE AVAL is finite and positive", all(is.finite(d$AVAL) & d$AVAL > 0), paste0("rows=", nrow(d)))
add_check("TTE CNSR uses only 0/1", all(d$CNSR %in% c(0L, 1L)), paste0("codes=", paste(sort(unique(d$CNSR)), collapse = ",")))
add_check("TTE contains events and censored observations", any(d$status == 1L) && any(d$status == 0L), paste0("events=", sum(d$status == 1L), "; censored=", sum(d$status == 0L)))

km_fit <- survfit(Surv(AVAL, status) ~ ANLTRT, data = d, conf.type = "log-log")
km_sum <- summary(km_fit, times = km_times, extend = TRUE)
km <- data.frame(
  ANLTRT = sub("^ANLTRT=", "", as.character(km_sum$strata)),
  time_days = as.numeric(km_sum$time),
  n_risk = as.integer(km_sum$n.risk),
  retention_probability = as.numeric(km_sum$surv),
  standard_error = as.numeric(km_sum$std.err),
  ci95_lower = as.numeric(km_sum$lower),
  ci95_upper = as.numeric(km_sum$upper),
  stringsAsFactors = FALSE
)
km$ANLTRT <- factor(km$ANLTRT, levels = expected_arms)
km <- km[order(km$ANLTRT, km$time_days), , drop = FALSE]
km$ANLTRT <- as.character(km$ANLTRT)
row.names(km) <- NULL
write.csv(km, file.path(out_dir, "table24_retention_km.csv"), row.names = FALSE, na = "")

km_table <- summary(km_fit)$table
if (is.null(dim(km_table))) km_table <- matrix(km_table, nrow = 1)
median_rows <- data.frame(
  ANLTRT = sub("^ANLTRT=", "", rownames(km_table)),
  subjects = as.integer(km_table[, "records"]),
  events = as.integer(km_table[, "events"]),
  median_days = as.numeric(km_table[, "median"]),
  median_ci95_lower = as.numeric(km_table[, "0.95LCL"]),
  median_ci95_upper = as.numeric(km_table[, "0.95UCL"]),
  stringsAsFactors = FALSE
)
median_rows$ANLTRT <- factor(median_rows$ANLTRT, levels = expected_arms)
median_rows <- median_rows[order(median_rows$ANLTRT), , drop = FALSE]
median_rows$ANLTRT <- as.character(median_rows$ANLTRT)
row.names(median_rows) <- NULL
write.csv(median_rows, file.path(out_dir, "retention_km_medians.csv"), row.names = FALSE, na = "")

active_arms <- expected_arms[expected_arms != "Placebo"]
pairwise_rows <- lapply(active_arms, function(active_arm) {
  dd <- d[as.character(d$ANLTRT) %in% c("Placebo", active_arm), , drop = FALSE]
  dd$ANLTRT <- relevel(droplevels(dd$ANLTRT), ref = "Placebo")

  logrank <- survdiff(Surv(AVAL, status) ~ ANLTRT, data = dd, rho = 0)
  logrank_chisq <- as.numeric(logrank$chisq)
  logrank_p <- stats::pchisq(logrank_chisq, df = 1, lower.tail = FALSE)

  cox_fit <- coxph(
    Surv(AVAL, status) ~ ANLTRT,
    data = dd,
    ties = cox_ties,
    x = TRUE,
    y = TRUE,
    model = TRUE
  )
  cox_summary <- summary(cox_fit)
  coef_row <- cox_summary$coefficients[1, , drop = TRUE]
  ci_row <- cox_summary$conf.int[1, , drop = TRUE]
  ph <- cox.zph(cox_fit, transform = "km")
  ph_p <- as.numeric(ph$table[1, "p"])

  data.frame(
    comparison = paste(active_arm, "vs Placebo"),
    active_arm = active_arm,
    reference_arm = "Placebo",
    analysis_treatment = "planned randomized assignment (TRT01P)",
    hazard_ratio = as.numeric(ci_row["exp(coef)"]),
    ci95_lower = as.numeric(ci_row["lower .95"]),
    ci95_upper = as.numeric(ci_row["upper .95"]),
    cox_p_value = as.numeric(coef_row["Pr(>|z|)"]),
    logrank_chisq = logrank_chisq,
    logrank_p_value = logrank_p,
    ph_test_p_value = ph_p,
    ph_diagnostic = ifelse(ph_p < alpha, "POTENTIAL_NON_PROPORTIONALITY", "NO_SIGNAL_AT_ALPHA"),
    interpretation = "HR > 1 indicates a higher study-discontinuation hazard than placebo; exploratory only",
    stringsAsFactors = FALSE
  )
})
pairwise <- do.call(rbind, pairwise_rows)
row.names(pairwise) <- NULL
write.csv(pairwise, file.path(out_dir, "table25_retention_pairwise.csv"), row.names = FALSE, na = "")

expected_km_rows <- length(expected_arms) * length(km_times)
add_check("KM table has one row per arm and requested timepoint", nrow(km) == expected_km_rows, paste0("rows=", nrow(km), "; expected=", expected_km_rows))
add_check(
  "KM probabilities and confidence limits are finite and bounded",
  all(
    is.finite(as.matrix(km[, c("retention_probability", "standard_error", "ci95_lower", "ci95_upper")])) &
      km$retention_probability >= 0 & km$retention_probability <= 1 &
      km$ci95_lower >= 0 & km$ci95_upper <= 1
  ),
  paste0("rows=", nrow(km))
)
monotone_ok <- all(vapply(split(km, km$ANLTRT), function(z) all(diff(z$retention_probability) <= 1e-12), logical(1)))
add_check("KM retention probabilities are non-increasing over time", monotone_ok, paste0("arms=", length(unique(km$ANLTRT))))
add_check("Pairwise table has exactly two active-versus-placebo comparisons", nrow(pairwise) == 2, paste0("rows=", nrow(pairwise)))
add_check(
  "Cox hazard ratios and confidence intervals are finite and positive",
  all(
    is.finite(as.matrix(pairwise[, c("hazard_ratio", "ci95_lower", "ci95_upper")])) &
      pairwise$hazard_ratio > 0 & pairwise$ci95_lower > 0 & pairwise$ci95_upper > 0 &
      pairwise$ci95_lower <= pairwise$hazard_ratio & pairwise$hazard_ratio <= pairwise$ci95_upper
  ),
  paste0("rows=", nrow(pairwise))
)
add_check(
  "Cox and log-rank p-values are valid",
  all(
    is.finite(as.matrix(pairwise[, c("cox_p_value", "logrank_p_value")])) &
      pairwise$cox_p_value >= 0 & pairwise$cox_p_value <= 1 &
      pairwise$logrank_p_value >= 0 & pairwise$logrank_p_value <= 1
  ),
  paste0("rows=", nrow(pairwise))
)
add_check(
  "Proportional-hazards diagnostic p-values are available",
  all(is.finite(pairwise$ph_test_p_value) & pairwise$ph_test_p_value >= 0 & pairwise$ph_test_p_value <= 1),
  paste0("rows=", nrow(pairwise))
)

qc <- add_check(get = TRUE)
write.csv(qc, file.path(out_dir, "tte_retention_survival_qc.csv"), row.names = FALSE, na = "")
required <- qc[qc$required, , drop = FALSE]
all_required <- nrow(required) > 0 && all(required$passed)

arm_counts <- lapply(expected_arms, function(arm) {
  z <- d[as.character(d$ANLTRT) == arm, , drop = FALSE]
  list(subjects = nrow(z), events = sum(z$status == 1L), censored = sum(z$status == 0L))
})
names(arm_counts) <- expected_arms

median_metrics <- lapply(seq_len(nrow(median_rows)), function(i) {
  list(
    arm = median_rows$ANLTRT[i],
    median_days = if (is.finite(median_rows$median_days[i])) median_rows$median_days[i] else NA_real_,
    lower = if (is.finite(median_rows$median_ci95_lower[i])) median_rows$median_ci95_lower[i] else NA_real_,
    upper = if (is.finite(median_rows$median_ci95_upper[i])) median_rows$median_ci95_upper[i] else NA_real_
  )
})

metrics <- list(
  analysis_version = "0.17.0",
  r_version = R.version.string,
  survival_version = as.character(utils::packageVersion("survival")),
  parameter = expected_paramcd,
  analysis_treatment_variable = analysis_trt_var,
  planned_actual_mismatch_subjects = sum(planned_actual_diff),
  subjects = nrow(d),
  events = sum(d$status == 1L),
  censored = sum(d$status == 0L),
  km_timepoints_days = km_times,
  arm_counts = arm_counts,
  medians = median_metrics,
  pairwise_comparisons = nrow(pairwise),
  ph_diagnostic_signals = sum(pairwise$ph_test_p_value < alpha),
  required_checks = nrow(required),
  required_passed = sum(required$passed),
  all_required_passed = all_required
)
jsonlite::write_json(
  metrics,
  file.path(out_dir, "tte_retention_survival_metrics.json"),
  pretty = TRUE,
  auto_unbox = TRUE,
  na = "null"
)

summary_lines <- c(
  "# Exploratory time-to-study-discontinuation analysis",
  "",
  paste0("- Analysis treatment: planned randomized assignment (`", analysis_trt_var, "`)."),
  paste0("- Planned/actual treatment differences retained for audit: ", metrics$planned_actual_mismatch_subjects, " subjects."),
  paste0("- Subjects: ", metrics$subjects, "; events: ", metrics$events, "; censored: ", metrics$censored, "."),
  paste0("- Kaplan-Meier timepoints: days ", paste(km_times, collapse = ", "), "."),
  paste0("- Required survival QC: ", metrics$required_passed, "/", metrics$required_checks, " passed."),
  paste0("- Cox proportional-hazards diagnostic signals at alpha=", alpha, ": ", metrics$ph_diagnostic_signals, "/", nrow(pairwise), "."),
  "",
  "## Pairwise active-versus-placebo comparisons",
  ""
)
for (i in seq_len(nrow(pairwise))) {
  row <- pairwise[i, ]
  summary_lines <- c(
    summary_lines,
    sprintf(
      "- %s: HR=%.4f (95%% CI %.4f to %.4f), Cox p=%.4g, log-rank p=%.4g, PH diagnostic p=%.4g (%s).",
      row$comparison, row$hazard_ratio, row$ci95_lower, row$ci95_upper,
      row$cox_p_value, row$logrank_p_value, row$ph_test_p_value, row$ph_diagnostic
    )
  )
}
summary_lines <- c(
  summary_lines,
  "",
  "Hazard ratios are exploratory retention diagnostics. A proportional-hazards diagnostic signal does not fail the pipeline; it limits interpretation of the Cox summary.",
  "This is an ADTTE-style public-data portfolio exercise, not a sponsor-approved endpoint, efficacy analysis or regulatory claim."
)
writeLines(summary_lines, file.path(out_dir, "tte_retention_survival_summary.md"))

if (!all_required) {
  failed <- required[!required$passed, "check"]
  stop("TTE retention survival QC failed: ", paste(failed, collapse = "; "))
}
