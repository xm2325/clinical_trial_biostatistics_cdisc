options(stringsAsFactors = FALSE)

required_packages <- c("jsonlite", "mmrm", "emmeans")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

suppressPackageStartupMessages({
  library(mmrm)
  library(emmeans)
})

options(mmrm.max_visits = 10)

out_dir <- "outputs"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

norm_chr <- function(x) {
  y <- as.character(x)
  y[is.na(y)] <- ""
  trimws(y)
}

add_check_factory <- function() {
  checks <- list()
  function(name = NULL, passed = NULL, detail = NULL, required = TRUE, get = FALSE) {
    if (get) return(do.call(rbind, checks))
    checks[[length(checks) + 1]] <<- data.frame(
      check = name,
      passed = isTRUE(passed),
      required = isTRUE(required),
      detail = as.character(detail),
      stringsAsFactors = FALSE
    )
    invisible(NULL)
  }
}
add_check <- add_check_factory()

input_path <- file.path(out_dir, "adqs_actot_style.csv")
if (!file.exists(input_path)) stop("Missing Python ACTOT analysis input: ", input_path)

x <- read.csv(input_path, na.strings = c("", "NA"), check.names = FALSE)
required_cols <- c("STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "CHG", "ABLFL", "EFFFL", "QSSEQ")
missing_cols <- setdiff(required_cols, names(x))
if (length(missing_cols) > 0) stop("ACTOT input missing columns: ", paste(missing_cols, collapse = ", "))

expected_arms <- c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")
expected_visits <- c("Week 8", "Week 16", "Week 24")
visit_map <- c("WEEK 8" = "Week 8", "WEEK 16" = "Week 16", "WEEK 24" = "Week 24")

x$AVISIT_U <- toupper(norm_chr(x$AVISIT))
x$ABLFL_N <- norm_chr(x$ABLFL)
x$EFFFL_N <- norm_chr(x$EFFFL)
x$TRT01A_N <- norm_chr(x$TRT01A)
x$AVAL <- suppressWarnings(as.numeric(x$AVAL))
x$BASE <- suppressWarnings(as.numeric(x$BASE))
x$CHG <- suppressWarnings(as.numeric(x$CHG))

# MMRM uses observed post-baseline values only. No LOCF rows are introduced.
d <- x[
  x$EFFFL_N == "Y" &
    x$ABLFL_N != "Y" &
    x$TRT01A_N %in% expected_arms &
    x$AVISIT_U %in% names(visit_map) &
    is.finite(x$AVAL) & is.finite(x$BASE) & is.finite(x$CHG),
  c("STUDYID", "USUBJID", "TRT01A_N", "AVISIT_U", "AVAL", "BASE", "CHG", "QSSEQ"),
  drop = FALSE
]
names(d)[names(d) == "TRT01A_N"] <- "TRT01A"
d$AVISIT <- unname(visit_map[d$AVISIT_U])
d$TRT01A <- factor(d$TRT01A, levels = expected_arms)
d$AVISIT <- factor(d$AVISIT, levels = expected_visits, ordered = TRUE)
d$USUBJID <- factor(d$USUBJID)
d$VISITN <- as.numeric(d$AVISIT)
d <- d[order(d$USUBJID, d$VISITN, d$QSSEQ), ]
row.names(d) <- NULL

add_check("MMRM analysis has all three treatment arms", identical(levels(droplevels(d$TRT01A)), expected_arms), paste(levels(droplevels(d$TRT01A)), collapse = ", "))
add_check("MMRM analysis has Week 8/16/24", identical(levels(droplevels(d$AVISIT)), expected_visits), paste(levels(droplevels(d$AVISIT)), collapse = ", "))

dup_key <- duplicated(paste(d$USUBJID, d$AVISIT, sep = "|"))
add_check("MMRM subject-visit key unique", !any(dup_key), paste0("duplicate rows=", sum(dup_key)))

chg_error <- abs(d$CHG - (d$AVAL - d$BASE))
max_chg_error <- if (length(chg_error) == 0) Inf else max(chg_error, na.rm = TRUE)
add_check("MMRM CHG equals AVAL-BASE", is.finite(max_chg_error) && max_chg_error <= 1e-12, sprintf("max absolute error=%.3g", max_chg_error))

base_range_by_subject <- tapply(d$BASE, d$USUBJID, function(z) diff(range(z, na.rm = TRUE)))
max_base_range <- max(base_range_by_subject, na.rm = TRUE)
add_check("MMRM BASE constant within subject", is.finite(max_base_range) && max_base_range <= 1e-12, sprintf("max within-subject range=%.3g", max_base_range))

visit_counts <- as.data.frame(table(d$AVISIT, d$TRT01A), stringsAsFactors = FALSE)
names(visit_counts) <- c("AVISIT", "TRT01A", "records")
write.csv(visit_counts, file.path(out_dir, "mmrm_visit_counts.csv"), row.names = FALSE)
write.csv(d, file.path(out_dir, "mmrm_analysis_dataset.csv"), row.names = FALSE, na = "")

fit_model <- function(covariance = c("US", "AR1H")) {
  covariance <- match.arg(covariance)
  if (covariance == "US") {
    formula <- CHG ~ TRT01A * AVISIT + BASE * AVISIT + us(AVISIT | USUBJID)
  } else {
    formula <- CHG ~ TRT01A * AVISIT + BASE * AVISIT + ar1h(VISITN | USUBJID)
  }
  mmrm(
    formula = formula,
    data = d,
    reml = TRUE,
    method = "Satterthwaite"
  )
}

primary_fit <- fit_model("US")
sensitivity_fit <- fit_model("AR1H")

optimizer_name <- function(fit) {
  obj <- tryCatch(mmrm::component(fit, name = "optimizer"), error = function(e) NA_character_)
  paste(as.character(obj), collapse = ";")
}

model_row <- function(fit, covariance) {
  data.frame(
    model = covariance,
    covariance = covariance,
    inference = "REML",
    df_method = "Satterthwaite",
    observations = nrow(d),
    subjects = length(unique(d$USUBJID)),
    logLik = as.numeric(logLik(fit)),
    AIC = AIC(fit),
    BIC = BIC(fit),
    optimizer = optimizer_name(fit),
    fit_returned = TRUE,
    stringsAsFactors = FALSE
  )
}
model_diagnostics <- rbind(model_row(primary_fit, "Unstructured"), model_row(sensitivity_fit, "AR1 heterogeneous"))
write.csv(model_diagnostics, file.path(out_dir, "mmrm_model_diagnostics.csv"), row.names = FALSE, na = "")

extract_emmeans <- function(fit, covariance) {
  emm <- emmeans(
    fit,
    specs = ~ TRT01A | AVISIT,
    cov.reduce = list(BASE = mean)
  )
  emm_df <- as.data.frame(confint(emm, level = 0.95))
  emm_df$covariance <- covariance

  cmp <- contrast(
    emm,
    method = list(
      "Xanomeline Low Dose vs Placebo" = c(-1, 1, 0),
      "Xanomeline High Dose vs Placebo" = c(-1, 0, 1)
    ),
    by = "AVISIT",
    adjust = "none"
  )
  cmp_df <- as.data.frame(summary(cmp, infer = c(TRUE, TRUE), level = 0.95, adjust = "none"))
  cmp_df$covariance <- covariance
  list(emmeans = emm_df, contrasts = cmp_df)
}

primary <- extract_emmeans(primary_fit, "Unstructured")
sensitivity <- extract_emmeans(sensitivity_fit, "AR1 heterogeneous")

primary_lsmeans <- primary$emmeans
primary_contrasts <- primary$contrasts
all_contrasts <- rbind(primary$contrasts, sensitivity$contrasts)

write.csv(primary_lsmeans, file.path(out_dir, "mmrm_lsmeans.csv"), row.names = FALSE, na = "")
write.csv(primary_contrasts, file.path(out_dir, "mmrm_treatment_contrasts.csv"), row.names = FALSE, na = "")
write.csv(all_contrasts, file.path(out_dir, "mmrm_covariance_sensitivity.csv"), row.names = FALSE, na = "")

add_check("Primary unstructured MMRM returned finite likelihood", is.finite(model_diagnostics$logLik[1]), paste0("logLik=", format(model_diagnostics$logLik[1], digits = 10)))
add_check("AR1H covariance sensitivity returned finite likelihood", is.finite(model_diagnostics$logLik[2]), paste0("logLik=", format(model_diagnostics$logLik[2], digits = 10)))
add_check("Primary MMRM has six active-vs-placebo visit contrasts", nrow(primary_contrasts) == 6, paste0("contrast rows=", nrow(primary_contrasts)))

contrast_numeric <- c("estimate", "SE", "df", "lower.CL", "upper.CL", "p.value")
missing_contrast_cols <- setdiff(contrast_numeric, names(primary_contrasts))
if (length(missing_contrast_cols) > 0) {
  add_check("Primary MMRM contrast columns available", FALSE, paste(missing_contrast_cols, collapse = ", "))
} else {
  finite_contrasts <- all(vapply(primary_contrasts[contrast_numeric], function(z) all(is.finite(as.numeric(z))), logical(1)))
  add_check("Primary MMRM contrast estimates and inference finite", finite_contrasts, paste0("rows=", nrow(primary_contrasts)))
}

week24 <- primary_contrasts[as.character(primary_contrasts$AVISIT) == "Week 24", , drop = FALSE]
add_check("Primary MMRM has two Week 24 active-vs-placebo contrasts", nrow(week24) == 2, paste0("Week 24 rows=", nrow(week24)))

# Compare the longitudinal Week 24 estimands with the earlier observed-case ANCOVA.
ancova_path <- file.path(out_dir, "table10_actot_ancova_contrasts.csv")
if (file.exists(ancova_path) && nrow(week24) == 2) {
  ancova <- read.csv(ancova_path, check.names = FALSE)
  ancova <- ancova[ancova$analysis == "Observed Week 24", c("comparison", "estimate", "se", "ci95_lower", "ci95_upper", "p_value"), drop = FALSE]
  week24_compare <- data.frame(
    comparison = as.character(week24$contrast),
    mmrm_estimate = as.numeric(week24$estimate),
    mmrm_se = as.numeric(week24$SE),
    mmrm_ci95_lower = as.numeric(week24$lower.CL),
    mmrm_ci95_upper = as.numeric(week24$upper.CL),
    mmrm_p_value = as.numeric(week24$p.value),
    stringsAsFactors = FALSE
  )
  merged <- merge(week24_compare, ancova, by = "comparison", all = TRUE)
  names(merged)[names(merged) == "estimate"] <- "ancova_estimate"
  names(merged)[names(merged) == "se"] <- "ancova_se"
  names(merged)[names(merged) == "ci95_lower"] <- "ancova_ci95_lower"
  names(merged)[names(merged) == "ci95_upper"] <- "ancova_ci95_upper"
  names(merged)[names(merged) == "p_value"] <- "ancova_p_value"
  merged$estimate_difference_mmrm_minus_ancova <- merged$mmrm_estimate - merged$ancova_estimate
  write.csv(merged, file.path(out_dir, "mmrm_vs_week24_ancova.csv"), row.names = FALSE, na = "")
}

qc <- add_check(get = TRUE)
write.csv(qc, file.path(out_dir, "mmrm_qc.csv"), row.names = FALSE, na = "")

required <- qc[qc$required, , drop = FALSE]
all_required <- nrow(required) > 0 && all(required$passed)

metrics <- list(
  analysis_version = "0.5.0",
  r_version = R.version.string,
  mmrm_version = as.character(utils::packageVersion("mmrm")),
  emmeans_version = as.character(utils::packageVersion("emmeans")),
  observed_records = nrow(d),
  subjects = length(unique(d$USUBJID)),
  visit_counts = setNames(as.list(as.integer(table(d$AVISIT))), names(table(d$AVISIT))),
  primary_covariance = "unstructured",
  sensitivity_covariance = "AR1 heterogeneous",
  primary_logLik = as.numeric(logLik(primary_fit)),
  sensitivity_logLik = as.numeric(logLik(sensitivity_fit)),
  primary_AIC = AIC(primary_fit),
  sensitivity_AIC = AIC(sensitivity_fit),
  required_checks = nrow(required),
  required_passed = sum(required$passed),
  all_required_passed = all_required
)
jsonlite::write_json(metrics, file.path(out_dir, "mmrm_metrics.json"), pretty = TRUE, auto_unbox = TRUE, na = "null")
writeLines(capture.output(summary(primary_fit)), file.path(out_dir, "mmrm_model_summary.txt"))

week24_lines <- if (nrow(week24) == 2) {
  apply(week24, 1, function(r) {
    sprintf(
      "- %s: estimate=%.4f; SE=%.4f; 95%% CI [%.4f, %.4f]; df=%.2f; p=%.4g.",
      r[["contrast"]], as.numeric(r[["estimate"]]), as.numeric(r[["SE"]]),
      as.numeric(r[["lower.CL"]]), as.numeric(r[["upper.CL"]]),
      as.numeric(r[["df"]]), as.numeric(r[["p.value"]])
    )
  })
} else {
  "- Week 24 contrasts unavailable."
}

summary_lines <- c(
  "# ACTOT MMRM run summary",
  "",
  paste0("- R: ", R.version.string, "."),
  paste0("- mmrm: ", metrics$mmrm_version, "; emmeans: ", metrics$emmeans_version, "."),
  paste0("- Observed post-baseline records: ", metrics$observed_records, " from ", metrics$subjects, " subjects."),
  paste0("- Visit records: ", paste(names(metrics$visit_counts), unlist(metrics$visit_counts), sep = "=", collapse = "; "), "."),
  "- Primary model: REML MMRM with treatment-by-visit, baseline-by-visit and unstructured within-subject covariance; Satterthwaite df.",
  "- Sensitivity covariance: heterogeneous AR(1) with the same fixed-effects model.",
  paste0("- Required MMRM QC: ", metrics$required_passed, "/", metrics$required_checks, " passed."),
  "",
  "## Primary Week 24 contrasts",
  week24_lines,
  "",
  "Only observed Week 8/16/24 ACTOT records enter the MMRM; LOCF values are not used in this longitudinal model."
)
writeLines(summary_lines, file.path(out_dir, "mmrm_run_summary.md"))
cat(paste(summary_lines, collapse = "\n"), "\n")

if (!all_required) {
  print(required[!required$passed, , drop = FALSE])
  stop("Required MMRM QC failed; see outputs/mmrm_qc.csv")
}
