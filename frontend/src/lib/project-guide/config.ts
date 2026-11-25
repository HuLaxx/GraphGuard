/**
 * Per-project settings for the project assistant. Everything else under
 * src/lib/project-guide and src/components/assistant is shared verbatim across
 * FleetFlow, GraphGuard and Sentinance.
 */
export const ASSISTANT_CONFIG = {
  homeProject: "graphguard",
  projectName: "GraphGuard",
  ownerName: "Rahul Khanke",
  contactLine: "email rahulkhanke786@gmail.com or message him at linkedin.com/in/rahulkhanke.",
  theme: "graphguard",
  launcherLabel: "Ask GraphGuard",
  eyebrow: "Case notes · RAG guide",
  title: "Ask the GraphGuard guide",
  subtitle: "Ask about the project, its stack and evidence, or about Rahul.",
  greeting:
    "Hi! I answer from GraphGuard's docs, model card and evidence register, and from Rahul's profile. Every answer cites its source.",
  placeholder: "e.g. How are fraud scores explained?",
  suggestions: [
    "What is GraphGuard and how does it work?",
    "How does the XGBoost model perform, and on what data?",
    "How do Kafka, Avro and Neo4j fit together here?",
    "What skills and tools does Rahul work with?",
  ],
  /** Routes where the floating launcher would cover task UI. */
  hiddenPaths: [] as string[],
} as const;
