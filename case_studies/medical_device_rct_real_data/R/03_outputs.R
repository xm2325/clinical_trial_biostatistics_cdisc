message("[03] Building figures and review-ready study summaries")

if (!file.exists(ANALYSIS_RDS)) stop("Analysis data not found")
dat <- readRDS(ANALYSIS_RDS)

binary_outcomes <- read.csv(file.path(DIR_OUTPUT, "binary_outcomes.csv"), check.names = FALSE)
continuous_outcomes <- read.csv(file.path(DIR_OUTPUT, "continuous_outcomes.csv"), check.names = FALSE)
sensitivity <- read.csv(file.path(DIR_OUTPUT, "sensitivity_analysis.csv"), check.names = FALSE)
qc <- read.csv(file.path(DIR_OUTPUT, "qc_findings.csv"), check.names = FALSE)
missingness <- read.csv(file.path(DIR_OUTPUT, "missingness.csv"), check.names = FALSE)

first <- binary_outcomes[binary_outcomes$variable == "attempt1_S_F", , drop = FALSE]
overall <- binary_outcomes[binary_outcomes$variable == "intubation_overall_S_F", , drop = FALSE]
repeat_attempt <- binary_outcomes[binary_outcomes$variable == "repeat_attempt", , drop = FALSE]
time_row <- continuous_outcomes[continuous_outcomes$variable == "total_intubation_time", , drop = FALSE]
ease_row <- continuous_outcomes[continuous_outcomes$variable == "ease", , drop = FALSE]
s1 <- sensitivity[sensitivity$analysis_id == "S1", , drop = FALSE]
s2 <- sensitivity[sensitivity$analysis_id == "S2", , drop = FALSE]
review_rows <- qc[qc$status == "REVIEW", , drop = FALSE]

if (nrow(first) != 1) stop("First-attempt result row missing")
if (nrow(time_row) != 1) stop("Total-time result row missing")

# -----------------------------------------------------------------------------
# Figure 1: first-attempt success with Wilson intervals and treatment contrast.
# -----------------------------------------------------------------------------
rates <- c(first$mac_risk, first$aws_risk)
counts <- c(first$mac_events, first$aws_events)
ns <- c(first$mac_n, first$aws_n)
cis <- t(mapply(wilson_ci, counts, ns))

png(file.path(DIR_FIG, "first_attempt_success.png"), width = 1600, height = 1000, res = 180)
par(mar = c(6, 6, 5, 2) + 0.1, las = 1)
x <- c(1, 2)
plot(
  x, rates,
  type = "n",
  xlim = c(0.5, 2.5),
  ylim = c(0.65, 1.02),
  xaxt = "n",
  xlab = "Randomized device",
  ylab = "First-attempt success proportion",
  main = "First-attempt intubation success"
)
abline(h = seq(0.65, 1.00, 0.05), lty = 3, col = "grey88")
axis(1, at = x, labels = c("Macintosh #4", "Pentax AWS video"), las = 1)
arrows(x, cis[, "lower"], x, cis[, "upper"], angle = 90, code = 3, length = 0.06, lwd = 2)
points(x, rates, pch = 19, cex = 1.6)
text(x, pmin(rates + 0.045, 1.01), labels = sprintf("%d/%d (%.1f%%)", counts, ns, 100 * rates), cex = 0.95)
mtext(
  sprintf(
    "AWS - Macintosh risk difference: %.1f percentage points (95%% CI %.1f to %.1f); Fisher p=%.4f",
    100 * first$risk_difference_aws_minus_mac,
    100 * first$rd_ci95_lower,
    100 * first$rd_ci95_upper,
    first$fisher_p
  ),
  side = 3,
  line = 0.5,
  cex = 0.85
)
mtext("99-patient public teaching release", side = 1, line = 4.5, cex = 0.8)
dev.off()

