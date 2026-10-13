#!/usr/bin/env Rscript
# SYNTHETIC portfolio dataflow. Not SDTM- or NONMEM-validated; run from repo root.
args <- commandArgs(trailingOnly=TRUE)
mode <- if (length(args) == 0L) "m3" else sub("^--blq-mode=", "", args[1])
if (!(mode %in% c("m1","m3"))) stop("Use --blq-mode=m1 or --blq-mode=m3")
root <- "case_studies/nonmem_dataflow_demo/advanced"
indir <- file.path(root, "data")
outdir <- file.path("outputs/nonmem_advanced", mode)
for (d in c("data", "model", "metadata")) dir.create(file.path(outdir, d), recursive=TRUE, showWarnings=FALSE)
source_file <- function(stem, columns) {
  x <- read.csv(file.path(indir, paste0(stem, ".csv")), na.strings=c("", "NA"),
                colClasses="character", check.names=FALSE, stringsAsFactors=FALSE)
  if (!all(columns %in% names(x))) stop(paste(stem, "missing:", paste(setdiff(columns,names(x)),collapse=",")))
  if (nrow(x)==0L || anyNA(x$USUBJID)) stop(paste("missing subject",stem))
  x
}
dm <- source_file("dm", c("USUBJID","AGE","SEX"))
ex <- source_file("ex", c("USUBJID","EXSEQ","EXSTDTC","EXDOSE","EXDOSU","EXROUTE","EXDURH"))
pc <- source_file("pc", c("USUBJID","PCSEQ","PCDTC","PCSTRESN","PCSTRESU","BLQ_FLAG","LLOQ_NG_ML"))
vs <- source_file("vs", c("USUBJID","VSDTC","VSTESTCD","VSSTRESN","VSSTRESU"))
unique_key <- function(key,label) if (anyDuplicated(key)) stop(paste("duplicate source key",label))
unique_key(dm$USUBJID,"DM")
unique_key(paste(ex$USUBJID,ex$EXSEQ),"EX")
unique_key(paste(pc$USUBJID,pc$PCSEQ),"PC")
unique_key(paste(vs$USUBJID,vs$VSTESTCD),"VS")
if (!setequal(dm$USUBJID,ex$USUBJID) || !setequal(dm$USUBJID,pc$USUBJID) ||
    !setequal(dm$USUBJID,vs$USUBJID)) stop("source subject sets differ")
