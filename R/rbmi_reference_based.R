options(stringsAsFactors = FALSE)

required_packages <- c("jsonlite", "rbmi")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

suppressPackageStartupMessages(library(rbmi))

out_dir <- "outputs"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

spec <- jsonlite::fromJSON("spec/reference_based_mi.json", simplifyVector = FALSE)
base_spec <- jsonlite::fromJSON(as.character(spec$base_imputation_spec), simplifyVector = FALSE)

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

rbmi_version <- as.character(utils::packageVersion("rbmi"))
expected_rbmi <- as.character(spec$reference_based_imputation$required_version)
add_check(
  "rbmi package version matches reference-based specification",
  identical(rbmi_version, expected_rbmi),
  paste0("installed=", rbmi_version, "; required=", expected_rbmi)
)
add_check(
  "v0.14 reuses the controlled v0.13 MI base specification",
  identical(as.character(base_spec$version), "0.13.0"),
  paste0("base_version=", as.character(base_spec$version))
)

adsl_path <- file.path(out_dir, "adsl_style.csv")
adqs_path <- file.path(out_dir, "adqs_actot_style.csv")
v013_mar_path <- file.path(out_dir, "table20_rbmi_mar_pairwise.csv")
for (p in c(adsl_path, adqs_path, v013_mar_path)) {
  if (!file.exists(p)) stop("Missing required upstream output: ", p)
}

adsl <- read.csv(adsl_path, na.strings = c("", "NA"), check.names = FALSE)
adqs <- read.csv(adqs_path, na.strings = c("", "NA"), check.names = FALSE)
v013_mar <- read.csv(v013_mar_path, na.strings = c("", "NA"), check.names = FALSE)

