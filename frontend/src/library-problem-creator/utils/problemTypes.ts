export const PROBLEM_TYPE_LABELS: Record<string, string> = {
  multiplechoiceresponse: 'Single Choice',
  choiceresponse: 'Multiple Choice',
  optionresponse: 'Dropdown',
  numericalresponse: 'Numeric',
  stringresponse: 'Text',
};

/** Returns the human-readable label for a problem type, falling back to the raw type string. */
export function getProblemTypeLabel(problemType: string): string {
  return PROBLEM_TYPE_LABELS[problemType] ?? problemType;
}