number <- function(x,label) {
  y <- suppressWarnings(as.numeric(x))
  if (any(!is.finite(y))) stop(paste("invalid or missing numeric",label))
  y
}
date <- function(x,label) {
  if (anyNA(x) || any(!grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$", x)))
    stop(paste("missing/partial timestamp",label))
  y <- as.POSIXct(strptime(x, "%Y-%m-%dT%H:%M:%S", tz="UTC"))
  if (anyNA(y) || any(format(y,"%Y-%m-%dT%H:%M:%S",tz="UTC") != x)) stop(paste("invalid timestamp",label))
  y
}
if (any(!dm$SEX %in% c("M","F")) || any(number(dm$AGE,"AGE") <= 0)) stop("invalid DM")
if (any(!ex$EXROUTE %in% c("ORAL","IV_INFUSION"))) stop("unsupported route")
if (any(!ex$EXDOSU %in% c("mg","ug"))) stop("unsupported EXDOSU")
if (any(!pc$PCSTRESU %in% c("ng/mL","ug/L","mg/L"))) stop("unsupported PCSTRESU")
if (any(!pc$BLQ_FLAG %in% c("Y","N"))) stop("invalid BLQ flag")
if (any(!vs$VSTESTCD %in% "WEIGHT") || any(!vs$VSSTRESU %in% c("kg","g"))) stop("unsupported VS")
if (any(number(ex$EXDOSE,"EXDOSE") <= 0) || any(number(ex$EXDURH,"EXDURH") < 0))
  stop("invalid dose or duration")
if (any((ex$EXROUTE == "ORAL") != (number(ex$EXDURH,"EXDURH")==0))) stop("oral duration must be 0; IV duration positive")
if (any(number(pc$LLOQ_NG_ML,"LLOQ") <= 0)) stop("LLOQ must be positive")
if (any((pc$BLQ_FLAG=="Y") != is.na(pc$PCSTRESN))) stop("BLQ flag/value conflict")
if (any(number(pc$PCSTRESN[pc$BLQ_FLAG=="N"],"PCSTRESN") < 0)) stop("negative observed concentration")
if (any(number(vs$VSSTRESN,"VSSTRESN") <= 0)) stop("invalid baseline weight")
subjects <- sort(dm$USUBJID)
xwalk <- data.frame(USUBJID=subjects, ID=seq_along(subjects))
write.csv(xwalk,file.path(outdir,"metadata","subject_crosswalk.csv"),row.names=FALSE)
as_hours <- function(x,y) as.numeric(difftime(x,y,units="hours"))
allrows <- list()
for(s in subjects) {
  id <- xwalk$ID[xwalk$USUBJID == s]
  e <- ex[ex$USUBJID==s,,drop=FALSE]
  p <- pc[pc$USUBJID==s,,drop=FALSE]
  d <- dm[dm$USUBJID==s,,drop=FALSE]
  w <- vs[vs$USUBJID==s & vs$VSTESTCD=="WEIGHT",,drop=FALSE]
  if(nrow(w)!=1L || nrow(e)==0L || nrow(p)==0L) stop(paste("unsupported source cardinality",s))
  ed <- date(e$EXSTDTC,"EXSTDTC")
  pd <- date(p$PCDTC,"PCDTC")
  wd <- date(w$VSDTC,"VSDTC")
  first <- min(ed)
  if(any(pd<first) || any(wd>first)) stop(paste("sample before first dose or post-dose weight",s))
  weight <- number(w$VSSTRESN,"weight")*ifelse(w$VSSTRESU=="g",0.001,1)
  age <- number(d$AGE,"age")
  sex <- as.integer(d$SEX=="M")
  for(j in seq_len(nrow(e))) {
    mg <- number(e$EXDOSE[j],"EXDOSE")*ifelse(e$EXDOSU[j]=="ug",0.001,1)
    dur <- number(e$EXDURH[j],"EXDURH")
    iv <- e$EXROUTE[j]=="IV_INFUSION"
    allrows[[length(allrows)+1L]] <- data.frame(ID=id,TIME=as_hours(ed[j],first),
      TAD=0,EVID=1,MDV=1,DV=0,AMT=mg,RATE=if(iv) mg/dur else 0,
      CMT=if(iv) 2 else 1,WT=weight,AGE=age,SEX=sex,BLQ=0,
      LLOQ=0,CENS=0,SOURCE_KEY=paste0("EX:",s,":",e$EXSEQ[j]),
      stringsAsFactors=FALSE)
  }
  for(j in seq_len(nrow(p))) {
    prev <- ed[ed<=pd[j]]
    if(!length(prev)) stop(paste("pre-dose sample",s))
    blq <- p$BLQ_FLAG[j]=="Y"
    ll <- number(p$LLOQ_NG_ML[j],"LLOQ")
    dv <- if(blq) { if(mode=="m3") ll else 0 } else {
      val <- number(p$PCSTRESN[j],"PCSTRESN")
      if(p$PCSTRESU[j]=="mg/L") val <- val * 1000
      if(val < ll) stop(paste("non-BLQ concentration below LLOQ",s))
      val
    }
    allrows[[length(allrows)+1L]] <- data.frame(ID=id,TIME=as_hours(pd[j],first),
      TAD=as_hours(pd[j],max(prev)),EVID=0,MDV=if(blq && mode=="m1") 1 else 0,
      DV=dv,AMT=0,RATE=0,CMT=2,WT=weight,AGE=age,SEX=sex,BLQ=as.integer(blq),
      LLOQ=ll,CENS=as.integer(blq),SOURCE_KEY=paste0("PC:",s,":",p$PCSEQ[j]),
      stringsAsFactors=FALSE)
  }
}
out <- do.call(rbind,allrows)
out <- out[order(out$ID,out$TIME,-out$EVID,out$SOURCE_KEY),,drop=FALSE]
rownames(out)<-NULL
physical <- c("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT","WT","AGE","SEX","BLQ","LLOQ","CENS")
if(any(!is.finite(as.matrix(out[,physical])))) stop("non-finite NONMEM fields")
review_path <- file.path(outdir,"data","nonmem_input_review.csv")
data_path <- file.path(outdir,"data","nonmem_input.csv")
write.csv(out,review_path,row.names=FALSE,na="")
write.table(out[,physical],data_path,col.names=FALSE,row.names=FALSE,sep=",",quote=FALSE,na="")
meta <- data.frame(variable=physical,
 source=c("DM.USUBJID","EX.EXSTDTC/PC.PCDTC","EX.EXSTDTC/PC.PCDTC","event type",
   "EX/PC + mode","PC.PCSTRESN/PC.LLOQ_NG_ML","EX.EXDOSE","EX.EXDURH",
   "EX.EXROUTE","VS.VSSTRESN","DM.AGE","DM.SEX","PC.BLQ_FLAG","PC.LLOQ_NG_ML","PC.BLQ_FLAG"),
 unit=c("","hour","hour","","","ng/mL","mg","mg/hour","","kg","year","","","ng/mL",""),
 note=c("subject ID crosswalk","hours since first dose","hours since latest dose","1=dose;0=PC",
  paste0("BLQ missing in m1, censored likelihood in m3; current=",mode),
  "For BLQ: m3 uses LLOQ threshold (not observed DV); m1 uses 0 sentinel",
  "Dose mg or ug->mg","IV: amount/duration; oral: 0","oral depot=1, IV/observation central=2",
  "single pre-dose weight kg","age","female=0,male=1","1 if BLQ","ng/mL","1 if BLQ"),stringsAsFactors=FALSE)
write.csv(meta,file.path(outdir,"metadata","variable_definitions.csv"),row.names=FALSE)
writeLines(mode,file.path(outdir,"metadata","blq_mode.txt"))
model_file <- file.path(root,"model",paste0("one_compartment_",mode,"_unexecuted.ctl"))
if(!file.copy(model_file,file.path(outdir,"model",basename(model_file)),overwrite=TRUE))
 stop("model copy failed")
cat(sprintf("Advanced synthetic dataflow mode=%s subjects=%d doses=%d samples=%d infusions=%d BLQ=%d rows=%d\n",
mode,length(subjects),sum(out$EVID==1),sum(out$EVID==0),sum(out$RATE>0),
sum(out$BLQ),nrow(out)))
