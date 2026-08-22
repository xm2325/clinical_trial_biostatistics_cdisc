options(stringsAsFactors = FALSE)

if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required")

out_dir <- "outputs"
spec <- jsonlite::fromJSON("spec/mi_sensitivity.json", simplifyVector = FALSE)
mar_path <- file.path(out_dir, "table20_rbmi_mar_pairwise.csv")
if (!file.exists(mar_path)) stop("Missing rbmi MAR output: ", mar_path)

mar <- read.csv(mar_path, check.names = FALSE)
required_cols <- c("comparison_id", "SE", "mcse_estimate", "mcse_se", "imputations", "pool_method")
missing_cols <- setdiff(required_cols, names(mar))
if (length(missing_cols) > 0) stop("MAR output missing columns: ", paste(missing_cols, collapse = ", "))

threshold <- as.numeric(spec$imputation$max_mcse_estimate_to_se_ratio)
requested <- as.integer(spec$imputation$n_imputations)
mar$mcse_estimate_to_se_ratio <- mar$mcse_estimate / mar$SE
mar$mcse_se_to_se_ratio <- mar$mcse_se / mar$SE

checks <- list()
add_check <- function(name, passed, detail) {
  checks[[length(checks) + 1]] <<- data.frame(
    check = name,
    passed = isTRUE(passed),
    required = TRUE,
    detail = detail,
    stringsAsFactors = FALSE
  )
}

add_check("MAR precision gate sees two controlled pairwise comparisons", nrow(mar) == 2 && length(unique(mar$comparison_id)) == 2, paste0("rows=", nrow(mar)))
add_check("MAR precision gate sees requested imputation count", all(mar$imputations == requested), paste0("pooled_N=", paste(unique(mar$imputations), collapse = ","), "; requested=", requested))
add_check("MAR precision gate sees Rubin pooling", all(mar$pool_method == "rubin"), paste0("pool_method=", paste(unique(mar$pool_method), collapse = ",")))
finite <- all(is.finite(mar$SE)) && all(mar$SE > 0) && all(is.finite(mar$mcse_estimate)) && all(is.finite(mar$mcse_se))
add_check("MAR Monte Carlo precision diagnostics are finite", finite, paste0("finite=", finite))
ratio_ok <- finite && all(mar$mcse_estimate_to_se_ratio <= threshold)
add_check("MAR MCSE estimate-to-SE ratio meets controlled threshold", ratio_ok, paste0("max_ratio=", sprintf("%.6f", max(mar$mcse_estimate_to_se_ratio, na.rm = TRUE)), "; threshold=", sprintf("%.6f", threshold)))

qc <- do.call(rbind, checks)
write.csv(mar[, c("comparison_id", "SE", "mcse_estimate", "mcse_se", "mcse_estimate_to_se_ratio", "mcse_se_to_se_ratio", "imputations", "pool_method")], file.path(out_dir, "rbmi_mcse_diagnostics.csv"), row.names = FALSE, na = "")
write.csv(qc, file.path(out_dir, "rbmi_mcse_qc.csv"), row.names = FALSE, na = "")

all_passed <- all(qc$passed)
metrics <- list(
  analysis_version = "0.13.0",
  requested_imputations = requested,
  comparisons = nrow(mar),
  max_mcse_estimate_to_se_ratio = if (finite) max(mar$mcse_estimate_to_se_ratio) else NULL,
  controlled_threshold = threshold,
  required_checks = nrow(qc),
  required_passed = sum(qc$passed),
  all_required_passed = all_passed
)
jsonlite::write_json(metrics, file.path(out_dir, "rbmi_mcse_metrics.json"), pretty = TRUE, auto_unbox = TRUE, na = "null")

cat("# rbmi Monte Carlo precision QC\n\n")
for (i in seq_len(nrow(mar))) {
  cat(sprintf("- %s: MCSE(est)=%.6f; SE=%.6f; ratio=%.2f%%.\n", mar$comparison_id[i], mar$mcse_estimate[i], mar$SE[i], 100 * mar$mcse_estimate_to_se_ratio[i]))
}
cat(sprintf("- Controlled maximum MCSE(est)/SE: %.2f%%.\n", 100 * threshold))
cat(sprintf("- Required QC: %d/%d passed.\n", sum(qc$passed), nrow(qc)))

if (!all_passed) stop("rbmi Monte Carlo precision QC failed; inspect outputs/rbmi_mcse_qc.csv")
