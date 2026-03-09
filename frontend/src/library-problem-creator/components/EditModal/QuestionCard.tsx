import React, { useState, useRef, useEffect } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Badge, Button, Card, Stack,
} from '@openedx/paragon';
import QuestionEditor from './QuestionEditor';
import ProblemTypeBadge from './ProblemTypeBadge';
import RegenerateForm from './RegenerateForm';
import VersionNavigator from './VersionNavigator';
import AnswerOptionsDisplay from './AnswerOptionsDisplay';
import messages from '../../messages';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';
/** Labelled field row */
const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="mb-2">
    <span className="small font-weight-bold">
      {label}
    </span>
    <div className="small mt-1">{children}</div>
  </div>
);

const QuestionCard = ({ index }: { index: number }) => {
  const {
    questions,
    questionHistories,
    selectedVersionIndices,
    discardedIndices,
    regeneratingIndices,
    editingIndex,
    regenerateQuestion,
    selectVersion,
    updateQuestion,
    discardQuestion,
    restoreQuestion,
    setEditingIndex,
  } = useLibraryProblemCreatorContext();

  const intl = useIntl();
  const [showRegenerateForm, setShowRegenerateForm] = useState(false);
  const [focusCard, setFocusCard] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const question = questions[index];
  const history = questionHistories[index] || [question];
  const selectedVersionIndex = selectedVersionIndices[index] ?? 0;
  const isDiscarded = discardedIndices.has(index);
  const isRegenerating = regeneratingIndices.has(index);
  const isEditing = editingIndex === index;

  // Scroll into view when edit is saved
  useEffect(() => {
    if (!isEditing && focusCard && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setFocusCard(false);
    }
  }, [isEditing, focusCard]);

  // Scroll into view when regeneration starts
  useEffect(() => {
    let timer: NodeJS.Timeout | undefined;
    if (isRegenerating && cardRef.current) {
      // Small delay to ensure DOM has updated with loading state
      timer = setTimeout(() => {
        cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
    }
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [isRegenerating]);

  const handleRegenerateSubmit = (idx: number, instructions?: string) => {
    setShowRegenerateForm(false);
    regenerateQuestion(idx, instructions);
  };

  return (
    <div ref={cardRef}>
      <Card
        isLoading={isRegenerating}
        className={`position-relative mb-2 ${isDiscarded ? 'text-muted' : ''}`}
      >
        {/* ── Header ── */}
        <Card.Section>
          <div className="d-flex align-items-center justify-content-between">
            <span className="font-weight-bold flex-1">
              {index + 1}. {question.displayName}
            </span>
            {isDiscarded
              ? (
                <Badge variant="danger" pill>
                  {intl.formatMessage(messages['ai.library.creator.card.discarded.label'])}
                </Badge>
              )
              : <ProblemTypeBadge problemType={question.problemType} className="ml-2" />}
          </div>
        </Card.Section>

        <Card.Divider />

        {/* ── Question body ── */}
        <Card.Section
          skeletonHeight={200}
        >

          {/* Question text */}
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.question'])}>
            <div>{question.questionHtml}</div>
          </Field>

          {/* Answer options — displayed as form components */}
          <AnswerOptionsDisplay question={question} />

          {/* Explanation */}
          {question.explanation && (
            <Field label={intl.formatMessage(messages['ai.library.creator.card.field.explanation'])}>
              <span>{question.explanation}</span>
            </Field>
          )}

          {/* Demand hints */}
          {question.demandHints && question.demandHints.length > 0 && (
            <Field label={intl.formatMessage(messages['ai.library.creator.card.field.hints'])}>
              <ol className="pl-3 mb-0 small">
                {question.demandHints.map((hint) => (
                  <li key={hint}>{hint}</li>
                ))}
              </ol>
            </Field>
          )}

          {/* Version history navigator */}
          <VersionNavigator
            selectedVersionIndex={selectedVersionIndex}
            totalVersions={history.length}
            onPrevious={() => selectVersion(index, selectedVersionIndex - 1)}
            onNext={() => selectVersion(index, selectedVersionIndex + 1)}
          />
          {/* Action buttons */}
          {!isDiscarded ? (
            <Stack direction="horizontal" gap={1} className="mt-5">
              <Button
                variant="outline-primary"
                size="sm"
                onClick={() => setEditingIndex(isEditing ? null : index)}
                disabled={isRegenerating || showRegenerateForm}
              >
                {intl.formatMessage(messages['ai.library.creator.card.edit'])}
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setShowRegenerateForm((v) => !v)}
                disabled={isRegenerating}
              >
                {intl.formatMessage(messages['ai.library.creator.card.regenerate'])}
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => discardQuestion(index)}
                disabled={isRegenerating || showRegenerateForm}
              >
                {intl.formatMessage(messages['ai.library.creator.card.discard'])}
              </Button>
            </Stack>
          ) : (
            <div className="mt-5">
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => restoreQuestion(index)}
              >
                {intl.formatMessage(messages['ai.library.creator.card.restore'])}
              </Button>
            </div>
          )}
        </Card.Section>

        <Card.Section>
          {/* Inline regenerate form */}
          {showRegenerateForm && (
            <>
              <Card.Divider />
              <RegenerateForm
                index={index}
                onSubmit={handleRegenerateSubmit}
                onCancel={() => setShowRegenerateForm(false)}
              />
            </>
          )}
          {/* Inline editor */}
          {isEditing && !isDiscarded && (
            <>
              <Card.Divider />
              <QuestionEditor
                question={question}
                onSave={(updated) => {
                  updateQuestion(index, updated);
                  setEditingIndex(null);
                  setFocusCard(true);
                }}
                onCancel={() => {
                  setEditingIndex(null);
                  setFocusCard(true);
                }}
              />
            </>
          )}
        </Card.Section>

      </Card>
    </div>
  );
};

export default QuestionCard;