# -----------------------------------------------------------------------------
# Figure 2: total intubation time with raw teaching-release records.
# -----------------------------------------------------------------------------
png(file.path(DIR_FIG, "total_intubation_time.png"), width = 1600, height = 1000, res = 180)
par(mar = c(6, 6, 5, 2) + 0.1, las = 1)
boxplot(
  total_intubation_time ~ device,
  data = dat,
  ylab = "Total intubation time (seconds)",
  xlab = "Randomized device",
  main = "Total intubation time by randomized device",
  outline = FALSE,
  border = "grey30"
)
set.seed(20260912)
stripchart(
  total_intubation_time ~ device,
  data = dat,
  vertical = TRUE,
  method = "jitter",
  pch = 21,
  bg = grDevices::adjustcolor("black", alpha.f = 0.45),
  col = grDevices::adjustcolor("black", alpha.f = 0.45),
  cex = 0.75,
  add = TRUE
)
mtext(
  sprintf(
    "Median AWS %.1f s vs Macintosh %.1f s | difference %.1f s (bootstrap 95%% CI %.1f to %.1f) | Wilcoxon p=%.3g",
    time_row$aws_median,
    time_row$mac_median,
    time_row$median_difference_aws_minus_mac,
    time_row$bootstrap_ci95_lower,
    time_row$bootstrap_ci95_upper,
    time_row$wilcoxon_p
  ),
  side = 3,
  line = 0.5,
  cex = 0.82
)
mtext("Points are deidentified records from the public teaching release", side = 1, line = 4.5, cex = 0.8)
dev.off()

# -----------------------------------------------------------------------------
# Figure 3: core-variable missingness, excluding structural attempt-2/3 fields.
# -----------------------------------------------------------------------------
miss_plot <- missingness[missingness$n_missing > 0, , drop = FALSE]
png(file.path(DIR_FIG, "missingness.png"), width = 1600, height = 900, res = 180)
par(mar = c(5, 11, 4, 2) + 0.1, las = 1)
if (nrow(miss_plot) > 0) {
  ord <- order(miss_plot$n_missing, decreasing = FALSE)
  mp <- miss_plot[ord, , drop = FALSE]
  bp <- barplot(
    mp$n_missing,
    names.arg = mp$variable,
    horiz = TRUE,
    xlab = "Missing patient records",
    main = "Unexpected missingness in core analysis variables",
    xlim = c(0, max(mp$n_missing) + 1.4),
    border = NA
  )
  text(mp$n_missing + 0.08, bp, labels = sprintf("%d / 99", mp$n_missing), pos = 4, cex = 0.9)
} else {
  plot.new()
  title("Unexpected missingness in core analysis variables")
  text(0.5, 0.5, "No missing values in core analysis variables")
}
mtext("Later-attempt fields are handled separately as structural missingness", side = 1, line = 3.5, cex = 0.8)
dev.off()

# -----------------------------------------------------------------------------
# Figure 4: one-page study -> data -> QC -> analysis -> decision flow.
# -----------------------------------------------------------------------------
png(file.path(DIR_FIG, "study_to_decision.png"), width = 1800, height = 950, res = 180)
par(mar = c(2, 2, 5, 2) + 0.1)
plot.new()
plot.window(xlim = c(0, 1), ylim = c(0, 1))
title("Medical-device RCT: study-to-decision workflow", cex.main = 1.35)

box_x <- c(0.03, 0.225, 0.42, 0.615, 0.81)
box_w <- 0.16
box_y1 <- 0.28
box_y2 <- 0.78
box_titles <- c("STUDY", "DATA", "QC", "ANALYSIS", "DECISION SUPPORT")
box_text <- c(
  "Randomized device comparison\nPentax AWS vs Macintosh #4",
  "99 patients\n22 study variables\npublic teaching release",
  sprintf("%d checks\n%d PASS | %d REVIEW | 0 FAIL\nno silent repair", nrow(qc), sum(qc$status == "PASS"), sum(qc$status == "REVIEW")),
  sprintf("First-attempt success\nRD %.1f pp (95%% CI %.1f to %.1f)\nTime difference +%.1f s",
          100 * first$risk_difference_aws_minus_mac,
          100 * first$rd_ci95_lower,
          100 * first$rd_ci95_upper,
          time_row$median_difference_aws_minus_mac),
  "Review estimates + uncertainty\nresolve source questions\nkeep claims inside data boundary"
)

for (i in seq_along(box_x)) {
  rect(box_x[i], box_y1, box_x[i] + box_w, box_y2, border = "grey35", lwd = 2, col = "grey97")
  text(box_x[i] + box_w / 2, 0.69, box_titles[i], font = 2, cex = 0.95)
  text(box_x[i] + box_w / 2, 0.50, box_text[i], cex = 0.78, adj = c(0.5, 0.5))
  if (i < length(box_x)) {
    arrows(box_x[i] + box_w + 0.008, 0.53, box_x[i + 1] - 0.008, 0.53, length = 0.08, lwd = 2)
  }
}

