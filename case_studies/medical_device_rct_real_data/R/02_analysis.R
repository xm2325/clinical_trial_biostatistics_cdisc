message("[02] Running randomized-device comparisons and sensitivity analyses")

if (!file.exists(ANALYSIS_RDS)) stop("Analysis data not found; run 01_prepare_data.R first")
dat <- readRDS(ANALYSIS_RDS)

aws <- dat$Randomization == 1
mac <- dat$Randomization == 0

if (sum(aws, na.rm = TRUE) != 50 || sum(mac, na.rm = TRUE) != 49) {
  stop("Unexpected randomized arm sizes in the teaching dataset")
}

# -----------------------------------------------------------------------------
# Baseline table: descriptive only. No baseline hypothesis tests are used.
# -----------------------------------------------------------------------------
baseline_rows <- list()
add_cont_baseline <- function(variable, label) {
  x1 <- dat[[variable]][aws]
  x0 <- dat[[variable]][mac]
  baseline_rows[[length(baseline_rows) + 1L]] <<- data.frame(
    variable = variable,
    label = label,
    statistic = "mean (SD); median [Q1, Q3]",
    aws_n = sum(!is.na(x1)),
    aws_value = sprintf(
      "%.2f (%.2f); %.2f [%.2f, %.2f]",
      mean(x1, na.rm = TRUE), sd(x1, na.rm = TRUE), median(x1, na.rm = TRUE),
      quantile(x1, 0.25, na.rm = TRUE), quantile(x1, 0.75, na.rm = TRUE)
    ),
    mac_n = sum(!is.na(x0)),
    mac_value = sprintf(
      "%.2f (%.2f); %.2f [%.2f, %.2f]",
      mean(x0, na.rm = TRUE), sd(x0, na.rm = TRUE), median(x0, na.rm = TRUE),
      quantile(x0, 0.25, na.rm = TRUE), quantile(x0, 0.75, na.rm = TRUE)
    ),
    smd_aws_minus_mac = smd_continuous(x1, x0),
    stringsAsFactors = FALSE
  )
}

add_bin_baseline <- function(variable, label) {
  x1 <- dat[[variable]][aws]
  x0 <- dat[[variable]][mac]
  baseline_rows[[length(baseline_rows) + 1L]] <<- data.frame(
    variable = variable,
    label = label,
    statistic = "n/N (%)",
    aws_n = sum(!is.na(x1)),
    aws_value = sprintf("%d/%d (%.1f%%)", sum(x1 == 1, na.rm = TRUE), sum(!is.na(x1)), 100 * mean(x1, na.rm = TRUE)),
    mac_n = sum(!is.na(x0)),
    mac_value = sprintf("%d/%d (%.1f%%)", sum(x0 == 1, na.rm = TRUE), sum(!is.na(x0)), 100 * mean(x0, na.rm = TRUE)),
    smd_aws_minus_mac = smd_binary(x1, x0),
    stringsAsFactors = FALSE
  )
}

add_cont_baseline("age", "Age, years")
add_bin_baseline("female", "Female")
add_cont_baseline("BMI", "Body mass index, kg/m^2")
add_bin_baseline("asa_3_4", "ASA physical status 3-4")
add_bin_baseline("mallampati_3_4", "Mallampati class 3-4")

baseline <- do.call(rbind, baseline_rows)
write_csv(baseline, file.path(DIR_OUTPUT, "baseline_table.csv"))

# -----------------------------------------------------------------------------
# Binary outcomes
# Difference direction is always AWS minus Macintosh.
# -----------------------------------------------------------------------------
binary_compare <- function(variable, label, event_value = 1) {
  y1 <- dat[[variable]][aws]
  y0 <- dat[[variable]][mac]
  y1 <- y1[!is.na(y1)]
  y0 <- y0[!is.na(y0)]
  x1 <- sum(y1 == event_value)
  x0 <- sum(y0 == event_value)
  n1 <- length(y1)
  n0 <- length(y0)

  rd <- newcombe_rd_ci(x1, n1, x0, n0)
  rr <- risk_ratio_ci(x1, n1, x0, n0)
  mat <- matrix(c(x1, n1 - x1, x0, n0 - x0), nrow = 2, byrow = TRUE)
  ft <- fisher.test(mat)

  data.frame(
    variable = variable,
    outcome = label,
    event_value = event_value,
    aws_events = x1,
    aws_n = n1,
    aws_risk = x1 / n1,
    mac_events = x0,
    mac_n = n0,
    mac_risk = x0 / n0,
    risk_difference_aws_minus_mac = unname(rd[["estimate"]]),
    rd_ci95_lower = unname(rd[["lower"]]),
    rd_ci95_upper = unname(rd[["upper"]]),
    risk_ratio_aws_over_mac = unname(rr[["estimate"]]),
    rr_ci95_lower = unname(rr[["lower"]]),
    rr_ci95_upper = unname(rr[["upper"]]),
    fisher_p = unname(ft$p.value),
    stringsAsFactors = FALSE
  )
}

