/**
 * BadgeForm Component
 * Initial form for users to select badge creation parameters
 * Redesigned with scope selection, unit loader, SelectableBox categories, and skills toggle
 */

import React, { useCallback, useMemo } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Form,
  StatefulButton,
  SelectableBox,
} from '@openedx/paragon';
import { BadgeFormData, BadgeScope, BadgeStyle, BadgeTone, BadgeLevel, BadgeCriterion } from '../types';
import messages from '../messages';

interface BadgeFormProps {
  onSubmit: (formData: BadgeFormData) => void;
  isLoading?: boolean;
  initialData?: Partial<BadgeFormData>;
  courseId: string;
}

const BadgeForm: React.FC<BadgeFormProps> = ({
  onSubmit,
  isLoading = false,
  initialData,
}) => {
  const intl = useIntl();
  // Selection state
  const [scope, setScope] = React.useState<BadgeScope>(initialData?.scope || 'course');
  const [unitId, setUnitId] = React.useState<string>(initialData?.unitId || '');
  const [style, setStyle] = React.useState<BadgeStyle>(initialData?.style || 'modern');
  const [tone, setTone] = React.useState<BadgeTone>(initialData?.tone || 'professional');
  const [level, setLevel] = React.useState<BadgeLevel>(initialData?.level || 'intermediate');
  const [criterion, setCriterion] = React.useState<BadgeCriterion>(initialData?.criterion || 'completion');
  const [skillsEnabled, setSkillsEnabled] = React.useState<boolean>(initialData?.skillsEnabled ?? true);
  const [description, setDescription] = React.useState<string>(initialData?.description || '');
  const [errors, setErrors] = React.useState<Record<string, boolean>>({});

  // Mock units data - in a real app this would come from Redux/API
  const mockUnits = useMemo(() => [
    { id: 'unit-1', name: 'Unit 1: Introduction' },
    { id: 'unit-2', name: 'Unit 2: Fundamentals' },
    { id: 'unit-3', name: 'Unit 3: Advanced Topics' },
    { id: 'unit-4', name: 'Unit 4: Capstone Project' },
  ], []);

  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, boolean> = {};

    if (scope === 'unit' && !unitId) {
      newErrors.unitId = true;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [scope, unitId]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (validateForm()) {
        const formData: BadgeFormData = {
          scope,
          ...(scope === 'unit' && { unitId }),
          style,
          tone,
          level,
          criterion,
          skillsEnabled,
          ...(description && { description }),
        };
        onSubmit(formData);
      }
    },
    [scope, unitId, style, tone, level, criterion, skillsEnabled, description, validateForm, onSubmit]
  );

  return (
    <Form onSubmit={handleSubmit} className="badge-form p-3">
      {/* Scope Selection using SelectableBox as Radio */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages.scopeLabel)}
        </Form.Label>
        <Form.Text className="d-block mb-3 text-muted">
          {intl.formatMessage(messages.scopeDescription)}
        </Form.Text>

        <SelectableBox.Set
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          name="scope"
          ariaLabel="scope selection"
          columns={4}

        >
          <SelectableBox
            value="course"
            aria-label={intl.formatMessage(messages.scopeCourse)}
          >
            {intl.formatMessage(messages.scopeCourse)}
          </SelectableBox>
          <SelectableBox
            type="radio"
            value="section"
            aria-label={intl.formatMessage(messages.scopeSection)}
          >
            {intl.formatMessage(messages.scopeSection)}
          </SelectableBox>
          <SelectableBox
            type="radio"
            value="unit"
            aria-label={intl.formatMessage(messages.scopeUnit)}
          >
            {intl.formatMessage(messages.scopeUnit)}
          </SelectableBox>
        </SelectableBox.Set>
      </Form.Group>

      {/*TODO build with the course outline Unit Selection - shown only when scope is 'unit' */}
      {scope === 'unit' && (
        <Form.Group controlId="unit-select" className="mb-4" isInvalid={errors.unitId}>
          <Form.Label>{intl.formatMessage(messages.unitLabel)}</Form.Label>
          <Form.Control
            as="select"
            value={unitId}
            onChange={(e) => {
              setUnitId(e.target.value);
              if (errors.unitId) {
                setErrors(prev => ({ ...prev, unitId: false }));
              }
            }}
            disabled={isLoading}
          >
            <option value="">
              {intl.formatMessage(messages.unitPlaceholder)}
            </option>
            {mockUnits.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name}
              </option>
            ))}
          </Form.Control>
          {errors.unitId && (
            <Form.Control.Feedback type="invalid">
              {intl.formatMessage(messages.requiredFieldError)}
            </Form.Control.Feedback>
          )}
        </Form.Group>
      )}

      {/* Style Selection using SelectableBox.Set */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages.styleLabel)}
        </Form.Label>

        <SelectableBox.Set
          value={style}
          onChange={(e) => setStyle(e.target.value as BadgeStyle)}
          name="style"
          ariaLabel="style selection"
          columns={4}

        >
          <SelectableBox
            value="modern"
            aria-label={intl.formatMessage(messages.styleModern)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.styleModern)}
          </SelectableBox>
          <SelectableBox
            value="classic"
            aria-label={intl.formatMessage(messages.styleClassic)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.styleClassic)}
          </SelectableBox>
          <SelectableBox
            value="minimalist"
            aria-label={intl.formatMessage(messages.styleMinimalist)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.styleMinimalist)}
          </SelectableBox>
          <SelectableBox
            value="playful"
            aria-label={intl.formatMessage(messages.stylePlayful)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.stylePlayful)}
          </SelectableBox>
        </SelectableBox.Set>
      </Form.Group>

      {/* Tone Selection using SelectableBox.Set */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages.toneLabel)}
        </Form.Label>

        <SelectableBox.Set
          value={tone}
          onChange={(e) => setTone(e.target.value as BadgeTone)}
          name="tone"
          ariaLabel="tone selection"
          columns={4}

        >
          <SelectableBox
            value="professional"
            aria-label={intl.formatMessage(messages.toneProfessional)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.toneProfessional)}
          </SelectableBox>
          <SelectableBox
            value="friendly"
            aria-label={intl.formatMessage(messages.toneFriendly)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.toneFriendly)}
          </SelectableBox>
          <SelectableBox
            value="academic"
            aria-label={intl.formatMessage(messages.toneAcademic)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.toneAcademic)}
          </SelectableBox>
          <SelectableBox
            value="creative"
            aria-label={intl.formatMessage(messages.toneCreative)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.toneCreative)}
          </SelectableBox>
        </SelectableBox.Set>
      </Form.Group>

      {/* Level Selection using SelectableBox.Set */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages.levelLabel)}
        </Form.Label>

        <SelectableBox.Set
          value={level}
          onChange={(e) => setLevel(e.target.value as BadgeLevel)}
          name="level"
          columns={4}
          ariaLabel="level selection"
        >
          <SelectableBox
            value="beginner"
            aria-label={intl.formatMessage(messages.levelBeginner)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.levelBeginner)}
          </SelectableBox>
          <SelectableBox
            value="intermediate"
            aria-label={intl.formatMessage(messages.levelIntermediate)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.levelIntermediate)}
          </SelectableBox>
          <SelectableBox
            value="advanced"
            aria-label={intl.formatMessage(messages.levelAdvanced)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.levelAdvanced)}
          </SelectableBox>
          <SelectableBox
            value="expert"
            aria-label={intl.formatMessage(messages.levelExpert)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.levelExpert)}
          </SelectableBox>
        </SelectableBox.Set>
      </Form.Group>

      {/* Criterion Selection using SelectableBox.Set */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages.criterionLabel)}
        </Form.Label>

        <SelectableBox.Set
          value={criterion}
          onChange={(e) => setCriterion(e.target.value as BadgeCriterion)}
          name="criterion"
          ariaLabel="criterion selection"
          columns={4}

        >
          <SelectableBox
            value="completion"
            aria-label={intl.formatMessage(messages.criterionCompletion)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.criterionCompletion)}
          </SelectableBox>
          <SelectableBox
            value="mastery"
            aria-label={intl.formatMessage(messages.criterionMastery)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.criterionMastery)}
          </SelectableBox>
          <SelectableBox
            value="participation"
            aria-label={intl.formatMessage(messages.criterionParticipation)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.criterionParticipation)}
          </SelectableBox>
          <SelectableBox
            value="excellence"
            aria-label={intl.formatMessage(messages.criterionExcellence)}
            disabled={isLoading}
          >
            {intl.formatMessage(messages.criterionExcellence)}
          </SelectableBox>
        </SelectableBox.Set>
      </Form.Group>

      {/* Skills Toggle Switch */}
      <Form.Group className="mb-4">
        <Form.Switch
          id="skills-toggle"
          label={intl.formatMessage(messages.skillsEnabledLabel)}
          checked={skillsEnabled}
          onChange={(e) => setSkillsEnabled(e.target.checked)}
          disabled={isLoading}
        />
        <Form.Text muted className="d-block mt-2">
          {intl.formatMessage(messages.skillsEnabledDescription, {
            scope: scope.toLowerCase(),
          })}
        </Form.Text>
      </Form.Group>

      {/* Additional Description Textarea */}
      <Form.Group className="mb-4" controlId="description">
        <Form.Label className="font-weight-bold">
          {intl.formatMessage(messages.descriptionLabel)}
        </Form.Label>
        <Form.Control
          as="textarea"
          rows={4}
          placeholder={intl.formatMessage(messages.descriptionPlaceholder)}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={isLoading}
        />
      </Form.Group>

      {/* Submit Button */}
      <div className="d-flex gap-2 justify-content-end mt-4">
        <StatefulButton
          onClick={handleSubmit}
          disabled={isLoading}
          state={isLoading ? 'pending' : 'default'}
          labels={{
            default: intl.formatMessage(messages.generateButton),
            pending: intl.formatMessage(messages.generatingMessage),
            complete: intl.formatMessage(messages.generateButton),
          }}
        />
      </div>
    </Form>
  );
};

export default BadgeForm;
