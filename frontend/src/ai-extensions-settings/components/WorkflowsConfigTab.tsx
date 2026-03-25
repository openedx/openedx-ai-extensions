/**
 * WorkflowsConfigTab Component
 * Two-column layout: profile list on the left, pretty-printed JSON on the right.
 *
 * NOTE: syntax highlighting via CodeMirror is deferred until the module boundary
 * between this plugin and frontend-app-authoring is formalised (webpack alias needed
 * to avoid duplicate @codemirror/state instances).
 */

import { useEffect, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert, Badge, Button, Spinner } from '@openedx/paragon';
import { AIWorkflowProfile } from '../../types';

type ProfileView = 'profile' | 'scopes' | 'prompt';
import { fetchProfilesList } from '../../services/profilesService';
import { prepareContextData } from '../../services/utils';
import messages from '../messages';

const COLUMN_HEADER_HEIGHT = '2.75rem';

/** Read-only JSON viewer. Plain pre for now; CodeMirror deferred (see file note). */
const JsonViewer = ({ content }: { content: string }) => (
  <pre
    className="bg-white m-0 p-4 small"
    style={{
      flex: 1,
      fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
      lineHeight: 1.6,
      overflowY: 'auto',
      whiteSpace: 'pre',
    }}
  >{content}</pre>
);

interface ProfileListItemProps {
  profile: AIWorkflowProfile;
  isSelected: boolean;
  onSelect: (p: AIWorkflowProfile) => void;
}

const ProfileListItem = ({ profile, isSelected, onSelect }: ProfileListItemProps) => {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      type="button"
      onClick={() => onSelect(profile)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`px-3 py-3 w-100 text-left border-0 border-bottom ${isSelected ? 'bg-primary text-white' : ''}`}
      style={{
        background: (!isSelected && hovered) ? 'var(--pgn-color-gray-200)' : undefined,
        borderLeft: `3px solid ${isSelected ? 'var(--pgn-color-primary-base)' : 'transparent'}`,
        cursor: 'pointer',
        transition: 'background 0.1s',
      }}
    >
      <div className="font-weight-bold small mb-1">
        {profile.slug}
      </div>
      {profile.description && (
        <div
          className="x-small text-muted"
          style={{
            lineHeight: '1.35',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {profile.description}
        </div>
      )}
    </button>
  );
};

const WorkflowsConfigTab = () => {
  const intl = useIntl();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<AIWorkflowProfile[]>([]);
  const [selected, setSelected] = useState<AIWorkflowProfile | null>(null);
  const [view, setView] = useState<ProfileView>('profile');

  const handleSelectProfile = (profile: AIWorkflowProfile) => {
    setSelected(profile);
    setView('profile');
  };

  useEffect(() => {
    const controller = new AbortController();
    const contextData = prepareContextData({});

    fetchProfilesList({ contextData, signal: controller.signal })
      .then((data) => {
        setProfiles(data.profiles);
        if (data.profiles.length > 0) { setSelected(data.profiles[0]); }
        setLoading(false);
      })
      .catch((err) => {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') { return; }
        setError(intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.error']));
        setLoading(false);
      });

    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <div className="p-4 d-flex align-items-center">
        <Spinner animation="border" size="sm" />
        <span className="ml-2">
          {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.loading'])}
        </span>
      </div>
    );
  }

  if (error) {
    return <div className="p-4"><Alert variant="danger">{error}</Alert></div>;
  }

  if (profiles.length === 0) {
    return (
      <div className="p-4">
        <Alert variant="info">
          {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.empty'])}
        </Alert>
      </div>
    );
  }

  const configJson = selected ? JSON.stringify(selected.effectiveConfig, null, 2) : '';
  const scopesJson = selected ? JSON.stringify(selected.scopes, null, 2) : '';

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: '520px' }}>

      {/* Left column */}
      <div
        className="border-right d-flex flex-column"
        style={{ width: '260px', flexShrink: 0 }}
      >
        <div
          className="bg-light border-bottom d-flex align-items-center px-3"
          style={{ height: COLUMN_HEADER_HEIGHT, flexShrink: 0 }}
        >
          <span className="x-small text-uppercase text-muted font-weight-bold" style={{ letterSpacing: '0.07em' }}>
            {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.title'])}
          </span>
          <Badge className="ml-2" variant="secondary">{profiles.length}</Badge>
        </div>

        <div style={{ overflowY: 'auto', flex: 1 }}>
          {profiles.map((profile) => (
            <ProfileListItem
              key={profile.id}
              profile={profile}
              isSelected={selected?.id === profile.id}
              onSelect={handleSelectProfile}
            />
          ))}
        </div>
      </div>

      {/* Right column */}
      <div className="d-flex flex-column" style={{ flex: 1, overflow: 'hidden' }}>
        {selected && (
          <>
            <div
              className="bg-light border-bottom d-flex align-items-center px-4"
              style={{ height: COLUMN_HEADER_HEIGHT, flexShrink: 0, gap: '0.5rem' }}
            >
              <span className="font-weight-bold mr-3">{selected.slug}</span>
              {(['profile', 'scopes', 'prompt'] as ProfileView[]).map((v) => (
                <Button
                  key={v}
                  size="sm"
                  variant={view === v ? 'primary' : 'tertiary'}
                  onClick={() => setView(v)}
                  className="text-capitalize"
                >
                  {v}
                </Button>
              ))}
            </div>
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {view === 'profile' && <JsonViewer content={configJson} />}
              {view === 'scopes' && <JsonViewer content={scopesJson} />}
              {view === 'prompt' && (
                <div className="p-4">
                  <Alert variant="info">Prompt editing is not yet available.</Alert>
                </div>
              )}
            </div>
          </>
        )}
      </div>

    </div>
  );
};

export default WorkflowsConfigTab;