binary_outcomes <- rbind(
  binary_compare("attempt1_S_F", "First-attempt intubation success"),
  binary_compare("intubation_overall_S_F", "Overall successful intubation"),
  binary_compare("repeat_attempt", "More than one intubation attempt"),
  binary_compare("bleeding", "Trace bleeding"),
  binary_compare("sore_throat_any", "Any postoperative sore throat")
)
write_csv(binary_outcomes, file.path(DIR_OUTPUT, "binary_outcomes.csv"))

# -----------------------------------------------------------------------------
# Continuous / ordinal-score outcomes
# Main location comparison uses medians, a seeded nonparametric bootstrap interval,
# and a Wilcoxon rank-sum test. This avoids a normality assumption for skewed times.
# -----------------------------------------------------------------------------
continuous_compare <- function(variable, label, seed_offset = 0L) {
  x1 <- dat[[variable]][aws]
  x0 <- dat[[variable]][mac]
  x1 <- x1[is.finite(x1)]
  x0 <- x0[is.finite(x0)]
  boot <- bootstrap_location_difference(
    x1, x0, FUN = median, B = 10000L, seed = 20260912L + seed_offset
  )
  wt <- suppressWarnings(wilcox.test(x1, x0, exact = FALSE, conf.int = FALSE))
  data.frame(
    variable = variable,
    outcome = label,
    aws_n = length(x1),
    aws_median = median(x1),
    aws_q1 = unname(quantile(x1, 0.25)),
    aws_q3 = unname(quantile(x1, 0.75)),
    mac_n = length(x0),
    mac_median = median(x0),
    mac_q1 = unname(quantile(x0, 0.25)),
    mac_q3 = unname(quantile(x0, 0.75)),
    median_difference_aws_minus_mac = unname(boot[["estimate"]]),
    bootstrap_ci95_lower = unname(boot[["lower"]]),
    bootstrap_ci95_upper = unname(boot[["upper"]]),
    wilcoxon_p = unname(wt$p.value),
    stringsAsFactors = FALSE
  )
}

continuous_outcomes <- rbind(
  continuous_compare("total_intubation_time", "Total intubation time, seconds", 0L),
  continuous_compare("ease", "Ease score: 0 extremely easy to 100 extremely difficult", 1L)
)
write_csv(continuous_outcomes, file.path(DIR_OUTPUT, "continuous_outcomes.csv"))

# -----------------------------------------------------------------------------
# Sensitivity analyses
# -----------------------------------------------------------------------------
sensitivity_rows <- list()

# S1: exclude rows where first-attempt time exceeds supplied total time. This is not
# the main analysis because the source definition is unresolved; it is a bounded check.
time_issue <- !is.na(dat$attempt1_time) & !is.na(dat$total_intubation_time) &
  dat$attempt1_time > dat$total_intubation_time
sens_dat <- dat[!time_issue, , drop = FALSE]
sens_aws <- sens_dat$Randomization == 1
sens_mac <- sens_dat$Randomization == 0
boot_s1 <- bootstrap_location_difference(
  sens_dat$total_intubation_time[sens_aws],
  sens_dat$total_intubation_time[sens_mac],
  FUN = median, B = 10000L, seed = 20260914L
)
sensitivity_rows[[1]] <- data.frame(
  analysis_id = "S1",
  analysis = "Total-time median difference excluding source-timing review rows",
  n = nrow(sens_dat),
  estimate = unname(boot_s1[["estimate"]]),
  ci95_lower = unname(boot_s1[["lower"]]),
  ci95_upper = unname(boot_s1[["upper"]]),
  scale = "seconds; AWS minus Macintosh",
  note = paste0("Excluded ", sum(time_issue), " row(s) only for sensitivity; main analysis retains source values."),
  stringsAsFactors = FALSE
)

# S2: covariate-adjusted log-time model. Randomized arm remains the target coefficient.
model_vars <- c("total_intubation_time", "Randomization", "age", "BMI", "gender", "asa", "Mallampati")
cc <- complete.cases(dat[, model_vars])
fit <- lm(
  log(total_intubation_time) ~ Randomization + age + BMI + gender + asa + Mallampati,
  data = dat[cc, , drop = FALSE]
)
coef_name <- "Randomization"
co <- coef(summary(fit))[coef_name, ]
ci <- confint(fit, coef_name, level = 0.95)
sensitivity_rows[[2]] <- data.frame(
  analysis_id = "S2",
  analysis = "Covariate-adjusted total-time model",
  n = sum(cc),
  estimate = exp(unname(co[["Estimate"]])),
  ci95_lower = exp(unname(ci[1])),
  ci95_upper = exp(unname(ci[2])),
  scale = "multiplicative time ratio; AWS / Macintosh",
  note = "Sensitivity only: OLS on log(total time), adjusted for age, BMI, gender, ASA and Mallampati.",
  stringsAsFactors = FALSE
)

sensitivity <- do.call(rbind, sensitivity_rows)
write_csv(sensitivity, file.path(DIR_OUTPUT, "sensitivity_analysis.csv"))

message("[02] Analysis complete: ", nrow(binary_outcomes), " binary and ", nrow(continuous_outcomes), " continuous outcome rows")
