message("[04] Refining recruiter-facing delivery visuals")

# Rebuild the missingness figure with more space for the explanatory footer.
miss_plot <- missingness[missingness$n_missing > 0, , drop = FALSE]
png(file.path(DIR_FIG, "missingness.png"), width = 1600, height = 950, res = 180)
par(mar = c(7, 11, 4, 2) + 0.1, las = 1)
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
mtext("Later-attempt fields are handled separately as structural missingness", side = 1, line = 5.1, cex = 0.75)
dev.off()

# Rebuild the one-page flow with short line lengths so every box can be read at a glance.
png(file.path(DIR_FIG, "study_to_decision.png"), width = 1900, height = 1000, res = 180)
par(mar = c(2, 2, 5, 2) + 0.1)
plot.new()
plot.window(xlim = c(0, 1), ylim = c(0, 1))
title("Medical-device RCT: study-to-decision workflow", cex.main = 1.35)

box_x <- c(0.025, 0.22, 0.415, 0.61, 0.805)
box_w <- 0.17
box_y1 <- 0.27
box_y2 <- 0.79
box_titles <- c("STUDY", "DATA", "QC", "ANALYSIS", "DECISION\nSUPPORT")
box_text <- c(
  "Randomized comparison\nPentax AWS video\nvs Macintosh #4",
  "99 patients\n22 variables\npublic teaching release",
  sprintf("%d checks\n%d PASS\n%d REVIEW\n0 FAIL", nrow(qc), sum(qc$status == "PASS"), sum(qc$status == "REVIEW")),
  sprintf("Success RD %.1f pp\n95%% CI %.1f to %.1f\nTime difference +%.1f s",
          100 * first$risk_difference_aws_minus_mac,
          100 * first$rd_ci95_lower,
          100 * first$rd_ci95_upper,
          time_row$median_difference_aws_minus_mac),
  "Review estimate\nand uncertainty\nResolve source questions\nRespect data boundary"
)

for (i in seq_along(box_x)) {
  rect(box_x[i], box_y1, box_x[i] + box_w, box_y2, border = "grey35", lwd = 2, col = "grey97")
  text(box_x[i] + box_w / 2, 0.69, box_titles[i], font = 2, cex = 0.88)
  text(box_x[i] + box_w / 2, 0.49, box_text[i], cex = 0.66, adj = c(0.5, 0.5))
  if (i < length(box_x)) {
    arrows(box_x[i] + box_w + 0.006, 0.53, box_x[i + 1] - 0.006, 0.53, length = 0.07, lwd = 2)
  }
}

text(
  0.5,
  0.13,
  "One R command builds provenance, QC, randomized analyses, sensitivity checks and a review package.",
  cex = 0.82
)
text(
  0.5,
  0.075,
  "Educational re-analysis of a redistributed teaching release; not new clinical or regulatory evidence.",
  cex = 0.75
)
dev.off()

message("[04] Recruiter-facing delivery visuals refined")
