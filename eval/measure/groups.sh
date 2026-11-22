# The figures compared: the reference figures (ref-*) and ours (our-*), by type, as in the comparison of 2026-11-13.
# Sourced by measure.sh. The paths name runs of that round: edit the lists for a new one.
source ${${(%):-%x}:A:h:h}/env.sh
R=$SCIFIG_SAMPLES
G=$SCIFIG_GEN
groups=(
  "ref-workflow=$R/workflow"
  "our-workflow=$G/e2e25/ml-training-workflow.png,$G/e2e31/ml-training-workflow.png,$G/e2e34/ml-training-workflow.png,$G/e2e37/mouse_16s_workflow.png"
  "ref-roadmap=$R/roadmap"
  "our-roadmap=$G/e2e26/roadmap-checked.png,$G/e2e28/roadmap-original.png,$G/e2e29/route-original.png,$G/e2e40/soc-roadmap-original.png"
  "ref-system=$R/system"
  "our-system=$G/e2e27/rag-overview.png,$G/e2e32/rag-architecture.png,$G/e2e33/rag-architecture.png,$G/fix39/final.png,$G/e2e30/architecture.png"
  "ref-model=$R/model"
  "our-model=$G/e2e35/transformer-architecture.png,$G/e2e36/cnn_architecture.png,$G/e2e43/transformer.png"
  "ref-framework=$R/framework"
  "our-framework=$G/e2e38/conceptual_framework.png"
  "ref-mechanism=$R/mechanism"
  "our-mechanism=$G/fix42/corrected.png"
  "ref-abstract=$R/abstract"
  "our-abstract=$G/e2e41/graphical_abstract_draft.png"
)
