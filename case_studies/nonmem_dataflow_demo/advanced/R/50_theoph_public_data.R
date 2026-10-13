#!/usr/bin/env Rscript
# PUBLIC theophylline PK records from R datasets::Theoph, not a synthetic clinical trial.
# Unknown patient age and sex encoded in unused NONMEM variables as AGE=-99 and SEX=-1.
# Theoph Time is relative hours; no actual calendar timestamps are invented.
if (!exists("Theoph",envir=as.environment("package:datasets"))) data("Theoph",package="datasets")
reference <- as.data.frame(datasets::Theoph)
stopifnot(nrow(reference)==132L,length(unique(reference$Subject))==12L)
root <- "outputs/nonmem_theoph_public"
for(sub in c("data","metadata","model")) dir.create(file.path(root,sub),recursive=TRUE,showWarnings=FALSE)
subject <- as.character(reference$Subject)
ids <- sort(unique(subject))
crosswalk <- data.frame(USUBJID=paste0("THEOPH_",ids),ID=seq_along(ids))
data_rows <- list()
for(k in seq_along(ids)){
  s<-ids[k];p<-reference[subject==s,,drop=FALSE]
  if(length(unique(p$Wt))!=1L || length(unique(p$Dose))!=1L) stop("Wt/Dose differ within subject")
  weight<-as.numeric(p$Wt[1]);dose_mg<-as.numeric(p$Dose[1])*weight
  if(anyNA(p$Time) || anyNA(p$conc) || any(p$Time<0) || any(p$conc<0)) stop("invalid Theoph source")
  data_rows[[length(data_rows)+1L]]<-data.frame(
   ID=k,TIME=0,TAD=0,EVID=1,MDV=1,DV=0,AMT=dose_mg,RATE=0,CMT=1,
   WT=weight,AGE=-99,SEX=-1,BLQ=0,LLOQ=0,CENS=0,
   SOURCE_KEY=paste0("DOSE:",s),stringsAsFactors=FALSE)
  for(j in seq_len(nrow(p))){
    data_rows[[length(data_rows)+1L]]<-data.frame(
      ID=k,TIME=as.numeric(p$Time[j]),TAD=as.numeric(p$Time[j]),
      EVID=0,MDV=0,DV=as.numeric(p$conc[j])*1000,AMT=0,RATE=0,CMT=2,
      WT=weight,AGE=-99,SEX=-1,BLQ=0,LLOQ=0,CENS=0,
      SOURCE_KEY=paste0("THEOPH:",s,":",j),stringsAsFactors=FALSE)
  }
}
data <- do.call(rbind,data_rows)
data <- data[order(data$ID,data$TIME,-data$EVID),,drop=FALSE]
rownames(data)<-NULL
cols <- c("ID","TIME","TAD","EVID","MDV","DV","AMT","RATE","CMT","WT","AGE","SEX","BLQ","LLOQ","CENS")
write.csv(data,file.path(root,"data/nonmem_input_review.csv"),row.names=FALSE)
write.table(data[,cols],file.path(root,"data/nonmem_input.csv"),
            sep=",",quote=FALSE,row.names=FALSE,col.names=FALSE)
source_export <- data.frame(SUBJECT=subject,WT_KG=reference$Wt,DOSE_MG_KG=reference$Dose,
                            TIME_H=reference$Time,CONC_MG_L=reference$conc)
write.csv(source_export,file.path(root,"data/public_theoph_source_export.csv"),row.names=FALSE)
write.csv(crosswalk,file.path(root,"metadata/subject_crosswalk.csv"),row.names=FALSE)
writeLines(c("PROVENANCE: datasets::Theoph (R recommended datasets package).",
  "12 human subjects; 132 published PK observations; oral theophylline.",
  "Dose units: mg/kg. Transform total dose mg = Dose * Wt(kg).",
  "Concentration source mg/L; analysis variable DV is ng/mL (times 1000).",
  "Time values represent hours after dose; no real calendar dates available.",
  "Age and sex are not observed: -99 and -1 are explicit unused placeholders.",
  "No LLOQ/BLQ evidence provided: CENS=0, LLOQ=0 (not zero assay limit).",
  "These are historical public PK measurements, not a CDISC SDTM source dataset.",
  "NONMEM estimation not performed."),file.path(root,"metadata/data_provenance.txt"))
file.copy("case_studies/nonmem_dataflow_demo/advanced/model/one_compartment_m1_unexecuted.ctl",
          file.path(root,"model/one_compartment_m1_unexecuted.ctl"),overwrite=TRUE)
cat(sprintf("R datasets::Theoph converted: %d observed concentrations, %d subjects, %d total NONMEM event rows\n",
sum(data$EVID==0),length(ids),nrow(data)))
