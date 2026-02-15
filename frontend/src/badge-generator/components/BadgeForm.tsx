/**
 * BadgeForm Component
 * Initial form for users to select badge creation parameters
 * Redesigned with scope selection, unit loader, SelectableBox categories, and skills toggle
 */

import React, { useMemo, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Form,
  StatefulButton,
  SelectableBox,
} from '@openedx/paragon';
import { BadgeFormData } from '../types';
import messages from '../messages';

// Form options defined as arrays for smart rendering
const formOptions = {
  scope: [
    { value: 'course', label: 'openedx-ai-extensions.badge-creation-modal.form.scope.course' },
    { value: 'section', label: 'openedx-ai-extensions.badge-creation-modal.form.scope.section' },
    { value: 'unit', label: 'openedx-ai-extensions.badge-creation-modal.form.scope.unit' },
  ],
  style: [
    { value: 'modern', label: 'openedx-ai-extensions.badge-creation-modal.form.style.modern' },
    { value: 'classic', label: 'openedx-ai-extensions.badge-creation-modal.form.style.classic' },
    { value: 'minimalist', label: 'openedx-ai-extensions.badge-creation-modal.form.style.minimalist' },
    { value: 'playful', label: 'openedx-ai-extensions.badge-creation-modal.form.style.playful' },
  ],
  tone: [
    { value: 'professional', label: 'openedx-ai-extensions.badge-creation-modal.form.tone.professional' },
    { value: 'friendly', label: 'openedx-ai-extensions.badge-creation-modal.form.tone.friendly' },
    { value: 'academic', label: 'openedx-ai-extensions.badge-creation-modal.form.tone.academic' },
    { value: 'creative', label: 'openedx-ai-extensions.badge-creation-modal.form.tone.creative' },
  ],
  level: [
    { value: 'beginner', label: 'openedx-ai-extensions.badge-creation-modal.form.level.beginner' },
    { value: 'intermediate', label: 'openedx-ai-extensions.badge-creation-modal.form.level.intermediate' },
    { value: 'advanced', label: 'openedx-ai-extensions.badge-creation-modal.form.level.advanced' },
    { value: 'expert', label: 'openedx-ai-extensions.badge-creation-modal.form.level.expert' },
  ],
  criterion: [
    { value: 'completion', label: 'openedx-ai-extensions.badge-creation-modal.form.criterion.completion' },
    { value: 'mastery', label: 'openedx-ai-extensions.badge-creation-modal.form.criterion.mastery' },
    { value: 'participation', label: 'openedx-ai-extensions.badge-creation-modal.form.criterion.participation' },
    { value: 'excellence', label: 'openedx-ai-extensions.badge-creation-modal.form.criterion.excellence' },
  ],
};

