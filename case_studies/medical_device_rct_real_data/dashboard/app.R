if (!requireNamespace("shiny", quietly = TRUE)) {
  stop("The optional dashboard requires the 'shiny' package. Run install.packages('shiny').")
}

library(shiny)

case_dir <- normalizePath(file.path(getwd(), ".."), mustWork = TRUE)
output_dir <- file.path(case_dir, "outputs")
data_path <- file.path(case_dir, "data", "analysis_data.rds")

required <- c(
  file.path(output_dir, "binary_outcomes.csv"),
  file.path(output_dir, "continuous_outcomes.csv"),
  file.path(output_dir, "qc_findings.csv"),
  file.path(output_dir, "missingness.csv"),
  data_path
)
if (any(!file.exists(required))) {
  stop("Run 'Rscript run_all.R' from the case-study folder before starting the dashboard.")
}

dat <- readRDS(data_path)
binary <- read.csv(file.path(output_dir, "binary_outcomes.csv"), check.names = FALSE)
continuous <- read.csv(file.path(output_dir, "continuous_outcomes.csv"), check.names = FALSE)
qc <- read.csv(file.path(output_dir, "qc_findings.csv"), check.names = FALSE)
missingness <- read.csv(file.path(output_dir, "missingness.csv"), check.names = FALSE)

first <- binary[binary$variable == "attempt1_S_F", , drop = FALSE]
time_row <- continuous[continuous$variable == "total_intubation_time", , drop = FALSE]

ui <- fluidPage(
  titlePanel("Medical-device RCT: statistical review dashboard"),
  p("Educational re-analysis of a 99-patient public teaching release; not new clinical evidence."),
  tabsetPanel(
    tabPanel(
      "Overview",
      fluidRow(
        column(
          4,
          wellPanel(
            h4("First-attempt success"),
            p(sprintf("Pentax AWS: %d/%d (%.1f%%)", first$aws_events, first$aws_n, 100 * first$aws_risk)),
            p(sprintf("Macintosh: %d/%d (%.1f%%)", first$mac_events, first$mac_n, 100 * first$mac_risk))
          )
        ),
        column(
          4,
          wellPanel(
            h4("Median total time"),
            p(sprintf("Pentax AWS: %.1f s", time_row$aws_median)),
            p(sprintf("Macintosh: %.1f s", time_row$mac_median))
          )
        ),
        column(
          4,
          wellPanel(
            h4("QC status"),
            p(sprintf("PASS: %d", sum(qc$status == "PASS"))),
            p(sprintf("REVIEW: %d", sum(qc$status == "REVIEW"))),
            p(sprintf("FAIL: %d", sum(qc$status == "FAIL")))
          )
        )
      ),
      plotOutput("time_plot", height = "420px")
    ),
    tabPanel(
      "Outcomes",
      h3("Binary outcomes"),
      tableOutput("binary_table"),
      h3("Continuous outcomes"),
      tableOutput("continuous_table")
    ),
    tabPanel(
      "QC and missingness",
      h3("Checks requiring review"),
      tableOutput("review_table"),
      h3("Core-variable missingness"),
      tableOutput("missing_table")
    )
  )
)

server <- function(input, output, session) {
  output$time_plot <- renderPlot({
    boxplot(
      total_intubation_time ~ device,
      data = dat,
      ylab = "Total intubation time (seconds)",
      xlab = "Randomized device",
      main = "Patient-level total intubation time",
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
  })

  output$binary_table <- renderTable({
    data.frame(
      Outcome = binary$outcome,
      `Pentax AWS` = sprintf("%d/%d (%.1f%%)", binary$aws_events, binary$aws_n, 100 * binary$aws_risk),
      Macintosh = sprintf("%d/%d (%.1f%%)", binary$mac_events, binary$mac_n, 100 * binary$mac_risk),
      `Risk difference, pp` = sprintf("%.1f", 100 * binary$risk_difference_aws_minus_mac),
      `Fisher p` = sprintf("%.4f", binary$fisher_p),
      check.names = FALSE
    )
  }, striped = TRUE, bordered = TRUE, spacing = "s")

  output$continuous_table <- renderTable({
    data.frame(
      Outcome = continuous$outcome,
      `Pentax AWS median [Q1, Q3]` = sprintf("%.1f [%.1f, %.1f]", continuous$aws_median, continuous$aws_q1, continuous$aws_q3),
      `Macintosh median [Q1, Q3]` = sprintf("%.1f [%.1f, %.1f]", continuous$mac_median, continuous$mac_q1, continuous$mac_q3),
      `Median difference` = sprintf("%.1f", continuous$median_difference_aws_minus_mac),
      `Wilcoxon p` = formatC(continuous$wilcoxon_p, format = "g", digits = 4),
      check.names = FALSE
    )
  }, striped = TRUE, bordered = TRUE, spacing = "s")

  output$review_table <- renderTable({
    qc[qc$status != "PASS", c("check_id", "domain", "status", "n_affected", "detail"), drop = FALSE]
  }, striped = TRUE, bordered = TRUE, spacing = "s")

  output$missing_table <- renderTable({
    missingness[missingness$n_missing > 0, c("variable", "n_missing", "n_total", "pct_missing"), drop = FALSE]
  }, striped = TRUE, bordered = TRUE, spacing = "s")
}

shinyApp(ui, server)
