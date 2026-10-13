#!/usr/bin/env Rscript
# Real published Theoph data + open-source R nlme population random effects.
# NOT licensed NONMEM, CDISC-conformant clinical trial data, or model qualification.
suppressPackageStartupMessages(library(nlme))
data("Theoph", package="datasets")
d <- datasets::Theoph
if (nrow(d)!=132L || length(unique(d$Subject))!=12L)
  stop("unexpected public Theoph source cardinality")
# For Theoph, Dose is mg/kg and concentration is mg/L: apparent CL is L/kg/h.
# Use separate diagonal random effects on log(Ka) and log(CL), with log(Ke)
# fixed across subjects. Avoid overfitting 3 strongly correlated random effects.
fit <- nlme::nlme(
  conc ~ SSfol(Dose, Time, lKe, lKa, lCl),
  data=d,
  fixed = lKe + lKa + lCl ~ 1,
  random = nlme::pdDiag(lKa + lCl ~ 1),
  start = c(lKe=-2.4,lKa=0.45,lCl=-3.2),
  method="ML",
  control=nlme::nlmeControl(maxIter=150,msMaxIter=200,pnlsMaxIter=25,
                             returnObject=FALSE)
)
fixed <- nlme::fixef(fit)
if (!all(c("lKe","lKa","lCl") %in% names(fixed)) ||
    any(!is.finite(fixed))) stop("invalid nlme coefficients")
ke <- exp(fixed["lKe"])
ka <- exp(fixed["lKa"])
cl <- exp(fixed["lCl"])
v <- cl/ke
if (any(!is.finite(c(ke,ka,cl,v))) ||
    any(c(ke,ka,cl,v)<=0)) stop("nonphysical positive kinetic parameters")
population <- as.numeric(predict(fit,level=0))
conditional <- as.numeric(predict(fit,level=1))
obs <- as.numeric(d$conc)
if (length(population)!=132 || length(conditional)!=132 ||
    any(!is.finite(population)) || any(!is.finite(conditional)))
  stop("non-finite or missing fitted concentrations")
rmse <- function(pred) sqrt(mean((pred-obs)^2))
pop_error <- rmse(population)
ind_error <- rmse(conditional)
# Direct function of fixed effects must match population prediction.
manual <- SSfol(as.numeric(d$Dose),as.numeric(d$Time),
                fixed["lKe"],fixed["lKa"],fixed["lCl"])
if (max(abs(as.numeric(manual)-population))>1e-6)
  stop("fixed-effect prediction disagrees with SSfol reconstruction")
output <- "outputs/nonmem_theoph_public/validation"
dir.create(output,recursive=TRUE,showWarnings=FALSE)
params <- data.frame(
 parameter=c("log_Ke_h_inverse","log_Ka_h_inverse","log_CL_L_kg_h",
             "Ke_h_inverse","Ka_h_inverse","CL_L_kg_h","V_L_kg",
             "sigma_residual_mg_L","population_RMSE_mg_L",
             "conditional_RMSE_mg_L","logLik","AIC"),
 value=as.numeric(c(fixed["lKe"],fixed["lKa"],fixed["lCl"],
                    ke,ka,cl,v,fit$sigma,pop_error,ind_error,
                    as.numeric(logLik(fit)),AIC(fit))),
 stringsAsFactors=FALSE)
write.csv(params,file.path(output,"theoph_nlme_parameters.csv"),row.names=FALSE)
predictions <- data.frame(
 SUBJECT=as.character(d$Subject),TIME_H=as.numeric(d$Time),
 DOSE_MG_KG=as.numeric(d$Dose),OBS_CONC_MG_L=obs,
 POP_PRED_MG_L=population,IND_PRED_MG_L=conditional)
write.csv(predictions,file.path(output,"theoph_nlme_predictions.csv"),row.names=FALSE)
writeLines(c(
 "# Real public Theoph nonlinear mixed-effects PK analysis (R nlme)",
 "",
 "Source: R datasets::Theoph, 12 subjects and 132 observations.",
 "Model: one-compartment oral SSfol; fixed log(Ke), log(Ka), log(CL);",
 "independent diagonal subject random effects on log(Ka) and log(CL).",
 "Fit method: nlme maximum likelihood, not NONMEM.",
 "",
 sprintf("Ke %.6f/h; Ka %.6f/h; CL %.6f L/kg/h; V %.6f L/kg",ke,ka,cl,v),
 sprintf("Population prediction in-sample RMSE %.5f mg/L",pop_error),
 sprintf("Subject-conditional prediction in-sample RMSE %.5f mg/L",ind_error),
 "",
 "Since dose is mg/kg (not absolute mg), CL and V are weight-normalised.",
 "These are in-sample summaries, not cross-validated forecasting performance.",
 "No BLQ model is needed or claimed: the public source has no assay LLOQ.",
 "The nlme fit uses public historical PK data but is NOT a licensed NONMEM",
 "run, a sponsor model, a validated pharmacometric model or a submission."
),file.path(output,"theoph_nlme_review.md"))
cat(sprintf("Public Theoph nlme: 12 subjects, 132 samples, CL=%.6f L/kg/h, population RMSE=%.5f mg/L, conditional RMSE=%.5f mg/L\n",
            cl,pop_error,ind_error))