const BadgeForm = () => {
  const intl = useIntl();

  // Selection state as an object
  const [formData, setFormData] = useState<BadgeFormData>({
    scope: 'course',
    unitId: '',
    style: 'modern',
    tone: 'professional',
    level: 'intermediate',
    criterion: 'completion',
    skillsEnabled: true,
    description: '',
  });

  const [errors, setErrors] = useState<Record<string, boolean>>({});

  // Mock units data
  const mockUnits = useMemo(() => [
    { id: 'unit-1', name: 'Unit 1: Introduction' },
    { id: 'unit-2', name: 'Unit 2: Fundamentals' },
    { id: 'unit-3', name: 'Unit 3: Advanced Topics' },
    { id: 'unit-4', name: 'Unit 4: Capstone Project' },
  ], []);

  const handleChange = (field: keyof BadgeFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: false }));
    }
  };

  return (
    <Form className="badge-form p-3">
      {/* Scope Selection */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.scope.label'])}
        </Form.Label>
        <Form.Text className="d-block mb-3 text-muted">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.scope.description'])}
        </Form.Text>

        <SelectableBox.Set
          value={formData.scope}
          onChange={(e) => handleChange('scope', e.target.value)}
          name="scope"
          ariaLabel="scope selection"
          columns={4}
        >
          {formOptions.scope.map(option => (
            <SelectableBox
              key={option.value}
              value={option.value}
              aria-label={intl.formatMessage(messages[option.label])}
            >
              {intl.formatMessage(messages[option.label])}
            </SelectableBox>
          ))}
        </SelectableBox.Set>
      </Form.Group>

      {/* Unit Selection - shown only when scope is 'unit' */}
      {formData.scope === 'unit' && (
        <Form.Group controlId="unit-select" className="mb-4" isInvalid={errors.unitId}>
          <Form.Label>{intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.unit.label'])}</Form.Label>
          <Form.Control
            as="select"
            value={formData.unitId}
            onChange={(e) => handleChange('unitId', e.target.value)}
          >
            <option value="">
              {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.unit.placeholder'])}
            </option>
            {mockUnits.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name}
              </option>
            ))}
          </Form.Control>
          {errors.unitId && (
            <Form.Control.Feedback type="invalid">
              {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.error.required-field'])}
            </Form.Control.Feedback>
          )}
        </Form.Group>
      )}

      {/* Style Selection */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.style.label'])}
        </Form.Label>
        <SelectableBox.Set
          value={formData.style}
          onChange={(e) => handleChange('style', e.target.value)}
          name="style"
          ariaLabel="style selection"
          columns={4}
        >
          {formOptions.style.map(option => (
            <SelectableBox
              key={option.value}
              value={option.value}
              aria-label={intl.formatMessage(messages[option.label])}
            >
              {intl.formatMessage(messages[option.label])}
            </SelectableBox>
          ))}
        </SelectableBox.Set>
      </Form.Group>

      {/* Tone Selection */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.tone.label'])}
        </Form.Label>
        <SelectableBox.Set
          value={formData.tone}
          onChange={(e) => handleChange('tone', e.target.value)}
          name="tone"
          ariaLabel="tone selection"
          columns={4}
        >
          {formOptions.tone.map(option => (
            <SelectableBox
              key={option.value}
              value={option.value}
              aria-label={intl.formatMessage(messages[option.label])}
            >
              {intl.formatMessage(messages[option.label])}
            </SelectableBox>
          ))}
        </SelectableBox.Set>
      </Form.Group>

      {/* Level Selection */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.level.label'])}
        </Form.Label>
        <SelectableBox.Set
          value={formData.level}
          onChange={(e) => handleChange('level', e.target.value)}
          name="level"
          ariaLabel="level selection"
          columns={4}
        >
          {formOptions.level.map(option => (
            <SelectableBox
              key={option.value}
              value={option.value}
              aria-label={intl.formatMessage(messages[option.label])}
            >
              {intl.formatMessage(messages[option.label])}
            </SelectableBox>
          ))}
        </SelectableBox.Set>
      </Form.Group>

      {/* Criterion Selection */}
      <Form.Group className="mb-4">
        <Form.Label className="font-weight-bold mb-3">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.criterion.label'])}
        </Form.Label>
        <SelectableBox.Set
          value={formData.criterion}
          onChange={(e) => handleChange('criterion', e.target.value)}
          name="criterion"
          ariaLabel="criterion selection"
          columns={4}
        >
          {formOptions.criterion.map(option => (
            <SelectableBox
              key={option.value}
              value={option.value}
              aria-label={intl.formatMessage(messages[option.label])}
            >
              {intl.formatMessage(messages[option.label])}
            </SelectableBox>
          ))}
        </SelectableBox.Set>
      </Form.Group>

      {/* Skills Toggle Switch */}
      <Form.Group className="mb-4">
        <Form.Switch
          id="skills-toggle"
          label={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.skills.label'])}
          checked={formData.skillsEnabled}
          onChange={(e) => handleChange('skillsEnabled', e.target.checked)}
        />
        <Form.Text muted className="d-block mt-2">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.skills.description'], {
            scope: formData.scope.toLowerCase(),
          })}
        </Form.Text>
      </Form.Group>

      {/* Additional Description Textarea */}
      <Form.Group className="mb-4" controlId="description">
        <Form.Label className="font-weight-bold">
          {intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.description.label'])}
        </Form.Label>
        <Form.Control
          as="textarea"
          rows={4}
          placeholder={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.description.placeholder'])}
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
        />
      </Form.Group>

      {/* Submit Button */}
      <div className="d-flex gap-2 justify-content-end mt-4">
        <StatefulButton
          disabled
          labels={{
            default: intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.button.generate']),
            pending: intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.generating.message']),
            complete: intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.button.generate']),
          }}
        />
      </div>
    </Form>
  );
};

export default BadgeForm;