required_adsl <- c("STUDYID", "USUBJID", "TRT01A", "RANDFL", "DCSFL", "TRTSDT", "TRTEDT")
required_adqs <- c("STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "CHG", "ABLFL", "EFFFL", "QSSEQ")
missing_adsl <- setdiff(required_adsl, names(adsl))
missing_adqs <- setdiff(required_adqs, names(adqs))
if (length(missing_adsl) > 0) stop("ADSL-style missing columns: ", paste(missing_adsl, collapse = ", "))
if (length(missing_adqs) > 0) stop("ACTOT analysis input missing columns: ", paste(missing_adqs, collapse = ", "))

adsl$RANDFL_N <- norm_chr(adsl$RANDFL)
adsl$DCSFL_N <- norm_chr(adsl$DCSFL)
adsl$TRT01A_N <- norm_chr(adsl$TRT01A)
adsl$TRTSDT_D <- as.Date(adsl$TRTSDT)
adsl$TRTEDT_D <- as.Date(adsl$TRTEDT)
adsl$TRTEND_DAY <- as.integer(adsl$TRTEDT_D - adsl$TRTSDT_D) + 1L

adqs$TRT01A_N <- norm_chr(adqs$TRT01A)
adqs$AVISIT_U <- toupper(norm_chr(adqs$AVISIT))
adqs$ABLFL_N <- norm_chr(adqs$ABLFL)
adqs$EFFFL_N <- norm_chr(adqs$EFFFL)
adqs$AVAL_N <- suppressWarnings(as.numeric(adqs$AVAL))
adqs$BASE_N <- suppressWarnings(as.numeric(adqs$BASE))
adqs$CHG_N <- suppressWarnings(as.numeric(adqs$CHG))
adqs$QSSEQ_N <- suppressWarnings(as.numeric(adqs$QSSEQ))

expected_arms <- c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")
expected_visits <- unlist(base_spec$imputation$visits, use.names = FALSE)
visit_map <- c("WEEK 8" = "8", "WEEK 16" = "16", "WEEK 24" = "24")
visit_days_raw <- unlist(spec$intercurrent_event$nominal_visit_days, use.names = TRUE)
visit_days <- stats::setNames(as.integer(visit_days_raw), names(visit_days_raw))

first_affected_visit <- function(end_day) {
  if (!is.finite(end_day)) return(NA_character_)
  candidates <- visit_days[visit_days > end_day]
  if (length(candidates) == 0) return(NA_character_)
  names(candidates)[which.min(candidates)]
}

subject_context <- adsl[
  adsl$RANDFL_N == "Y" & adsl$TRT01A_N %in% expected_arms,
  c("STUDYID", "USUBJID", "TRT01A_N", "DCSFL_N", "TRTSDT_D", "TRTEDT_D", "TRTEND_DAY"),
  drop = FALSE
]
subject_context <- subject_context[!duplicated(paste(subject_context$STUDYID, subject_context$USUBJID, sep = "|")), , drop = FALSE]
names(subject_context)[3:6] <- c("TRT01A", "DCSFL", "TRTSDT", "TRTEDT")

base <- adqs[
  adqs$ABLFL_N == "Y" & is.finite(adqs$AVAL_N),
  c("STUDYID", "USUBJID", "TRT01A_N", "AVAL_N", "QSSEQ_N"),
  drop = FALSE
]
base <- base[order(base$STUDYID, base$USUBJID, base$QSSEQ_N), , drop = FALSE]
base <- base[!duplicated(paste(base$STUDYID, base$USUBJID, sep = "|"), fromLast = TRUE), , drop = FALSE]
names(base)[3:4] <- c("TRT01A_BASE", "BASE")

target <- merge(
  subject_context,
  base[, c("STUDYID", "USUBJID", "TRT01A_BASE", "BASE")],
  by = c("STUDYID", "USUBJID"),
  all = FALSE,
  sort = FALSE
)
treatment_mismatch <- target$TRT01A != target$TRT01A_BASE
add_check(
  "Target-population treatment matches baseline ACTOT treatment",
  !any(treatment_mismatch),
  paste0("mismatches=", sum(treatment_mismatch))
)
target <- target[!treatment_mismatch, , drop = FALSE]
add_check(
  "Reference-based MI target population contains 254 randomised baseline-ACTOT subjects",
  nrow(target) == 254,
  paste0("subjects=", nrow(target))
)

obs <- adqs[
  adqs$EFFFL_N == "Y" &
    adqs$ABLFL_N != "Y" &
    adqs$TRT01A_N %in% expected_arms &
    adqs$AVISIT_U %in% names(visit_map) &
    is.finite(adqs$CHG_N) & is.finite(adqs$BASE_N),
  c("STUDYID", "USUBJID", "TRT01A_N", "AVISIT_U", "CHG_N", "BASE_N", "QSSEQ_N"),
  drop = FALSE
]
obs$VISIT <- unname(visit_map[obs$AVISIT_U])
obs_key <- paste(obs$STUDYID, obs$USUBJID, obs$VISIT, sep = "|")
add_check(
  "Observed ACTOT subject-visit rows remain unique for reference-based MI",
  !any(duplicated(obs_key)),
  paste0("duplicate_rows=", sum(duplicated(obs_key)))
)

comparison_list <- base_spec$analysis$comparisons
strategies <- unlist(spec$reference_based_imputation$strategies, use.names = FALSE)
initial_strategy <- as.character(spec$reference_based_imputation$initial_draw_strategy)
reference_arm_controlled <- as.character(spec$reference_based_imputation$reference_arm)
n_imp <- as.integer(base_spec$imputation$n_imputations)
fail_threshold <- as.numeric(base_spec$imputation$failure_threshold)
mcse_threshold <- as.numeric(spec$reference_based_imputation$max_mcse_estimate_to_se_ratio)

built_in <- names(rbmi::getStrategies())
add_check(
  "All controlled reference-based strategies are built into rbmi",
  all(strategies %in% built_in),
  paste0("strategies=", paste(strategies, collapse = ","))
)
add_check(
  "Controlled reference-based analysis reuses 200 imputations",
  n_imp == 200,
  paste0("n_imputations=", n_imp)
)

pool_week24 <- function(impute_obj, vars_an) {
  ana <- rbmi::analyse(impute_obj, rbmi::ancova, vars = vars_an, visits = "24")
  pooled <- rbmi::pool(
    ana,
    conf.level = as.numeric(spec$analysis$confidence_level),
    alternative = "two.sided"
  )
  pooled_df <- as.data.frame(pooled)
  row <- pooled_df[pooled_df$parameter == "trt_24", , drop = FALSE]
  if (nrow(row) != 1) stop("Expected one pooled trt_24 row; got ", nrow(row))
  mc <- tryCatch(rbmi::mcse(pooled, ana), error = function(e) NULL)
  mc_df <- if (is.null(mc)) NULL else as.data.frame(mc)
  mc_row <- if (is.null(mc_df)) NULL else mc_df[mc_df$parameter == "trt_24", , drop = FALSE]
  list(
    pool = pooled,
    row = row,
    mcse_est = if (!is.null(mc_row) && nrow(mc_row) == 1) as.numeric(mc_row$est[1]) else NA_real_,
    mcse_se = if (!is.null(mc_row) && nrow(mc_row) == 1) as.numeric(mc_row$se[1]) else NA_real_
  )
}

result_rows <- list()
ice_audit_rows <- list()
draw_diag_rows <- list()

for (cmp in comparison_list) {
  cmp_id <- as.character(cmp$id)
  active <- as.character(cmp$active_arm)
  reference <- as.character(cmp$reference_arm)
  seed <- as.integer(cmp$seed)

  if (!identical(reference, reference_arm_controlled)) {
    stop("Comparison reference arm differs from controlled reference arm: ", reference)
  }

  pair_subjects <- target[
    target$TRT01A %in% c(reference, active),
    c("STUDYID", "USUBJID", "TRT01A", "DCSFL", "TRTSDT", "TRTEDT", "TRTEND_DAY", "BASE"),
    drop = FALSE
  ]
  pair_subjects <- pair_subjects[order(pair_subjects$USUBJID), , drop = FALSE]

  grid <- merge(
    pair_subjects[, c("STUDYID", "USUBJID", "TRT01A", "BASE"), drop = FALSE],
    data.frame(VISIT = expected_visits, stringsAsFactors = FALSE),
    by = NULL,
    all = TRUE
  )
  pair_obs <- obs[
    obs$TRT01A_N %in% c(reference, active),
    c("STUDYID", "USUBJID", "VISIT", "CHG_N"),
    drop = FALSE
  ]
  dat <- merge(
    grid,
    pair_obs,
    by = c("STUDYID", "USUBJID", "VISIT"),
    all.x = TRUE,
    sort = FALSE
  )
  names(dat)[names(dat) == "CHG_N"] <- "CHG"
  dat <- dat[order(dat$USUBJID, match(dat$VISIT, expected_visits)), , drop = FALSE]
  row.names(dat) <- NULL

  dat$USUBJID <- factor(dat$USUBJID)
  dat$VISIT <- factor(dat$VISIT, levels = expected_visits)
  dat$TRT01A <- factor(dat$TRT01A, levels = c(reference, active))
  dat$BASE <- as.numeric(dat$BASE)
  dat$CHG <- as.numeric(dat$CHG)

  active_disc <- pair_subjects[pair_subjects$TRT01A == active & pair_subjects$DCSFL == "Y", , drop = FALSE]
  valid_dates <- is.finite(active_disc$TRTEND_DAY)
  add_check(
    paste0(cmp_id, " active discontinuers have usable treatment timing"),
    all(valid_dates),
    paste0("discontinuers=", nrow(active_disc), "; invalid_timing=", sum(!valid_dates))
  )
  active_disc$FIRST_AFFECTED_VISIT <- vapply(active_disc$TRTEND_DAY, first_affected_visit, character(1))
  active_ice <- active_disc[!is.na(active_disc$FIRST_AFFECTED_VISIT), , drop = FALSE]
  add_check(
    paste0(cmp_id, " has active discontinuers with a scheduled post-treatment visit"),
    nrow(active_ice) > 0,
    paste0("ICE_subjects=", nrow(active_ice), "; active_discontinuers=", nrow(active_disc))
  )

  audit <- data.frame(
    comparison_id = cmp_id,
    USUBJID = as.character(active_ice$USUBJID),
    active_arm = active,
    TRTSDT = as.character(active_ice$TRTSDT),
    TRTEDT = as.character(active_ice$TRTEDT),
    treatment_end_day = as.integer(active_ice$TRTEND_DAY),
    first_affected_visit = as.character(active_ice$FIRST_AFFECTED_VISIT),
    observed_post_ice_n = 0L,
    initial_strategy = initial_strategy,
    stringsAsFactors = FALSE
  )

  if (nrow(audit) > 0) {
    for (i in seq_len(nrow(audit))) {
      subject_rows <- dat[as.character(dat$USUBJID) == audit$USUBJID[i], , drop = FALSE]
      affected_position <- match(audit$first_affected_visit[i], expected_visits)
      positions <- match(as.character(subject_rows$VISIT), expected_visits)
      audit$observed_post_ice_n[i] <- sum(is.finite(subject_rows$CHG) & positions >= affected_position)
    }
  }

  observed_post_ice_total <- sum(audit$observed_post_ice_n)
  add_check(
    paste0(cmp_id, " has zero observed scheduled ACTOT outcomes on/after first affected visit"),
    observed_post_ice_total == 0,
    paste0("observed_post_ice=", observed_post_ice_total)
  )
  if (isTRUE(spec$intercurrent_event$require_zero_observed_post_ice_for_strategy_switch) && observed_post_ice_total != 0) {
    stop("Reference-based strategy switching is not allowed with observed post-ICE data for ", cmp_id)
  }

  ice_key <- paste(audit$USUBJID, audit$first_affected_visit, sep = "|")
  add_check(
    paste0(cmp_id, " ICE audit has one first-affected visit per subject"),
    !any(duplicated(audit$USUBJID)) && !any(duplicated(ice_key)),
    paste0("ICE_rows=", nrow(audit))
  )
  ice_audit_rows[[length(ice_audit_rows) + 1]] <- audit

  data_ice <- data.frame(
    USUBJID = audit$USUBJID,
    VISIT = audit$first_affected_visit,
    strategy = rep(initial_strategy, nrow(audit)),
    stringsAsFactors = FALSE
  )

  vars_imp <- rbmi::set_vars(
    outcome = "CHG",
    visit = "VISIT",
    subjid = "USUBJID",
    group = "TRT01A",
    covariates = c("BASE*VISIT", "TRT01A*VISIT"),
    strategy = "strategy"
  )
  method <- rbmi::method_approxbayes(
    covariance = as.character(base_spec$imputation$covariance),
    threshold = fail_threshold,
    same_cov = isTRUE(base_spec$imputation$same_covariance_across_groups),
    REML = isTRUE(base_spec$imputation$reml),
    n_samples = n_imp
  )

  set.seed(seed)
  draw_obj <- rbmi::draws(
    data = dat,
    data_ice = data_ice,
    vars = vars_imp,
    method = method,
    ncores = 2,
    quiet = TRUE
  )
  n_failures <- if (is.null(draw_obj$n_failures)) 0L else as.integer(draw_obj$n_failures)
  n_samples_actual <- length(draw_obj$samples)
  max_failures <- ceiling(fail_threshold * n_imp)
  add_check(
    paste0(cmp_id, " reference-based model produced requested draws"),
    n_samples_actual == n_imp,
    paste0("samples=", n_samples_actual, "; requested=", n_imp)
  )
  add_check(
    paste0(cmp_id, " reference-based model failures remain within threshold"),
    n_failures <= max_failures,
    paste0("failures=", n_failures, "; maximum=", max_failures)
  )

  draw_diag_rows[[length(draw_diag_rows) + 1]] <- data.frame(
    comparison_id = cmp_id,
    active_arm = active,
    reference_arm = reference,
    seed = seed,
    requested_imputations = n_imp,
    completed_draws = n_samples_actual,
    model_failures = n_failures,
    ICE_subjects = nrow(audit),
    observed_post_ice_n = observed_post_ice_total,
    initial_strategy = initial_strategy,
    stringsAsFactors = FALSE
  )

  vars_an <- rbmi::set_vars(
    outcome = "CHG",
    visit = "VISIT",
    subjid = "USUBJID",
    group = "TRT01A",
    covariates = c("BASE")
  )
  references <- stats::setNames(c(reference, reference), c(reference, active))

  for (strategy in strategies) {
    update_strategy <- data.frame(
      USUBJID = audit$USUBJID,
      strategy = rep(strategy, nrow(audit)),
      stringsAsFactors = FALSE
    )
    impute_obj <- suppressWarnings(
      rbmi::impute(
        draw_obj,
        references = references,
        update_strategy = update_strategy
      )
    )
    pooled_res <- pool_week24(impute_obj, vars_an)
    pr <- pooled_res$row
    result_rows[[length(result_rows) + 1]] <- data.frame(
      comparison_id = cmp_id,
      comparison = paste0(active, " vs ", reference),
      active_arm = active,
      reference_arm = reference,
      strategy_id = strategy,
      strategy_label = switch(
        strategy,
        MAR = "Missing at Random",
        JR = "Jump to Reference",
        CR = "Copy Reference",
        CIR = "Copy Increments in Reference",
        strategy
      ),
      active_ice_subjects = nrow(audit),
      estimate_active_minus_placebo = as.numeric(pr$est[1]),
      SE = as.numeric(pr$se[1]),
      ci95_lower = as.numeric(pr$lci[1]),
      ci95_upper = as.numeric(pr$uci[1]),
      p_value = as.numeric(pr$pval[1]),
      mcse_estimate = pooled_res$mcse_est,
      mcse_se = pooled_res$mcse_se,
      pool_method = as.character(pooled_res$pool$method),
      imputations = as.integer(pooled_res$pool$N),
      stringsAsFactors = FALSE
    )
  }
}

results <- do.call(rbind, result_rows)
ice_audit <- do.call(rbind, ice_audit_rows)
draw_diagnostics <- do.call(rbind, draw_diag_rows)

results$estimate_change_from_MAR <- NA_real_
for (cmp_id in unique(results$comparison_id)) {
  mar <- results[results$comparison_id == cmp_id & results$strategy_id == "MAR", "estimate_active_minus_placebo"]
  if (length(mar) == 1) {
    idx <- results$comparison_id == cmp_id
    results$estimate_change_from_MAR[idx] <- results$estimate_active_minus_placebo[idx] - mar
  }
}
results$mcse_estimate_to_se_ratio <- ifelse(
  is.finite(results$mcse_estimate) & is.finite(results$SE) & results$SE > 0,
  results$mcse_estimate / results$SE,
  NA_real_
)
results$mcse_pass <- is.finite(results$mcse_estimate_to_se_ratio) & results$mcse_estimate_to_se_ratio <= mcse_threshold

expected_rows <- length(comparison_list) * length(strategies)
add_check(
  "Reference-based MI output contains two comparisons by four strategies",
  nrow(results) == expected_rows,
  paste0("rows=", nrow(results), "; expected=", expected_rows)
)
finite_cols <- c("estimate_active_minus_placebo", "SE", "ci95_lower", "ci95_upper", "p_value", "mcse_estimate")
finite_results <- all(vapply(results[finite_cols], function(z) all(is.finite(as.numeric(z))), logical(1)))
add_check(
  "All reference-based MI estimates and inference are finite",
  finite_results,
  paste0("rows=", nrow(results))
)
add_check(
  "All reference-based analyses use Rubin pooling",
  all(results$pool_method == "rubin"),
  paste(unique(results$pool_method), collapse = ",")
)
add_check(
  "All reference-based analyses pool the controlled 200 imputations",
  all(results$imputations == n_imp),
  paste0("pooled_N=", paste(unique(results$imputations), collapse = ","))
)
add_check(
  "All reference-based strategies satisfy the controlled MCSE precision gate",
  all(results$mcse_pass),
  paste0(
    "max_ratio=",
    if (any(is.finite(results$mcse_estimate_to_se_ratio))) sprintf("%.6f", max(results$mcse_estimate_to_se_ratio, na.rm = TRUE)) else "NA",
    "; threshold=", sprintf("%.6f", mcse_threshold)
  )
)

v013_diag <- merge(
  results[results$strategy_id == "MAR", c("comparison_id", "comparison", "estimate_active_minus_placebo", "SE", "p_value"), drop = FALSE],
  v013_mar[, c("comparison_id", "estimate_active_minus_placebo", "SE", "p_value"), drop = FALSE],
  by = "comparison_id",
  all.x = TRUE,
  suffixes = c("_v014_mar", "_v013_mar")
)
v013_diag$estimate_difference_v014_minus_v013 <- v013_diag$estimate_active_minus_placebo_v014_mar - v013_diag$estimate_active_minus_placebo_v013_mar
v013_diag$se_difference_v014_minus_v013 <- v013_diag$SE_v014_mar - v013_diag$SE_v013_mar

write.csv(ice_audit, file.path(out_dir, "rbmi_reference_ice_audit.csv"), row.names = FALSE, na = "")
write.csv(draw_diagnostics, file.path(out_dir, "rbmi_reference_draw_diagnostics.csv"), row.names = FALSE, na = "")
write.csv(results, file.path(out_dir, "table22_rbmi_reference_based.csv"), row.names = FALSE, na = "")
write.csv(
  results[, c("comparison_id", "strategy_id", "mcse_estimate", "SE", "mcse_estimate_to_se_ratio", "mcse_pass"), drop = FALSE],
  file.path(out_dir, "rbmi_reference_mcse_qc.csv"),
  row.names = FALSE,
  na = ""
)
write.csv(v013_diag, file.path(out_dir, "rbmi_reference_vs_v013_mar.csv"), row.names = FALSE, na = "")

qc <- add_check(get = TRUE)
write.csv(qc, file.path(out_dir, "rbmi_reference_qc.csv"), row.names = FALSE, na = "")
required <- qc[qc$required, , drop = FALSE]
all_required <- nrow(required) > 0 && all(required$passed)

ice_counts <- aggregate(USUBJID ~ comparison_id + first_affected_visit, data = ice_audit, FUN = length)
names(ice_counts)[3] <- "n"
write.csv(ice_counts, file.path(out_dir, "rbmi_reference_ice_counts.csv"), row.names = FALSE, na = "")

metrics <- list(
  analysis_version = "0.14.0",
  r_version = R.version.string,
  rbmi_version = rbmi_version,
  base_mi_version = as.character(base_spec$version),
  n_imputations = n_imp,
  strategies = strategies,
  comparisons = length(comparison_list),
  result_rows = nrow(results),
  ice_subject_rows = nrow(ice_audit),
  observed_post_ice = sum(ice_audit$observed_post_ice_n),
  required_checks = nrow(required),
  required_passed = sum(required$passed),
  all_required_passed = all_required,
  max_mcse_estimate_to_se_ratio = if (any(is.finite(results$mcse_estimate_to_se_ratio))) max(results$mcse_estimate_to_se_ratio, na.rm = TRUE) else NA_real_,
  mcse_threshold = mcse_threshold
)
jsonlite::write_json(metrics, file.path(out_dir, "rbmi_reference_metrics.json"), pretty = TRUE, auto_unbox = TRUE, na = "null")
writeLines(capture.output(sessionInfo()), file.path(out_dir, "rbmi_reference_session_info.txt"))

summary_lines <- c(
  "# rbmi reference-based MI sensitivity summary",
  "",
  sprintf("- rbmi version: %s", rbmi_version),
  sprintf("- Base MI: v%s approximate-Bayesian draws, %d imputations, Week 8/16/24 ACTOT history.", as.character(base_spec$version), n_imp),
  sprintf("- Strategies: %s.", paste(strategies, collapse = ", ")),
  "- ICE: recorded treatment discontinuation; first affected visit is the first nominal Week 8/16/24 visit after recorded treatment end.",
  "- Non-MAR strategies are applied only to active-arm discontinuers; placebo remains MAR and is the reference distribution.",
  sprintf("- Observed scheduled ACTOT outcomes on/after first affected visit: %d.", sum(ice_audit$observed_post_ice_n)),
  sprintf("- Monte Carlo precision criterion: MCSE(estimate) / pooled SE <= %.3f.", mcse_threshold),
  "",
  "## Pooled Week 24 results",
  ""
)
ordered <- results[order(results$comparison_id, match(results$strategy_id, strategies)), , drop = FALSE]
for (i in seq_len(nrow(ordered))) {
  r <- ordered[i, , drop = FALSE]
  summary_lines <- c(
    summary_lines,
    sprintf(
      "- %s / %s: estimate=%.4f; SE=%.4f; 95%% CI [%.4f, %.4f]; p=%.4g; MCSE ratio=%.4f.",
      r$comparison,
      r$strategy_id,
      r$estimate_active_minus_placebo,
      r$SE,
      r$ci95_lower,
      r$ci95_upper,
      r$p_value,
      r$mcse_estimate_to_se_ratio
    )
  )
}
summary_lines <- c(
  summary_lines,
  "",
  sprintf("Required QC: %d/%d passed.", sum(required$passed), nrow(required)),
  "",
  "Evidence boundary: independent public-data portfolio work using recorded treatment-discontinuation timing. JR/CR/CIR results are controlled sensitivity analyses, not sponsor-approved estimand decisions or regulatory analyses."
)
writeLines(summary_lines, file.path(out_dir, "rbmi_reference_summary.md"))
cat(paste(summary_lines, collapse = "\n"), "\n")

if (!all_required) {
  stop("Reference-based rbmi sensitivity QC failed; inspect outputs/rbmi_reference_qc.csv")
}
