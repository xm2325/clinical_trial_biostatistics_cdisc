options(stringsAsFactors = FALSE)

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Package 'jsonlite' is required. Install it before running this script.")
}

out_dir <- "outputs"
cache_dir <- "cache"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

norm_chr <- function(x) {
  y <- as.character(x)
  y[is.na(y)] <- ""
  trimws(y)
}

upper_chr <- function(x) toupper(norm_chr(x))

parse_date <- function(x) {
  y <- norm_chr(x)
  y[y == ""] <- NA_character_
  suppressWarnings(as.Date(substr(y, 1, 10)))
}

min_date_or_na <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) as.Date(NA_character_) else min(x)
}

max_date_or_na <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) == 0) as.Date(NA_character_) else max(x)
}

read_source_csv <- function(name) {
  path <- file.path(cache_dir, paste0(name, ".csv"))
  if (!file.exists(path)) stop("Missing cached source: ", path)
  read.csv(path, na.strings = c("", "NA"), check.names = FALSE)
}

read_dataset_json <- function(path) {
  if (!file.exists(path)) stop("Missing Dataset-JSON source: ", path)
  payload <- jsonlite::fromJSON(
    path,
    simplifyVector = TRUE,
    simplifyDataFrame = TRUE,
    simplifyMatrix = TRUE
  )
  cols <- as.character(payload$columns$name)
  rr <- payload$rows
  if (is.matrix(rr)) {
    df <- as.data.frame(rr, stringsAsFactors = FALSE)
  } else if (is.data.frame(rr)) {
    df <- rr
  } else if (is.list(rr)) {
    mat <- do.call(rbind, lapply(rr, function(row) {
      vapply(row, function(z) {
        if (is.null(z) || length(z) == 0) NA_character_ else as.character(z[[1]])
      }, character(1))
    }))
    df <- as.data.frame(mat, stringsAsFactors = FALSE)
  } else {
    stop("Unsupported Dataset-JSON rows representation")
  }
  if (ncol(df) != length(cols)) stop("Dataset-JSON row width does not match metadata")
  names(df) <- cols
  df
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

same_num <- function(a, b, tol = 1e-10) {
  a <- suppressWarnings(as.numeric(a))
  b <- suppressWarnings(as.numeric(b))
  same_na <- is.na(a) == is.na(b)
  ok <- rep(FALSE, length(a))
  both_na <- is.na(a) & is.na(b)
  both_num <- !is.na(a) & !is.na(b)
  ok[both_na] <- TRUE
  ok[both_num] <- abs(a[both_num] - b[both_num]) <= tol
  same_na & ok
}

# Independent safety derivation from raw DM / EX / DS / AE.
dm <- read_source_csv("dm")
ae <- read_source_csv("ae")
ds <- read_source_csv("ds")
ex <- read_source_csv("ex")

ex_split <- split(ex, norm_chr(ex$USUBJID))
ds_split <- split(ds, norm_chr(ds$USUBJID))

adsl_rows <- lapply(seq_len(nrow(dm)), function(i) {
  id <- norm_chr(dm$USUBJID[i])
  study <- norm_chr(dm$STUDYID[i])
  ee <- ex_split[[id]]
  dd <- ds_split[[id]]

  has_ex <- !is.null(ee) && nrow(ee) > 0
  ex_start <- if (has_ex) min_date_or_na(parse_date(ee$EXSTDTC)) else as.Date(NA_character_)
  ex_end <- if (has_ex) max_date_or_na(parse_date(ee$EXENDTC)) else as.Date(NA_character_)
  dm_start <- parse_date(dm$RFXSTDTC[i])
  dm_end <- parse_date(dm$RFXENDTC[i])

  randomised <- !is.null(dd) && any(upper_chr(dd$DSDECOD) == "RANDOMIZED")
  completed <- !is.null(dd) && any(upper_chr(dd$DSDECOD) == "COMPLETED")
  ds_end <- as.Date(NA_character_)
  if (!is.null(dd) && nrow(dd) > 0) {
    disp <- dd[upper_chr(dd$DSCAT) == "DISPOSITION EVENT", , drop = FALSE]
    if (nrow(disp) > 0) ds_end <- max_date_or_na(parse_date(disp$DSSTDTC))
  }

  trtsdt <- ex_start
  if (is.na(trtsdt)) trtsdt <- dm_start
  trtedt <- ex_end
  end_src <- if (!is.na(ex_end)) "EX" else ""
  if (is.na(trtedt) && !is.na(dm_end)) {
    trtedt <- dm_end
    end_src <- "DM"
  }
  if (is.na(trtedt) && !is.na(ds_end)) {
    trtedt <- ds_end
    end_src <- "DS_DISPOSITION_FALLBACK"
  }

  data.frame(
    STUDYID = study,
    USUBJID = id,
    TRT01P = norm_chr(dm$ARM[i]),
    TRT01A = norm_chr(dm$ACTARM[i]),
    RANDFL = ifelse(randomised, "Y", "N"),
    SAFFL = ifelse(has_ex, "Y", "N"),
    COMPLFL = ifelse(completed, "Y", "N"),
    TRTSDT = trtsdt,
    TRTEDT = trtedt,
    TRTEDTSRC = end_src,
    stringsAsFactors = FALSE
  )
})
r_adsl <- do.call(rbind, adsl_rows)

m <- match(norm_chr(ae$USUBJID), r_adsl$USUBJID)
astdt <- parse_date(ae$AESTDTC)
trtsdt <- r_adsl$TRTSDT[m]
trtedt <- r_adsl$TRTEDT[m]
saffl <- r_adsl$SAFFL[m]
trtem <- !is.na(m) & saffl == "Y" & !is.na(astdt) & !is.na(trtsdt) & !is.na(trtedt) &
  astdt >= trtsdt & astdt <= (trtedt + 30)
trtem[is.na(trtem)] <- FALSE
r_adae <- ae
r_adae$TRTEMFL <- ifelse(trtem, "Y", "N")
r_adae$TRT01A <- r_adsl$TRT01A[m]

r_counts <- list(
  randomized_subjects = sum(r_adsl$RANDFL == "Y"),
  safety_subjects = sum(r_adsl$SAFFL == "Y"),
  completed_subjects = sum(r_adsl$RANDFL == "Y" & r_adsl$COMPLFL == "Y"),
  subjects_with_teae = length(unique(r_adae$USUBJID[r_adae$TRTEMFL == "Y"])),
  teae_events = sum(r_adae$TRTEMFL == "Y"),
  ds_exposure_end_fallback_subjects = sum(r_adsl$SAFFL == "Y" & r_adsl$TRTEDTSRC == "DS_DISPOSITION_FALLBACK")
)

py_metrics <- jsonlite::fromJSON(file.path(out_dir, "metrics.json"), simplifyVector = TRUE)
for (nm in names(r_counts)) {
  py_val <- py_metrics[[nm]]
  r_val <- r_counts[[nm]]
  add_check(
    paste0("R independently reproduces ", nm),
    identical(as.integer(r_val), as.integer(py_val)),
    paste0("R=", r_val, "; Python=", py_val)
  )
}

# Independent any-TEAE risk differences.
safety <- r_adsl[r_adsl$SAFFL == "Y", c("USUBJID", "TRT01A"), drop = FALSE]
teae_ids <- unique(norm_chr(r_adae$USUBJID[r_adae$TRTEMFL == "Y"]))
safety$ANY_TEAE <- as.integer(norm_chr(safety$USUBJID) %in% teae_ids)
placebo <- safety[safety$TRT01A == "Placebo", , drop = FALSE]
if (nrow(placebo) == 0) stop("No placebo safety subjects in R reconstruction")

risk_rows <- list()
for (arm in c("Xanomeline Low Dose", "Xanomeline High Dose")) {
  g <- safety[safety$TRT01A == arm, , drop = FALSE]
  n1 <- nrow(g); e1 <- sum(g$ANY_TEAE)
  n0 <- nrow(placebo); e0 <- sum(placebo$ANY_TEAE)
  p1 <- e1 / n1; p0 <- e0 / n0
  rd <- p1 - p0
  se <- sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
  z <- qnorm(0.975)
  fp <- fisher.test(matrix(c(e1, n1 - e1, e0, n0 - e0), nrow = 2, byrow = TRUE))$p.value
  risk_rows[[length(risk_rows) + 1]] <- data.frame(
    comparison = paste0(arm, " vs Placebo"),
    n_arm = n1,
    n_placebo = n0,
    risk_arm = round(p1, 4),
    risk_placebo = round(p0, 4),
    risk_difference = round(rd, 4),
    ci95_lower = round(rd - z * se, 4),
    ci95_upper = round(rd + z * se, 4),
    fisher_p = round(fp, 6),
    stringsAsFactors = FALSE
  )
}
r_risk <- do.call(rbind, risk_rows)
py_risk <- read.csv(file.path(out_dir, "table7_teae_risk_difference.csv"), check.names = FALSE)
r_risk <- r_risk[order(r_risk$comparison), ]
py_risk <- py_risk[order(py_risk$comparison), ]
risk_num_cols <- c("n_arm", "n_placebo", "risk_arm", "risk_placebo", "risk_difference", "ci95_lower", "ci95_upper", "fisher_p")
risk_diff <- max(abs(as.matrix(r_risk[risk_num_cols]) - as.matrix(py_risk[risk_num_cols])), na.rm = TRUE)
add_check(
  "R independently reproduces TEAE risk-difference table",
  identical(r_risk$comparison, py_risk$comparison) && risk_diff <= 1e-6,
  sprintf("max numeric difference=%.3g", risk_diff)
)

# Independent efficacy derivation from official QS Dataset-JSON.
qs <- read_dataset_json(file.path(cache_dir, "qs.json"))

# CIBIC selected analysis records.
q <- qs[upper_chr(qs$QSTESTCD) == "CIBIC", , drop = FALSE]
q$AVAL <- suppressWarnings(as.numeric(q$QSSTRESN))
q$ADY <- suppressWarnings(as.numeric(q$QSDY))
q$QSSEQ_NUM <- suppressWarnings(as.numeric(q$QSSEQ))
subj <- r_adsl[, c("STUDYID", "USUBJID", "TRT01P", "RANDFL", "COMPLFL"), drop = FALSE]
q <- merge(q, subj, by = c("STUDYID", "USUBJID"), all = FALSE)
q <- q[q$RANDFL == "Y" & !is.na(q$AVAL) & !is.na(q$ADY), , drop = FALSE]

windows <- list(
  list("Week 8", 8, 56, 2, 84),
  list("Week 16", 16, 112, 85, 140),
  list("Week 24", 24, 168, 141, Inf)
)

choose_cibic <- function(g, w) {
  avisit <- w[[1]]; avisitn <- w[[2]]; target <- w[[3]]; lo <- w[[4]]; hi <- w[[5]]
  if (is.infinite(hi)) actual <- g[g$ADY >= lo, , drop = FALSE] else actual <- g[g$ADY >= lo & g$ADY <= hi, , drop = FALSE]
  dtype <- ""
  if (nrow(actual) > 0) {
    actual$DIST <- abs(actual$ADY - target)
    actual <- actual[order(actual$DIST, actual$ADY, actual$QSSEQ_NUM), , drop = FALSE]
    chosen <- actual[1, , drop = FALSE]
  } else {
    prior <- g[g$ADY < lo, , drop = FALSE]
    if (nrow(prior) == 0) return(NULL)
    prior <- prior[order(prior$ADY, prior$QSSEQ_NUM), , drop = FALSE]
    chosen <- prior[nrow(prior), , drop = FALSE]
    dtype <- "LOCF"
  }
  data.frame(
    STUDYID = chosen$STUDYID,
    USUBJID = chosen$USUBJID,
    AVISIT = avisit,
    AVISITN = avisitn,
    AVAL = chosen$AVAL,
    DTYPE = dtype,
    QSSEQ = chosen$QSSEQ,
    stringsAsFactors = FALSE
  )
}

cibic_rows <- list()
for (g in split(q, interaction(q$STUDYID, q$USUBJID, drop = TRUE))) {
  g <- g[order(g$ADY, g$QSSEQ_NUM), , drop = FALSE]
  for (w in windows) {
    rr <- choose_cibic(g, w)
    if (!is.null(rr)) cibic_rows[[length(cibic_rows) + 1]] <- rr
  }
}
r_cibic <- do.call(rbind, cibic_rows)
py_cibic <- read.csv(file.path(out_dir, "adqscibc_style.csv"), na.strings = c("", "NA"), check.names = FALSE)

cib_key <- function(df) paste(norm_chr(df$STUDYID), norm_chr(df$USUBJID), norm_chr(df$AVISIT), sep = "|")
r_cibic$key <- cib_key(r_cibic)
py_cibic$key <- cib_key(py_cibic)
r_cibic <- r_cibic[order(r_cibic$key), ]
py_cibic <- py_cibic[order(py_cibic$key), ]
keys_equal <- identical(r_cibic$key, py_cibic$key)
seq_equal <- keys_equal && all(same_num(r_cibic$QSSEQ, py_cibic$QSSEQ, 0))
dtype_equal <- keys_equal && identical(norm_chr(r_cibic$DTYPE), norm_chr(py_cibic$DTYPE))
aval_equal <- keys_equal && all(same_num(r_cibic$AVAL, py_cibic$AVAL, 1e-12))
add_check("R CIBIC selected analysis keys match Python", keys_equal, paste0("R rows=", nrow(r_cibic), "; Python rows=", nrow(py_cibic)))
add_check("R CIBIC QSSEQ selection matches Python", seq_equal, paste0("match=", seq_equal))
add_check("R CIBIC DTYPE classification matches Python", dtype_equal, paste0("match=", dtype_equal))
add_check("R CIBIC source-derived AVAL matches Python", aval_equal, paste0("match=", aval_equal))

# ACTOT long-form baseline/change reconstruction.
a <- qs[upper_chr(qs$QSTESTCD) == "ACTOT", , drop = FALSE]
a$AVAL <- suppressWarnings(as.numeric(a$QSSTRESN))
a$ADY <- suppressWarnings(as.numeric(a$QSDY))
a$QSSEQ_NUM <- suppressWarnings(as.numeric(a$QSSEQ))
subj2 <- r_adsl[, c("STUDYID", "USUBJID", "TRT01A", "RANDFL"), drop = FALSE]
a <- merge(a, subj2, by = c("STUDYID", "USUBJID"), all = FALSE)
a <- a[a$RANDFL == "Y" & !is.na(a$AVAL), , drop = FALSE]

actot_rows <- list()
for (g in split(a, interaction(a$STUDYID, a$USUBJID, drop = TRUE))) {
  g <- g[order(g$ADY, g$QSSEQ_NUM), , drop = FALSE]
  b <- g[upper_chr(g$QSBLFL) == "Y", , drop = FALSE]
  if (nrow(b) == 0) next
  b <- b[order(b$ADY, b$QSSEQ_NUM), , drop = FALSE]
  base <- b$AVAL[nrow(b)]
  ablfl <- ifelse(upper_chr(g$QSBLFL) == "Y", "Y", "")
  has_post <- any(ablfl != "Y" & !is.na(g$AVAL))
  actot_rows[[length(actot_rows) + 1]] <- data.frame(
    STUDYID = g$STUDYID,
    USUBJID = g$USUBJID,
    TRT01A = g$TRT01A,
    AVISIT = g$VISIT,
    ADY = g$ADY,
    AVAL = g$AVAL,
    BASE = base,
    CHG = ifelse(ablfl == "Y", 0, g$AVAL - base),
    ABLFL = ablfl,
    EFFFL = ifelse(!is.na(base) && has_post, "Y", "N"),
    QSSEQ = g$QSSEQ,
    stringsAsFactors = FALSE
  )
}
r_actot <- do.call(rbind, actot_rows)
py_actot <- read.csv(file.path(out_dir, "adqs_actot_style.csv"), na.strings = c("", "NA"), check.names = FALSE)
actot_key <- function(df) paste(norm_chr(df$STUDYID), norm_chr(df$USUBJID), norm_chr(df$QSSEQ), sep = "|")
r_actot$key <- actot_key(r_actot)
py_actot$key <- actot_key(py_actot)
r_actot <- r_actot[order(r_actot$key), ]
py_actot <- py_actot[order(py_actot$key), ]
actot_keys_equal <- identical(r_actot$key, py_actot$key)
actot_values_equal <- actot_keys_equal && all(same_num(r_actot$AVAL, py_actot$AVAL, 1e-12)) &&
  all(same_num(r_actot$BASE, py_actot$BASE, 1e-12)) && all(same_num(r_actot$CHG, py_actot$CHG, 1e-12))
actot_flags_equal <- actot_keys_equal && identical(norm_chr(r_actot$ABLFL), norm_chr(py_actot$ABLFL)) &&
  identical(norm_chr(r_actot$EFFFL), norm_chr(py_actot$EFFFL))
add_check("R ACTOT source-row keys match Python", actot_keys_equal, paste0("R rows=", nrow(r_actot), "; Python rows=", nrow(py_actot)))
add_check("R ACTOT AVAL/BASE/CHG match Python", actot_values_equal, paste0("match=", actot_values_equal))
add_check("R ACTOT baseline/efficacy flags match Python", actot_flags_equal, paste0("match=", actot_flags_equal))

# Independent ACTOT Week-24 observed and LOCF analysis subjects.
expected_arms <- c("Placebo", "Xanomeline Low Dose", "Xanomeline High Dose")
x <- r_actot[r_actot$EFFFL == "Y" & r_actot$TRT01A %in% expected_arms, , drop = FALSE]
base_rows <- x[x$ABLFL == "Y", c("STUDYID", "USUBJID", "TRT01A", "BASE"), drop = FALSE]
base_rows <- base_rows[!duplicated(paste(base_rows$STUDYID, base_rows$USUBJID)), , drop = FALSE]

pick_last <- function(df) {
  out <- lapply(split(df, interaction(df$STUDYID, df$USUBJID, drop = TRUE)), function(g) {
    g <- g[order(g$ADY), , drop = FALSE]
    g[nrow(g), , drop = FALSE]
  })
  do.call(rbind, out)
}

obs_src <- x[upper_chr(x$AVISIT) == "WEEK 24", c("STUDYID", "USUBJID", "AVAL", "ADY", "AVISIT"), drop = FALSE]
obs_src <- pick_last(obs_src)
obs <- merge(base_rows, obs_src, by = c("STUDYID", "USUBJID"), all = FALSE)
obs$DTYPE <- ""
obs$CHG <- obs$AVAL - obs$BASE

locf_src <- x[x$ABLFL != "Y" & x$ADY > 1 & x$ADY <= 168, c("STUDYID", "USUBJID", "AVAL", "ADY", "AVISIT"), drop = FALSE]
locf_src <- pick_last(locf_src)
locf <- merge(base_rows, locf_src, by = c("STUDYID", "USUBJID"), all = FALSE)
locf$DTYPE <- ifelse(upper_chr(locf$AVISIT) == "WEEK 24", "", "LOCF")
locf$CHG <- locf$AVAL - locf$BASE

fit_ancova <- function(d, label) {
  d <- d[complete.cases(d[, c("AVAL", "BASE", "TRT01A")]), , drop = FALSE]
  mean_base <- mean(d$BASE)
  d$BASEC <- d$BASE - mean_base
  d$LOW <- as.numeric(d$TRT01A == "Xanomeline Low Dose")
  d$HIGH <- as.numeric(d$TRT01A == "Xanomeline High Dose")
  fit <- lm(AVAL ~ LOW + HIGH + BASEC, data = d)
  sm <- summary(fit)$coefficients
  df <- df.residual(fit)
  tcrit <- qt(0.975, df)
  out <- lapply(c("LOW", "HIGH"), function(term) {
    arm <- if (term == "LOW") "Xanomeline Low Dose" else "Xanomeline High Dose"
    est <- unname(coef(fit)[term])
    se <- sm[term, "Std. Error"]
    p <- sm[term, "Pr(>|t|)"]
    data.frame(
      analysis = label,
      comparison = paste0(arm, " vs Placebo"),
      n_total = nrow(d),
      estimate = est,
      se = se,
      ci95_lower = est - tcrit * se,
      ci95_upper = est + tcrit * se,
      p_value = p,
      df = df,
      baseline_reference = mean_base,
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, out)
}

r_contrasts <- rbind(
  fit_ancova(obs, "Observed Week 24"),
  fit_ancova(locf, "LOCF sensitivity")
)
py_contrasts <- read.csv(file.path(out_dir, "table10_actot_ancova_contrasts.csv"), check.names = FALSE)
contrast_key <- function(df) paste(df$analysis, df$comparison, sep = "|")
r_contrasts$key <- contrast_key(r_contrasts)
py_contrasts$key <- contrast_key(py_contrasts)
r_contrasts <- r_contrasts[order(r_contrasts$key), ]
py_contrasts <- py_contrasts[order(py_contrasts$key), ]
contrast_keys_equal <- identical(r_contrasts$key, py_contrasts$key)
contrast_cols <- c("estimate", "se", "ci95_lower", "ci95_upper", "p_value", "baseline_reference")
max_ancova_diff <- if (contrast_keys_equal) {
  max(abs(as.matrix(r_contrasts[contrast_cols]) - as.matrix(py_contrasts[contrast_cols])), na.rm = TRUE)
} else Inf
ancova_n_df_equal <- contrast_keys_equal && all(r_contrasts$n_total == py_contrasts$n_total) && all(r_contrasts$df == py_contrasts$df)
add_check("R ANCOVA contrast keys/N/df match Python", ancova_n_df_equal, paste0("observed N=", nrow(obs), "; LOCF N=", nrow(locf)))
add_check("R ANCOVA estimates/SE/CI/p match Python", contrast_keys_equal && max_ancova_diff <= 1e-8, sprintf("max numeric difference=%.3g", max_ancova_diff))

# Persist independent QC evidence and fail on required discrepancies.
qc <- add_check(get = TRUE)
write.csv(qc, file.path(out_dir, "r_independent_qc.csv"), row.names = FALSE, na = "")
write.csv(r_contrasts[, setdiff(names(r_contrasts), "key")], file.path(out_dir, "r_actot_ancova_contrasts.csv"), row.names = FALSE, na = "")
write.csv(r_risk, file.path(out_dir, "r_teae_risk_difference.csv"), row.names = FALSE, na = "")

r_metrics <- list(
  analysis_version = "0.4.0",
  r_version = R.version.string,
  jsonlite_version = as.character(utils::packageVersion("jsonlite")),
  independent_counts = r_counts,
  cdisc_qs_rows = nrow(qs),
  r_cibic_rows = nrow(r_cibic),
  r_actot_rows = nrow(r_actot),
  observed_week24_n = nrow(obs),
  locf_week24_n = nrow(locf),
  required_checks = sum(qc$required),
  required_passed = sum(qc$required & qc$passed),
  all_required_passed = all(qc$passed[qc$required])
)
jsonlite::write_json(r_metrics, file.path(out_dir, "r_metrics.json"), pretty = TRUE, auto_unbox = TRUE, na = "null")
writeLines(capture.output(sessionInfo()), file.path(out_dir, "r_session_info.txt"))

summary_lines <- c(
  "# Independent R QC summary",
  "",
  paste0("- R version: ", R.version.string),
  paste0("- jsonlite: ", as.character(utils::packageVersion("jsonlite"))),
  paste0("- Required cross-language checks: ", r_metrics$required_passed, "/", r_metrics$required_checks, " passed."),
  paste0("- Independent safety counts: randomised=", r_counts$randomized_subjects,
         ", safety=", r_counts$safety_subjects,
         ", subjects with TEAE=", r_counts$subjects_with_teae,
         ", TEAE events=", r_counts$teae_events, "."),
  paste0("- CIBIC selected rows reconstructed in R: ", nrow(r_cibic), "."),
  paste0("- ACTOT source rows reconstructed in R: ", nrow(r_actot), "."),
  paste0("- ACTOT ANCOVA subjects: observed Week 24=", nrow(obs), "; LOCF=", nrow(locf), "."),
  sprintf("- Maximum R/Python ANCOVA numeric difference: %.3g.", max_ancova_diff),
  "",
  "R code independently re-derives the analysis inputs from the same public raw sources; Python outputs are read only for the final cross-language comparison."
)
writeLines(summary_lines, file.path(out_dir, "r_independent_qc_summary.md"))
cat(paste(summary_lines, collapse = "\n"), "\n")

if (!all(qc$passed[qc$required])) {
  print(qc[qc$required & !qc$passed, , drop = FALSE])
  stop("Independent R QC failed; see outputs/r_independent_qc.csv")
}
