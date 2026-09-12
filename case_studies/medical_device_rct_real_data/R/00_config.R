options(stringsAsFactors = FALSE)

SOURCE_URL <- "https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/medicaldata/laryngoscope.csv"
SOURCE_DOC <- "https://search.r-project.org/CRAN/refmans/medicaldata/html/laryngoscope.html"
SOURCE_STUDY_DOI <- "10.1213/ANE.0b013e31822cf47d"
TSHS_URL <- "https://www.causeweb.org/tshs/"

DIR_DATA <- "data"
DIR_OUTPUT <- "outputs"
DIR_FIG <- file.path(DIR_OUTPUT, "figures")

dir.create(DIR_DATA, recursive = TRUE, showWarnings = FALSE)
dir.create(DIR_OUTPUT, recursive = TRUE, showWarnings = FALSE)
dir.create(DIR_FIG, recursive = TRUE, showWarnings = FALSE)

RAW_CSV <- file.path(DIR_DATA, "laryngoscope.csv")
ANALYSIS_RDS <- file.path(DIR_DATA, "analysis_data.rds")

DEVICE_LABELS <- c(
  `0` = "Macintosh #4",
  `1` = "Pentax AWS video"
)

fmt_num <- function(x, digits = 3) {
  ifelse(is.na(x), NA_character_, formatC(x, format = "f", digits = digits))
}

fmt_pct <- function(x, digits = 1) {
  ifelse(is.na(x), NA_character_, paste0(formatC(100 * x, format = "f", digits = digits), "%"))
}

wilson_ci <- function(x, n, conf.level = 0.95) {
  if (is.na(x) || is.na(n) || n <= 0) return(c(lower = NA_real_, upper = NA_real_))
  z <- qnorm(1 - (1 - conf.level) / 2)
  p <- x / n
  den <- 1 + z^2 / n
  centre <- (p + z^2 / (2 * n)) / den
  half <- z * sqrt((p * (1 - p) / n) + z^2 / (4 * n^2)) / den
  c(lower = max(0, centre - half), upper = min(1, centre + half))
}

newcombe_rd_ci <- function(x1, n1, x0, n0, conf.level = 0.95) {
  p1 <- x1 / n1
  p0 <- x0 / n0
  ci1 <- wilson_ci(x1, n1, conf.level)
  ci0 <- wilson_ci(x0, n0, conf.level)
  rd <- p1 - p0
  lower <- rd - sqrt((p1 - ci1[["lower"]])^2 + (ci0[["upper"]] - p0)^2)
  upper <- rd + sqrt((ci1[["upper"]] - p1)^2 + (p0 - ci0[["lower"]])^2)
  c(estimate = rd, lower = lower, upper = upper)
}

risk_ratio_ci <- function(x1, n1, x0, n0, conf.level = 0.95) {
  # The selected outcomes use success/occurrence coding. Add a half-cell correction
  # only when one of the four 2x2 cells is zero.
  a <- x1
  b <- n1 - x1
  c_ <- x0
  d <- n0 - x0
  if (any(c(a, b, c_, d) == 0)) {
    a <- a + 0.5
    b <- b + 0.5
    c_ <- c_ + 0.5
    d <- d + 0.5
  }
  n1c <- a + b
  n0c <- c_ + d
  rr <- (a / n1c) / (c_ / n0c)
  se <- sqrt((1 / a) - (1 / n1c) + (1 / c_) - (1 / n0c))
  z <- qnorm(1 - (1 - conf.level) / 2)
  c(estimate = rr, lower = exp(log(rr) - z * se), upper = exp(log(rr) + z * se))
}

bootstrap_location_difference <- function(x1, x0, FUN = median, B = 10000L, seed = 20260912L) {
  x1 <- x1[is.finite(x1)]
  x0 <- x0[is.finite(x0)]
  if (length(x1) < 2 || length(x0) < 2) {
    return(c(estimate = NA_real_, lower = NA_real_, upper = NA_real_))
  }
  set.seed(seed)
  est <- FUN(x1) - FUN(x0)
  sims <- replicate(B, {
    FUN(sample(x1, length(x1), replace = TRUE)) -
      FUN(sample(x0, length(x0), replace = TRUE))
  })
  qs <- unname(quantile(sims, probs = c(0.025, 0.975), na.rm = TRUE, type = 6))
  c(estimate = est, lower = qs[1], upper = qs[2])
}

smd_continuous <- function(x1, x0) {
  x1 <- x1[is.finite(x1)]
  x0 <- x0[is.finite(x0)]
  sp <- sqrt((var(x1) + var(x0)) / 2)
  if (!is.finite(sp) || sp == 0) return(NA_real_)
  (mean(x1) - mean(x0)) / sp
}

smd_binary <- function(x1, x0) {
  x1 <- x1[!is.na(x1)]
  x0 <- x0[!is.na(x0)]
  p1 <- mean(x1)
  p0 <- mean(x0)
  den <- sqrt((p1 * (1 - p1) + p0 * (1 - p0)) / 2)
  if (!is.finite(den) || den == 0) return(NA_real_)
  (p1 - p0) / den
}

write_csv <- function(x, path) {
  write.csv(x, path, row.names = FALSE, na = "")
}
