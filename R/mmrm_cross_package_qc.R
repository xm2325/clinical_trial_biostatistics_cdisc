options(stringsAsFactors = FALSE)

required_packages <- c("jsonlite", "nlme")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

suppressPackageStartupMessages({
  library(nlme)
})

out_dir <- "outputs"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

norm_chr <- function(x) {
  y <- as.character(x)
  y[is.na(y)] <- ""
  trimws(y)
}

input_path <- file.path(out_dir, "adqs_actot_style.csv")
if (!file.exists(input_path)) stop("Missing ACTOT source-derived input: ", input_path)

x <- read.csv(input_path, na.strings = c("", "NA"), check.names = FALSE)
required_cols <- c("STUDYID", "USUBJID", "TRT01A", "AVISIT", "AVAL", "BASE", "CHG", "ABLFL", "EFFFL", "QSSEQ")
missing_cols <- setdiff(required_cols, names(x))
if (length(missing_cols) > 0) stop("ACTOT input missing columns: ", paste(missing_cols, collapse = ", "))

expected_arms <- c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")
expected_visits <- c("Week 8", "Week 16", "Week 24")
visit_map <- c("WEEK 8" = "Week 8", "WEEK 16" = "Week 16", "WEEK 24" = "Week 24")

# Reconstruct the observed-data analysis rows independently from the source-derived
# ACTOT file rather than consuming mmrm_analysis_dataset.csv from the primary program.
x$AVISIT_U <- toupper(norm_chr(x$AVISIT))
x$ABLFL_N <- norm_chr(x$ABLFL)
x$EFFFL_N <- norm_chr(x$EFFFL)
x$TRT01A_N <- norm_chr(x$TRT01A)
x$AVAL <- suppressWarnings(as.numeric(x$AVAL))
x$BASE <- suppressWarnings(as.numeric(x$BASE))
x$CHG <- suppressWarnings(as.numeric(x$CHG))

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
d$VISITN <- match(as.character(d$AVISIT), expected_visits)
d$USUBJID <- factor(d$USUBJID)
d <- d[order(d$USUBJID, d$VISITN, d$QSSEQ), ]
row.names(d) <- NULL

if (nrow(d) == 0) stop("Independent MMRM reconstruction has zero rows")
if (anyDuplicated(paste(d$USUBJID, d$VISITN, sep = "|"))) stop("Independent MMRM subject-visit keys are not unique")
if (max(abs(d$CHG - (d$AVAL - d$BASE)), na.rm = TRUE) > 1e-12) stop("Independent MMRM CHG does not equal AVAL-BASE")

analysis_rows <- data.frame(
  STUDYID = norm_chr(d$STUDYID),
  USUBJID = norm_chr(d$USUBJID),
  TRT01A = norm_chr(d$TRT01A),
  AVISIT = norm_chr(d$AVISIT),
  AVAL = d$AVAL,
  BASE = d$BASE,
  CHG = d$CHG,
  QSSEQ = d$QSSEQ,
  stringsAsFactors = FALSE
)
write.csv(
  analysis_rows,
  file.path(out_dir, "mmrm_cross_package_analysis_dataset.csv"),
  row.names = FALSE,
  na = ""
)

# nlme::gls with corSymm + visit-specific residual variances is a separate
# implementation of an unstructured marginal covariance MMRM. The primary
# production-style portfolio model remains mmrm::mmrm with Satterthwaite df.
fit <- gls(
  CHG ~ TRT01A * AVISIT + BASE * AVISIT,
  data = d,
  correlation = corSymm(form = ~ VISITN | USUBJID),
  weights = varIdent(form = ~ 1 | AVISIT),
  method = "REML",
  na.action = na.omit,
  control = glsControl(maxIter = 200, msMaxIter = 200, tolerance = 1e-8, msTol = 1e-8)
)

beta <- coef(fit)
vc <- vcov(fit)
baseline_mean <- mean(d$BASE)
newdata <- data.frame(
  TRT01A = factor(expected_arms, levels = expected_arms),
  AVISIT = factor(rep("Week 24", length(expected_arms)), levels = expected_visits, ordered = TRUE),
  BASE = rep(baseline_mean, length(expected_arms)),
  stringsAsFactors = FALSE
)
mm <- model.matrix(delete.response(terms(fit)), newdata)
if (!all(names(beta) %in% colnames(mm))) stop("Independent model-matrix columns do not align with fixed effects")
mm <- mm[, names(beta), drop = FALSE]

contrast_specs <- list(
  "Xanomeline Low Dose vs Placebo" = c(-1, 1, 0),
  "Xanomeline High Dose vs Placebo" = c(-1, 0, 1)
)
rows <- lapply(names(contrast_specs), function(label) {
  weights <- contrast_specs[[label]]
  cvec <- as.numeric(t(weights) %*% mm)
  names(cvec) <- colnames(mm)
  estimate <- sum(cvec * beta)
  se <- sqrt(as.numeric(t(cvec) %*% vc %*% cvec))
  data.frame(
    contrast = label,
    AVISIT = "Week 24",
    estimate = estimate,
    SE = se,
    method = "nlme::gls",
    covariance = "Unstructured (corSymm + varIdent)",
    inference_scope = "point estimate and model-based SE validation; df/p-value not cross-validated",
    stringsAsFactors = FALSE
  )
})
contrasts <- do.call(rbind, rows)
write.csv(contrasts, file.path(out_dir, "mmrm_cross_package_contrasts.csv"), row.names = FALSE, na = "")

model_metrics <- list(
  analysis_version = "0.16.0",
  implementation = "nlme::gls",
  covariance = "unstructured via corSymm + varIdent",
  inference_scope = "analysis-row identity plus point estimate and model-based SE validation only",
  observed_records = nrow(d),
  subjects = length(unique(d$USUBJID)),
  baseline_mean = baseline_mean,
  logLik = as.numeric(logLik(fit)),
  AIC = AIC(fit),
  BIC = BIC(fit),
  nlme_version = as.character(utils::packageVersion("nlme")),
  r_version = R.version.string
)
jsonlite::write_json(model_metrics, file.path(out_dir, "mmrm_cross_package_metrics.json"), pretty = TRUE, auto_unbox = TRUE, na = "null")
writeLines(capture.output(summary(fit)), file.path(out_dir, "mmrm_cross_package_model_summary.txt"))

cat("Independent nlme MMRM reconstruction complete:\n")
cat("Independent analysis rows:", nrow(analysis_rows), "\n")
print(contrasts)
