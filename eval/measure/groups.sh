# The figures compared: SciDraw's samples (sd-*) and ours (our-*), by type, as in the comparison of 2026-11-13.
# Sourced by measure.sh. The paths name runs of that round: edit the lists for a new one.
source ${${(%):-%x}:A:h:h}/env.sh
R=$SCIDRAW_SAMPLES
G=$SCIFIG_GEN
groups=(
  "sd-workflow=$R/workflow-diagram-generator"
  "our-workflow=$G/e2e25/ml-training-workflow.png,$G/e2e31/ml-training-workflow.png,$G/e2e34/ml-training-workflow.png,$G/e2e37/mouse_16s_workflow.png"
  "sd-roadmap=$R/research-roadmap-maker"
  "our-roadmap=$G/e2e26/roadmap-checked.png,$G/e2e28/roadmap-original.png,$G/e2e29/route-original.png,$G/e2e40/soc-roadmap-original.png"
  "sd-system=$R/rag-architecture-diagram-generator,$R/ai-architecture-diagram-generator/campusSystemArchitecture.png,$R/ai-architecture-diagram-generator/ecommerceMicroservices.png,$R/ai-architecture-diagram-generator/layeredErpArchitecture.png"
  "our-system=$G/e2e27/rag-overview.png,$G/e2e32/rag-architecture.png,$G/e2e33/rag-architecture.png,$G/fix39/final.png,$G/e2e30/architecture.png"
  "sd-model=$R/ai-architecture-diagram-generator/cnnClassifier.png,$R/ai-architecture-diagram-generator/encoderDecoder.png,$R/ai-architecture-diagram-generator/ganModel.png,$R/ai-architecture-diagram-generator/lstmSeq.png,$R/ai-architecture-diagram-generator/multimodalPipeline.png,$R/ai-architecture-diagram-generator/transformer.png,$R/llm-architecture-diagram-generator,$R/neural-network-diagram-generator"
  "our-model=$G/e2e35/transformer-architecture.png,$G/e2e36/cnn_architecture.png,$G/e2e43/transformer.png"
  "sd-framework=$R/conceptual-framework-maker"
  "our-framework=$G/e2e38/conceptual_framework.png"
  "sd-mechanism=$R/mechanism-figure-generator,$R/signaling-pathway-diagram-generator"
  "our-mechanism=$G/fix42/corrected.png"
  "sd-abstract=$R/graphical-abstract,$R/graphical-abstract-maker"
  "our-abstract=$G/e2e41/graphical_abstract_draft.png"
)
