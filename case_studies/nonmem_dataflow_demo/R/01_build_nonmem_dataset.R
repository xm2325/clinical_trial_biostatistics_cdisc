#!/usr/bin/env Rscript
# Synthetic PK source -> NONMEM-style event dataset. Base R; run from repository root.
# Portfolio work sample ONLY. Not a validated NONMEM input for clinical submission.
input_dir <- "case_studies/nonmem_dataflow_demo/data"
output_dir <- "outputs/nonmem_demo"
data_dir <- file.path(output_dir, "data")
meta_dir <- file.path(output_dir, "metadata")
model_dir <- file.path(output_dir, "model")
for (d in c(data_dir, meta_dir, model_dir)) dir.create(d, recursive = TRUE, showWarnings = FALSE)

read_src <- function(n, fields) {
  p <- file.path(input_dir, paste0(n, ".csv"))
  d <- read.csv(p, colClasses = "character", na.strings = c("", "NA"),
                check.names = FALSE, stringsAsFactors = FALSE)
  if (!all(fields %in% names(d))) stop(paste("missing columns in", n))
  if (anyNA(d$USUBJID) || any(!nzchar(d$USUBJID))) stop(paste("missing subject in", n))
  d
}
num <- function(x, label) {
  y <- suppressWarnings(as.numeric(x))
  if (any(!is.finite(y))) stop(paste("invalid or missing", label))
  y
}
dt <- function(x, label) {
  y <- as.POSIXct(x, format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")
  if (anyNA(y)) stop(paste("invalid timestamp in", label))
  y
}
check_unique <- function(x, what) {
  if (anyDuplicated(x)) stop(paste("duplicate", what))
}
hours <- function(x, origin) as.numeric(difftime(x, origin, units = "hours"))
dm <- read_src("dm", c("USUBJID", "AGE", "SEX"))
ex <- read_src("ex", c("USUBJID", "EXSTDTC", "EXDOSE", "EXDOSU", "EXROUTE"))
pc <- read_src("pc", c("USUBJID", "PCDTC", "PCSTRESN", "PCSTRESU", "BLQ_FLAG", "LLOQ_NG_ML"))
vs <- read_src("vs", c("USUBJID", "VSDTC", "VSTESTCD", "VSSTRESN", "VSSTRESU"))
check_unique(dm$USUBJID, "DM subject")
check_unique(paste(ex$USUBJID, ex$EXSTDTC), "EX subject/time")
check_unique(paste(pc$USUBJID, pc$PCDTC), "PC subject/time")
if (!setequal(dm$USUBJID, ex$USUBJID) || !setequal(dm$USUBJID, pc$USUBJID) ||
    !setequal(dm$USUBJID, vs$USUBJID)) stop("source subject coverage mismatch")
if (any(!ex$EXROUTE %in% "ORAL")) stop("demo supports ORAL dosing only")
if (any(!ex$EXDOSU %in% c("mg", "ug"))) stop("unsupported dose unit")
if (any(!pc$PCSTRESU %in% c("ng/mL", "ug/L"))) stop("unsupported concentration unit")
if (any(!pc$BLQ_FLAG %in% c("Y", "N"))) stop("BLQ_FLAG must be Y or N")
if (any(!vs$VSTESTCD %in% "WEIGHT") || any(!vs$VSSTRESU %in% c("kg", "g"))) {
  stop("demo supports WEIGHT in kg or g only")
}
if (any(num(ex$EXDOSE, "EXDOSE") <= 0)) stop("dose must be positive")
if (any(num(pc$LLOQ_NG_ML, "LLOQ") <= 0)) stop("LLOQ must be positive")
if (any(num(dm$AGE, "AGE") <= 0) || any(!dm$SEX %in% c("F", "M"))) stop("invalid demographics")
if (any(!is.na(pc$PCSTRESN[pc$BLQ_FLAG == "Y"])) ||
    any(is.na(pc$PCSTRESN[pc$BLQ_FLAG == "N"]))) stop("BLQ and concentration disagree")

subjects <- sort(dm$USUBJID)
crosswalk <- data.frame(USUBJID = subjects, ID = seq_along(subjects))
rows <- list()
for (s in subjects) {
  id <- crosswalk$ID[crosswalk$USUBJID == s]
  d <- dm[dm$USUBJID == s, , drop = FALSE]
  e <- ex[ex$USUBJID == s, , drop = FALSE]
  p <- pc[pc$USUBJID == s, , drop = FALSE]
  v <- vs[vs$USUBJID == s & vs$VSTESTCD == "WEIGHT", , drop = FALSE]
  if (nrow(v) != 1L || nrow(e) < 1L || nrow(p) < 1L) stop(paste("unsupported source cardinality", s))
  ed <- dt(e$EXSTDTC, "EXSTDTC")
  pd <- dt(p$PCDTC, "PCDTC")
  wd <- dt(v$VSDTC, "VSDTC")
  first <- min(ed)
  if (any(pd < first) || wd > first) stop(paste("observation before dose or weight after first dose", s))
  weight <- num(v$VSSTRESN, "VSSTRESN") * ifelse(v$VSSTRESU == "g", 0.001, 1)
  if (weight <= 0) stop("invalid weight")
  age <- num(d$AGE, "AGE")
  sex <- ifelse(d$SEX == "M", 1, 0)
  for (j in seq_len(nrow(e))) {
    amount <- num(e$EXDOSE[j], "EXDOSE") * ifelse(e$EXDOSU[j] == "ug", 0.001, 1)
    rows[[length(rows) + 1L]] <- data.frame(ID = id, TIME = hours(ed[j], first), TAD = 0,
      EVID = 1, MDV = 1, DV = 0, AMT = amount, RATE = 0, CMT = 1,
      WT = weight, AGE = age, SEX = sex, BLQ = 0, LLOQ = 0)
  }
  for (j in seq_len(nrow(p))) {
    last_dose <- ed[ed <= pd[j]]
    if (!length(last_dose)) stop("PC record predates all doses")
    is_blq <- p$BLQ_FLAG[j] == "Y"
    ll <- num(p$LLOQ_NG_ML[j], "LLOQ")
    dv <- if (is_blq) 0 else num(p$PCSTRESN[j], "PCSTRESN")
    if (!is_blq && dv < ll) stop(paste("unflagged sub-LLOQ value", s))
    rows[[length(rows) + 1L]] <- data.frame(ID = id, TIME = hours(pd[j], first),
      TAD = hours(pd[j], max(last_dose)), EVID = 0, MDV = ifelse(is_blq, 1, 0),
      DV = dv, AMT = 0, RATE = 0, CMT = 2, WT = weight,
      AGE = age, SEX = sex, BLQ = as.integer(is_blq), LLOQ = ll)
  }
}
out <- do.call(rbind, rows)
out <- out[order(out$ID, out$TIME, -out$EVID), , drop = FALSE]
rownames(out) <- NULL
if (any(!is.finite(as.matrix(out)))) stop("non-finite NONMEM export values")
review <- file.path(data_dir, "nonmem_input_review.csv")
no_header <- file.path(data_dir, "nonmem_input.csv")
write.csv(out, review, row.names = FALSE, na = "")
write.table(out, no_header, row.names = FALSE, col.names = FALSE, sep = ",",
            quote = FALSE, na = "")
write.csv(crosswalk, file.path(meta_dir, "subject_crosswalk.csv"), row.names = FALSE)
defs <- data.frame(
  VARIABLE = names(out),
  SOURCE = c("DM.USUBJID", "EXSTDTC / PCDTC", "EXSTDTC / PCDTC", "event type",
    "PC.BLQ_FLAG / event type", "PC.PCSTRESN", "EX.EXDOSE",
    "EX.EXROUTE", "event type", "VS.VSSTRESN", "DM.AGE", "DM.SEX",
    "PC.BLQ_FLAG", "PC.LLOQ_NG_ML"),
  DERIVATION = c("sorted stable ID crosswalk", "hours since first dose", "hours since latest dose",
    "dose=1; sample=0", "dose or BLQ=1; measurable sample=0",
    "observed concentration in ng/mL; 0 for dose or BLQ",
    "dose in mg; 0 for sample", "0 (no infusion)", "oral depot=1; central observation=2",
    "baseline weight in kg", "years", "female=0, male=1",
    "BLQ=1 otherwise 0", "lower limit in ng/mL; 0 for dose"),
  stringsAsFactors = FALSE)
write.csv(defs, file.path(meta_dir, "variable_definitions.csv"), row.names = FALSE)
file.copy(file.path("case_studies/nonmem_dataflow_demo/model", "one_compartment_illustrative.ctl"),
          file.path(model_dir, "one_compartment_illustrative.ctl"), overwrite = TRUE)
manifest_paths <- c(review, no_header, file.path(meta_dir, "subject_crosswalk.csv"),
                    file.path(meta_dir, "variable_definitions.csv"),
                    file.path(model_dir, "one_compartment_illustrative.ctl"))
manifest <- data.frame(path = manifest_paths,
                       md5 = unname(tools::md5sum(manifest_paths)))
write.csv(manifest, file.path(meta_dir, "manifest.csv"), row.names = FALSE)
cat(sprintf("NONMEM demo: %d subjects, %d dose records, %d PC records, %d BLQ; written to %s\n",
            length(subjects), sum(out$EVID == 1), sum(out$EVID == 0),
            sum(out$BLQ == 1), output_dir))
