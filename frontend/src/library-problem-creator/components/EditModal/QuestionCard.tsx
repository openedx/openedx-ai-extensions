import React, { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Badge,
  Button, Card, Icon, Stack,
} from '@openedx/paragon';
import QuestionEditor from './QuestionEditor';
import ProblemTypeBadge from './ProblemTypeBadge';
import RegenerateForm from './RegenerateForm';
import VersionNavigator from './VersionNavigator';
import messages from '../../messages';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';
import { Choice } from '../../types';

/** Choice list — shared by MCQ, checkbox, and dropdown */
const ChoiceList = ({ choices }: { choices: Choice[] }) => (
  <ul className="small mb-0">
    {choices.map((choice, i) => (
      <li key={`${choice.text}-${i}`} className={`d-flex align-items-start mb-1`}>
        <span>
          {choice.text}
          {choice.feedback && (
            <p className="ml-2 font-italic x-small">
              {choice.feedback}
            </p>
          )}
        </span>
      </li>
    ))}
  </ul>
);

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

  const question = questions[index];
  const history = questionHistories[index] || [question];
  const selectedVersionIndex = selectedVersionIndices[index] ?? 0;
  const isDiscarded = discardedIndices.has(index);
  const isRegenerating = regeneratingIndices.has(index);
  const isEditing = editingIndex === index;

  const isChoiceBased = ['multiplechoiceresponse', 'choiceresponse', 'optionresponse'].includes(question.problemType);
  const isNumeric = question.problemType === 'numericalresponse';
  const isText = question.problemType === 'stringresponse';

  const handleRegenerateSubmit = (idx: number, instructions?: string) => {
    setShowRegenerateForm(false);
    regenerateQuestion(idx, instructions);
  };

  return (
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
          {isDiscarded ?
            <Badge variant="danger" pill>
              {intl.formatMessage(messages['ai.library.creator.card.discarded.label'])}
            </Badge>
            :
            < ProblemTypeBadge problemType={question.problemType} className="ml-2" />
          }
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

        {/* Choice-based answers */}
        {isChoiceBased && question.choices && question.choices.length > 0 && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.choices'])}>
            <ChoiceList choices={question.choices} />
          </Field>
        )}

        {/* Numeric answer + tolerance */}
        {isNumeric && (
          <div className="d-flex" style={{ gap: '1.5rem' }}>
            {question.answerValue && (
              <Field label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}>
                <code>{question.answerValue}</code>
              </Field>
            )}
            {question.tolerance && question.tolerance !== '<UNKNOWN>' && (
              <Field label={intl.formatMessage(messages['ai.library.creator.card.field.tolerance'])}>
                <code>±{question.tolerance}</code>
              </Field>
            )}
          </div>
        )}

        {/* Text / string answer */}
        {isText && question.answerValue && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}>
            <code>{question.answerValue}</code>
          </Field>
        )}

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
          <>
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

          </>
        ) : (
          <div className="mt-2">
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
        <Card.Divider />
        {/* Inline regenerate form */}
        {showRegenerateForm && (
          <RegenerateForm
            index={index}
            onSubmit={handleRegenerateSubmit}
            onCancel={() => setShowRegenerateForm(false)}
          />
        )}
        {/* Inline editor */}
        {isEditing && !isDiscarded && (
          <QuestionEditor
            question={question}
            onSave={(updated) => { updateQuestion(index, updated); setEditingIndex(null); }}
            onCancel={() => setEditingIndex(null)}
          />
        )}
      </Card.Section>

    </Card>
  );
};

export default QuestionCard;