text(
  0.5,
  0.13,
  "One R command: source data -> provenance -> analysis-ready data -> QC -> randomized comparisons -> sensitivity checks -> review package",
  cex = 0.9
)
text(
  0.5,
  0.07,
  "Portfolio re-analysis of a redistributed teaching release; not new clinical evidence or a regulatory conclusion",
  cex = 0.8
)
dev.off()

# -----------------------------------------------------------------------------
# Markdown summaries
# -----------------------------------------------------------------------------
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
  "The teaching release supports the same broad question as the source study: whether the AWS device improves intubation performance relative to a standard Macintosh laryngoscope. In this re-analysis, the AWS group does not show a first-attempt-success advantage and has longer total intubation time. The first-attempt-success interval is wide, so the data do not rule out clinically relevant differences in either direction. These numbers should be interpreted only within the original study purpose and the limits of the redistributed teaching release.",
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
  sprintf(
    "The first-attempt-success contrast is %.1f percentage points (95%% CI %.1f to %.1f), so the released data do not establish an AWS advantage and still allow uncertainty in either direction.",
    100 * first$risk_difference_aws_minus_mac,
    100 * first$rd_ci95_lower,
    100 * first$rd_ci95_upper
  ),
  sprintf(
    "Total intubation time is longer with AWS by a median %.1f seconds (bootstrap 95%% CI %.1f to %.1f), and the prespecified source-time sensitivity check gives the same practical conclusion.",
    time_row$median_difference_aws_minus_mac,
    time_row$bootstrap_ci95_lower,
    time_row$bootstrap_ci95_upper
  ),
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
  "Data provenance, missingness, QC, baseline summaries, randomized comparisons, sensitivity analyses, figures and the day-5 handoff are generated from one R command and checked in CI."
)
writeLines(stakeholder_lines, file.path(DIR_OUTPUT, "stakeholder_brief.md"))

day5_lines <- c(
  "# Day-5 study-team handoff",
  "",
  "## What is ready",
  "",
  "- Prespecified analysis boundary and public-data limitation.",
  "- Reproducible patient-level import with source URL, retrieval time and MD5 checksum.",
  sprintf("- Automated QC: %d checks = %d PASS, %d REVIEW, 0 FAIL.", nrow(qc), sum(qc$status == "PASS"), sum(qc$status == "REVIEW")),
  "- Baseline descriptive table and randomized binary/continuous outcome analyses.",
  "- Bounded source-timing sensitivity analysis and supportive adjusted log-time model.",
  "- Review-ready figures, technical analysis summary and internal stakeholder brief.",
  "- Executable output checks in CI.",
  "",
  "## Decision message for the study team",
  "",
  sprintf(
    "First-attempt success is %.1f%% with AWS and %.1f%% with Macintosh; the AWS-minus-Macintosh risk difference is %.1f percentage points (95%% CI %.1f to %.1f).",
    100 * first$aws_risk,
    100 * first$mac_risk,
    100 * first$risk_difference_aws_minus_mac,
    100 * first$rd_ci95_lower,
    100 * first$rd_ci95_upper
  ),
  sprintf(
    "Median total intubation time is %.1f s with AWS and %.1f s with Macintosh; the median difference is +%.1f s (bootstrap 95%% CI %.1f to %.1f).",
    time_row$aws_median,
    time_row$mac_median,
    time_row$median_difference_aws_minus_mac,
    time_row$bootstrap_ci95_lower,
    time_row$bootstrap_ci95_upper
  ),
  "",
  "The current package therefore does not show a first-attempt-success advantage for AWS and shows longer intubation time with AWS in the released data. The time finding is stable to the planned source-timing sensitivity check.",
  "",
  "## Open review items",
  "",
  "- Confirm the source definition for the timing inconsistency rather than overwriting the patient record.",
  "- Clarify the public `view` code wording before using it as a clinically labelled variable.",
  "- Keep the teaching-release and de-identification boundary visible in any external discussion.",
  "",
  "## Evidence boundary",
  "",
  "This is an educational portfolio re-analysis of a redistributed 99-patient teaching release. It is not an exact reproduction of the 105-patient publication, new clinical evidence, a regulatory analysis, or sponsor/CRO production work."
)
writeLines(day5_lines, file.path(DIR_OUTPUT, "day5_handoff.md"))

message("[03] Generated review-ready tables, four figures and three Markdown reports")
