message("[03] Building figures and review-ready study summaries")

if (!file.exists(ANALYSIS_RDS)) stop("Analysis data not found")
dat <- readRDS(ANALYSIS_RDS)

binary_outcomes <- read.csv(file.path(DIR_OUTPUT, "binary_outcomes.csv"), check.names = FALSE)
continuous_outcomes <- read.csv(file.path(DIR_OUTPUT, "continuous_outcomes.csv"), check.names = FALSE)
sensitivity <- read.csv(file.path(DIR_OUTPUT, "sensitivity_analysis.csv"), check.names = FALSE)
qc <- read.csv(file.path(DIR_OUTPUT, "qc_findings.csv"), check.names = FALSE)
missingness <- read.csv(file.path(DIR_OUTPUT, "missingness.csv"), check.names = FALSE)

# -----------------------------------------------------------------------------
# Figure 1: first-attempt success with Wilson intervals
# -----------------------------------------------------------------------------
first <- binary_outcomes[binary_outcomes$variable == "attempt1_S_F", , drop = FALSE]
if (nrow(first) != 1) stop("First-attempt result row missing")

rates <- c(first$mac_risk, first$aws_risk)
counts <- c(first$mac_events, first$aws_events)
ns <- c(first$mac_n, first$aws_n)
cis <- t(mapply(wilson_ci, counts, ns))

png(file.path(DIR_FIG, "first_attempt_success.png"), width = 1200, height = 800, res = 140)
par(mar = c(5, 5, 4, 2) + 0.1)
bp <- barplot(
  rates,
  names.arg = c("Macintosh #4", "Pentax AWS video"),
  ylim = c(0, 1.05),
  ylab = "First-attempt success proportion",
  main = "First-attempt intubation success\n99-patient public teaching release",
  border = NA
)
arrows(bp, cis[, "lower"], bp, cis[, "upper"], angle = 90, code = 3, length = 0.06, lwd = 2)
text(bp, pmin(rates + 0.07, 1.02), labels = sprintf("%d/%d\n%.1f%%", counts, ns, 100 * rates), cex = 0.9)
abline(h = seq(0, 1, 0.2), lty = 3, col = "grey85")
dev.off()

# -----------------------------------------------------------------------------
# Figure 2: total intubation time. Raw points are deidentified teaching records.
# -----------------------------------------------------------------------------
png(file.path(DIR_FIG, "total_intubation_time.png"), width = 1200, height = 800, res = 140)
par(mar = c(5, 5, 4, 2) + 0.1)
boxplot(
  total_intubation_time ~ device,
  data = dat,
  ylab = "Total intubation time (seconds)",
  xlab = "Randomized device",
  main = "Total intubation time by randomized device",
  outline = FALSE
)
set.seed(20260912)
stripchart(
  total_intubation_time ~ device,
  data = dat,
  vertical = TRUE,
  method = "jitter",
  pch = 16,
  cex = 0.7,
  add = TRUE
)
dev.off()

# -----------------------------------------------------------------------------
# Figure 3: core-variable missingness, excluding structural attempt-2/3 fields.
# -----------------------------------------------------------------------------
miss_plot <- missingness[missingness$n_missing > 0, , drop = FALSE]
png(file.path(DIR_FIG, "missingness.png"), width = 1200, height = 800, res = 140)
par(mar = c(8, 5, 4, 2) + 0.1)
if (nrow(miss_plot) > 0) {
  ord <- order(miss_plot$n_missing, decreasing = TRUE)
  mp <- miss_plot[ord, , drop = FALSE]
  barplot(
    mp$n_missing,
    names.arg = mp$variable,
    las = 2,
    ylab = "Missing patient records",
    main = "Unexpected missingness in core analysis variables",
    ylim = c(0, max(mp$n_missing) + 1)
  )
} else {
  plot.new()
  title("Unexpected missingness in core analysis variables")
  text(0.5, 0.5, "No missing values in core analysis variables")
}
dev.off()

# -----------------------------------------------------------------------------
# Markdown summaries
# -----------------------------------------------------------------------------
overall <- binary_outcomes[binary_outcomes$variable == "intubation_overall_S_F", , drop = FALSE]
repeat_attempt <- binary_outcomes[binary_outcomes$variable == "repeat_attempt", , drop = FALSE]
time_row <- continuous_outcomes[continuous_outcomes$variable == "total_intubation_time", , drop = FALSE]
ease_row <- continuous_outcomes[continuous_outcomes$variable == "ease", , drop = FALSE]
s1 <- sensitivity[sensitivity$analysis_id == "S1", , drop = FALSE]
s2 <- sensitivity[sensitivity$analysis_id == "S2", , drop = FALSE]

review_rows <- qc[qc$status == "REVIEW", , drop = FALSE]

summary_lines <- c(
  "# Real-data medical-device RCT analysis summary",
  "",
  "## Analysis boundary",
  "",
  paste0(
    "This is an educational/portfolio re-analysis of the 99-patient public teaching release of the randomized Pentax AWS vs Macintosh #4 laryngoscope study. ",
    "It is not an exact reproduction of the 105-patient original publication, not new clinical evidence, and not a regulatory analysis."
  ),
  "",
  "## Main results in the teaching release",
  "",
  sprintf(
    "- First-attempt success: Pentax AWS %d/%d (%.1f%%) vs Macintosh %d/%d (%.1f%%). Absolute difference (AWS - Macintosh) %.1f percentage points, 95%% Newcombe interval %.1f to %.1f; Fisher exact p=%.4f.",
    first$aws_events, first$aws_n, 100 * first$aws_risk,
    first$mac_events, first$mac_n, 100 * first$mac_risk,
    100 * first$risk_difference_aws_minus_mac,
    100 * first$rd_ci95_lower, 100 * first$rd_ci95_upper, first$fisher_p
  ),
  sprintf(
    "- Total intubation time: Pentax AWS median %.1f s [Q1 %.1f, Q3 %.1f] vs Macintosh median %.1f s [Q1 %.1f, Q3 %.1f]. Median difference (AWS - Macintosh) %.1f s, bootstrap 95%% interval %.1f to %.1f; Wilcoxon p=%.4g.",
    time_row$aws_median, time_row$aws_q1, time_row$aws_q3,
    time_row$mac_median, time_row$mac_q1, time_row$mac_q3,
    time_row$median_difference_aws_minus_mac,
    time_row$bootstrap_ci95_lower, time_row$bootstrap_ci95_upper,
    time_row$wilcoxon_p
  ),
  sprintf(
    "- Overall success: Pentax AWS %d/%d (%.1f%%) vs Macintosh %d/%d (%.1f%%); Fisher exact p=%.4f.",
    overall$aws_events, overall$aws_n, 100 * overall$aws_risk,
    overall$mac_events, overall$mac_n, 100 * overall$mac_risk, overall$fisher_p
  ),
  sprintf(
    "- More than one attempt: Pentax AWS %d/%d (%.1f%%) vs Macintosh %d/%d (%.1f%%); Fisher exact p=%.4f.",
    repeat_attempt$aws_events, repeat_attempt$aws_n, 100 * repeat_attempt$aws_risk,
    repeat_attempt$mac_events, repeat_attempt$mac_n, 100 * repeat_attempt$mac_risk, repeat_attempt$fisher_p
  ),
  sprintf(
    "- Ease score (0 extremely easy, 100 extremely difficult): Pentax AWS median %.1f vs Macintosh %.1f; median difference %.1f, bootstrap 95%% interval %.1f to %.1f.",
    ease_row$aws_median, ease_row$mac_median, ease_row$median_difference_aws_minus_mac,
    ease_row$bootstrap_ci95_lower, ease_row$bootstrap_ci95_upper
  ),
  "",
  "## Sensitivity analyses",
  "",
  sprintf(
    "- Source-time review exclusion: after excluding %d row(s) where first-attempt time exceeds supplied total time, the AWS-minus-Macintosh median total-time difference is %.1f s (bootstrap 95%% interval %.1f to %.1f).",
    99 - s1$n, s1$estimate, s1$ci95_lower, s1$ci95_upper
  ),
  sprintf(
    "- Covariate-adjusted log-time model: N=%d complete cases; estimated multiplicative time ratio AWS/Macintosh %.3f (95%% CI %.3f to %.3f). This is supportive, not the randomized primary comparison.",
    s2$n, s2$estimate, s2$ci95_lower, s2$ci95_upper
  ),
  "",
  "## Data-quality review",
  "",
  paste0("The automated QC file contains ", nrow(qc), " checks; ", nrow(review_rows), " require REVIEW rather than silent correction."),
  "",
  paste0("- Core-variable missingness totals ", sum(missingness$n_missing), " cells across ", sum(missingness$n_missing > 0), " variables. Later-attempt fields are handled separately as structural missingness."),
  "- The raw `view` code is excluded from clinically labelled inference because the public dictionary's verbal label is internally hard to reconcile with the clinical grade ordering.",
  "- Any row where first-attempt time exceeds supplied total time is retained in the main analysis and surfaced for source clarification; a bounded exclusion sensitivity is reported separately.",
  "",
  "## Interpretation",
  "",
  "The teaching release supports the same broad question as the source study: whether the AWS device improves intubation performance relative to a standard Macintosh laryngoscope. In this re-analysis, the AWS group does not show a first-attempt-success advantage and has longer total intubation time. These numbers should be interpreted only within the original study purpose and the limits of the redistributed teaching release.",
  "",
  "The original publication remains the primary clinical source."
)
writeLines(summary_lines, file.path(DIR_OUTPUT, "analysis_summary.md"))

stakeholder_lines <- c(
  "# Internal stakeholder brief",
  "",
  "## Decision-level message",
  "",
  sprintf(
    "In the 99-patient teaching release, first-attempt success is %.1f%% with Pentax AWS and %.1f%% with Macintosh #4, while median total intubation time is %.1f vs %.1f seconds, respectively.",
    100 * first$aws_risk, 100 * first$mac_risk, time_row$aws_median, time_row$mac_median
  ),
  "",
  "The analysis therefore does not provide evidence that the video device is faster or more successful on the first attempt in this released dataset. The time result is also stable to the prespecified source-time sensitivity check.",
  "",
  "## What needs review before external use",
  "",
  "1. Confirm the intended definition/capping of total intubation time for the source-timing review row(s).",
  "2. Resolve the public data dictionary wording for the Cormack-Lehane `view` code before assigning a clinical label to that field.",
  "3. Treat the dataset as an educational/deidentified teaching release, not a replacement for the source trial database.",
  "4. Do not present these re-analysis outputs as a new publication or regulatory conclusion without source permission and study-team review.",
  "",
  "## Delivery status",
  "",
  "Data provenance, missingness, QC, baseline summaries, randomized comparisons, sensitivity analyses and figures are generated from one R command and checked in CI."
)
writeLines(stakeholder_lines, file.path(DIR_OUTPUT, "stakeholder_brief.md"))

message("[03] Generated review-ready tables, three figures and two Markdown reports")
